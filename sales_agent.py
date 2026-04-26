"""Telegram sales agent powered by Groq."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from groq import AsyncGroq

from catalog import (
    build_no_match_reply,
    build_selection_reply,
    build_smalltalk_reply,
    build_sales_listing,
    get_products_by_ids,
    is_price_query,
    price_for_quantity,
    render_catalog_context,
    resolve_catalog_product,
    search_alternatives,
    search_products,
)
from config import (
    COMPANY_NAME,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_MODEL_FALLBACK,
    MANAGER_NAME,
    MAX_HISTORY_MESSAGES,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    STATUS_LABELS,
    SUPPLIER_EMAIL,
    SUPPLIER_TELEGRAM_CHAT_ID,
)
from database import (
    add_order_event,
    clear_conversation_history,
    create_order as db_create_order,
    get_client_orders,
    get_conversation_history,
    get_lead,
    get_order,
    get_order_events,
    get_order_summary_for_client,
    reload_products,
    save_conversation_history,
    update_order,
    upsert_lead,
)

logger = logging.getLogger(__name__)

_CONTACT_RE = re.compile(r"(\+?\d[\d\-\s()]{8,}\d|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_PURCHASE_WORDS = {"беру", "возьму", "оформляй", "оформить", "заказываю", "нужны", "скидывай"}
_BUDGET_WORDS = {"бюджет", "дешевле", "дорого", "недорого", "цена", "сколько", "диапазон"}

_SYSTEM_PROMPT = """\
Ты — {name}, сильный менеджер по продажам компании {company}. Отвечаешь как взрослый уверенный продавец, а не как бот и не как ребёнок.

Жёсткие правила:
1. Опирайся только на служебные блоки [КАТАЛОГ] и [ПРОДАЖА].
2. Не придумывай товары, цены, наличие, скидки и сроки.
3. Пиши по-деловому, коротко и уверенно.
4. Не сюсюкай, не отвечай односложно в духе "хорошо", "секунду", "будет", если можно ответить предметно.
5. Если товар уже найден кодом и показан клиенту, помогай выбрать и доводи до заказа.
6. Если клиент хочет оформить, собери имя, контакт и количество.
7. create_order вызывай только когда есть точный product_id из каталога.
8. После create_order сразу вызывай notify_supplier.
9. Если клиент сомневается по цене, помоги сузить выбор по бюджету.
10. Не используй markdown.

Тон:
- профессиональный;
- живой, но без фамильярности;
- торговый: вести к выбору и закрытию;
- если есть выбор, лучше дать конкретику, чем пустой вопрос.
"""

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Создать заказ по товару из каталога.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_chat_id": {"type": "integer"},
                    "client_name": {"type": "string"},
                    "client_contact": {"type": "string"},
                    "product_id": {"type": "string"},
                    "product_name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["client_chat_id", "client_name", "client_contact", "product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_supplier",
            "description": "Уведомить поставщика о заказе.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_info",
            "description": "Получить детали заказа по ID.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_client_orders",
            "description": "Получить активные заказы клиента.",
            "parameters": {
                "type": "object",
                "properties": {"client_chat_id": {"type": "integer"}},
                "required": ["client_chat_id"],
            },
        },
    },
]


class SalesAgent:
    """RAG-first sales agent with deterministic catalog replies."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._bot = None
        self._active_model = GROQ_MODEL
        self._system = _SYSTEM_PROMPT.format(name=MANAGER_NAME, company=COMPANY_NAME)
        products = reload_products()
        if not products:
            logger.warning("Catalog is empty. Run: py import_excel.py <price.xlsx>")
        else:
            logger.info("Catalog loaded: %d products", len(products))

    def set_bot(self, bot) -> None:
        self._bot = bot

    def refresh(self) -> int:
        products = reload_products()
        self._system = _SYSTEM_PROMPT.format(name=MANAGER_NAME, company=COMPANY_NAME)
        return len(products)

    def _remember_catalog(self, history: list[dict], catalog_context: str) -> list[dict]:
        cleaned = [
            item for item in history
            if not (item.get("role") == "system" and "[ПАМЯТЬ_КАТАЛОГА]" in item.get("content", ""))
        ]
        if "Статус: найдено" in catalog_context:
            compact = "\n".join(catalog_context.splitlines()[:7])
            cleaned.append({"role": "system", "content": f"[ПАМЯТЬ_КАТАЛОГА]\n{compact}"})
        return cleaned

    def _infer_lead_stage(self, text: str, matches: list[dict], lead: Optional[dict]) -> str:
        text_l = text.lower()
        if _CONTACT_RE.search(text_l):
            return "checkout"
        if any(word in text_l for word in _PURCHASE_WORDS):
            return "intent"
        if matches:
            return "selection" if len(matches) <= 5 else "discovery"
        if any(word in text_l for word in _BUDGET_WORDS):
            return "qualification"
        return lead.get("stage", "new") if lead else "new"

    def _next_sales_step(self, text: str, stage: str, matches: list[dict]) -> str:
        if is_price_query(text):
            return "Уточнить ценовой диапазон и после этого показать подходящие варианты."
        if stage == "checkout":
            return "Подтвердить товар, количество и оформить заказ."
        if stage == "intent":
            return "Собрать имя, контакт и количество."
        if stage == "selection":
            return "Помочь клиенту выбрать конкретную позицию и закрыть на заказ."
        if stage == "discovery":
            return "Показать ассортимент и довести до выбора позиции."
        if stage == "qualification":
            return "Уточнить бюджет или главный параметр."
        if matches:
            return "Дать конкретные варианты и вести к выбору."
        return "Выявить потребность и предложить релевантный товар."

    async def _sales_context(self, chat_id: int, text: str, catalog_context: str, matches: list[dict]) -> str:
        lead = await get_lead(chat_id)
        summary = await get_order_summary_for_client(chat_id)
        stage = self._infer_lead_stage(text=text, matches=matches, lead=lead)
        next_step = self._next_sales_step(text=text, stage=stage, matches=matches)
        interested_ids = [item["id"] for item in matches[:12]]

        await upsert_lead(
            chat_id,
            stage=stage,
            summary=next_step,
            interested_product_ids=interested_ids,
            last_message=text[:500],
        )

        known_contact = lead.get("client_contact", "") if lead else ""
        known_products = ", ".join((lead.get("interested_product_ids", []) if lead else [])[:5]) or "нет"
        lines = catalog_context.splitlines()
        catalog_status = lines[1] if len(lines) > 1 else "нет"
        return (
            "[ПРОДАЖА]\n"
            f"Стадия: {stage}\n"
            f"Следующий шаг: {next_step}\n"
            f"История клиента: заказов={summary['total_orders']}, выручка={summary['total_revenue']:.2f}\n"
            f"Известный контакт: {known_contact or 'нет'}\n"
            f"Интересы лида: {known_products}\n"
            f"Каталог: {catalog_status}"
        )

    async def process_message(self, chat_id: int, text: str, user_name: str = "Клиент") -> str:
        history = await get_conversation_history(chat_id)
        lead = await get_lead(chat_id)
        preferred_ids = lead.get("interested_product_ids", []) if lead else []
        context_products = get_products_by_ids(preferred_ids)

        selection_reply = build_selection_reply(text, context_products)
        if selection_reply:
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": selection_reply})
            await save_conversation_history(chat_id, history, user_name)
            return selection_reply

        smalltalk_reply = build_smalltalk_reply(text, has_context=bool(context_products))
        if smalltalk_reply:
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": smalltalk_reply})
            await save_conversation_history(chat_id, history, user_name)
            return smalltalk_reply

        catalog_context, matches = render_catalog_context(text, preferred_product_ids=preferred_ids)
        sales_context = await self._sales_context(chat_id, text, catalog_context, matches)

        deterministic_reply = build_sales_listing(text, matches)
        if deterministic_reply:
            logger.info(
                "Deterministic catalog reply | chat_id=%s | matches=%s | price_query=%s",
                chat_id,
                len(matches),
                is_price_query(text),
            )
            history.append({"role": "user", "content": text})
            history = self._remember_catalog(history, catalog_context)
            history.append({"role": "assistant", "content": deterministic_reply})
            await save_conversation_history(chat_id, history, user_name)
            return deterministic_reply

        alternatives = []
        if not matches and is_price_query(text):
            alternatives = search_products(text, limit=3, preferred_product_ids=preferred_ids, ignore_price=True)
        if not matches and not alternatives:
            alternatives = search_alternatives(text, limit=3)
        no_match_reply = build_no_match_reply(text, had_context=bool(context_products), alternatives=alternatives)
        if no_match_reply and not matches:
            logger.info("No-match catalog reply | chat_id=%s | had_context=%s", chat_id, bool(context_products))
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": no_match_reply})
            await save_conversation_history(chat_id, history, user_name)
            return no_match_reply

        llm_history = list(history)
        llm_history.append({"role": "user", "content": text})
        llm_history.append({"role": "system", "content": catalog_context})
        llm_history.append({"role": "system", "content": sales_context})
        if len(llm_history) > MAX_HISTORY_MESSAGES:
            llm_history = llm_history[-MAX_HISTORY_MESSAGES:]

        allow_tools = bool(_CONTACT_RE.search(text.lower()))
        logger.info(
            "LLM reply path | chat_id=%s | matches=%s | model=%s | allow_tools=%s",
            chat_id,
            len(matches),
            self._active_model,
            allow_tools,
        )
        reply = await self._run_loop(llm_history, context_chat_id=chat_id, allow_tools=allow_tools)

        history.append({"role": "user", "content": text})
        history = self._remember_catalog(history, catalog_context)
        history.append({"role": "assistant", "content": reply})
        await save_conversation_history(chat_id, history, user_name)
        return reply

    async def process_supplier_message(self, raw_text: str) -> Optional[tuple[int, str]]:
        upper = raw_text.upper()
        match = re.search(r"ПОДТВЕРЖДАЮ\s+(ORD-[A-Z0-9]+)", upper)
        if match:
            return await self._supplier_confirmed(match.group(1), raw_text)
        match = re.search(r"РЕЗЕРВ\s+(ORD-[A-Z0-9]+)", upper)
        if match:
            return await self._supplier_reserved(match.group(1))
        match = re.search(r"ОТМЕНА\s+(ORD-[A-Z0-9]+)", upper)
        if match:
            return await self._supplier_cancelled(match.group(1), raw_text)
        return None

    async def reset_history(self, chat_id: int) -> None:
        await clear_conversation_history(chat_id)

    async def _run_loop(self, messages: list[dict], context_chat_id: int, allow_tools: bool) -> str:
        import asyncio

        working = [{"role": "system", "content": self._system}] + list(messages)

        for _iteration in range(6):
            response = None
            last_err = None
            for attempt in range(3):
                try:
                    response = await self._client.chat.completions.create(
                        model=self._active_model,
                        messages=working,
                        tools=_TOOLS if allow_tools else None,
                        tool_choice="auto" if allow_tools else "none",
                        max_tokens=512,
                        temperature=0.15,
                    )
                    last_err = None
                    break
                except Exception as exc:
                    last_err = exc
                    err = str(exc).lower()
                    if "rate_limit" in err or "rate limit" in err or "429" in err:
                        if self._active_model != GROQ_MODEL_FALLBACK:
                            logger.warning("Rate limit on %s -> fallback %s", self._active_model, GROQ_MODEL_FALLBACK)
                            self._active_model = GROQ_MODEL_FALLBACK
                        else:
                            await asyncio.sleep(3)
                        continue
                    if any(key in err for key in ("failed_generation", "overloaded", "timeout", "503")):
                        logger.warning("Groq transient (attempt %d): %s", attempt + 1, exc)
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

            if last_err is not None:
                logger.error("Groq failed after retries: %s", last_err)
                return "Сейчас небольшая техническая задержка. Напишите ещё раз через пару секунд."

            choice = response.choices[0]
            if choice.finish_reason != "tool_calls":
                content = choice.message.content or ""
                return content.strip() or "Что подобрать?"

            tool_calls_list = []
            for tc in (choice.message.tool_calls or []):
                tool_calls_list.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                )
            working.append({"role": "assistant", "content": choice.message.content or "", "tool_calls": tool_calls_list})

            for tc in (choice.message.tool_calls or []):
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = await self._exec(tc.function.name, args, context_chat_id)
                logger.info("Tool %s -> %.120s", tc.function.name, result)
                working.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Не получилось завершить операцию. Напишите ещё раз."

    async def _exec(self, name: str, args: dict, chat_id: int) -> str:
        try:
            match name:
                case "create_order":
                    return await self._create_order(args, chat_id)
                case "notify_supplier":
                    return await self._notify_supplier(args["order_id"])
                case "get_order_info":
                    return await self._get_order_info(args["order_id"])
                case "get_client_orders":
                    return await self._get_client_orders(args.get("client_chat_id", chat_id))
                case _:
                    return f"Неизвестный инструмент: {name}"
        except Exception as exc:
            logger.exception("Tool %s error", name)
            return f"Ошибка: {exc}"

    async def _create_order(self, inp: dict, default_chat_id: int) -> str:
        quantity = inp.get("quantity", 0)
        if not isinstance(quantity, int) or quantity <= 0:
            return "Ошибка: количество должно быть целым числом больше нуля."

        product = resolve_catalog_product(product_id=inp.get("product_id", ""), product_name=inp.get("product_name", ""))
        if not product:
            return "Ошибка: товар не найден в текущем каталоге. Выберите точную позицию из каталога."
        if not inp.get("client_name", "").strip():
            return "Ошибка: не указано имя клиента."
        if not inp.get("client_contact", "").strip():
            return "Ошибка: не указан контакт клиента."

        unit_price, discount_pct = price_for_quantity(product, quantity)
        order_id = await db_create_order(
            {
                "client_chat_id": inp.get("client_chat_id", default_chat_id),
                "client_name": inp.get("client_name", "").strip(),
                "client_contact": inp.get("client_contact", "").strip(),
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "notes": inp.get("notes", "").strip(),
            }
        )
        total = unit_price * quantity
        await add_order_event(
            order_id,
            event_type="created",
            source="bot",
            payload=json.dumps({"product_id": product["id"], "quantity": quantity, "unit_price": unit_price}, ensure_ascii=False),
        )
        await upsert_lead(
            inp.get("client_chat_id", default_chat_id),
            client_name=inp.get("client_name", "").strip(),
            client_contact=inp.get("client_contact", "").strip(),
            stage="ordered",
            summary=f"Оформлен заказ {order_id}",
            interested_product_ids=[product["id"]],
            order_delta=1,
            revenue_delta=total,
        )

        discount_line = f"\nСкидка: {discount_pct}%" if discount_pct else ""
        return (
            f"Заказ оформил: {order_id}\n"
            f"Товар: {product['name']}\n"
            f"Количество: {quantity}\n"
            f"Цена за шт: {unit_price:,.2f} ₽{discount_line}\n"
            f"Сумма: {total:,.2f} ₽\n"
            f"Контакт: {inp.get('client_name', '').strip()} / {inp.get('client_contact', '').strip()}"
        )

    async def _notify_supplier(self, order_id: str) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."

        full_msg = (
            f"Новый заказ {order_id}\n\n"
            f"Товар: {order['product_name']}\n"
            f"Количество: {order['quantity']} шт.\n"
            f"Сумма: {order['total_price']:,.2f} ₽\n"
            f"Клиент: {order.get('client_name', '')} / {order.get('client_contact', '')}\n"
            f"Комментарий: {order.get('notes', '') or 'нет'}\n\n"
            f"Ответьте одной командой:\n"
            f"ПОДТВЕРЖДАЮ {order_id}\n"
            f"РЕЗЕРВ {order_id}\n"
            f"ОТМЕНА {order_id}"
        )

        sent = []
        if SUPPLIER_TELEGRAM_CHAT_ID and self._bot:
            try:
                await self._bot.send_message(chat_id=int(SUPPLIER_TELEGRAM_CHAT_ID), text=full_msg)
                sent.append("Telegram")
            except Exception as exc:
                logger.error("Supplier TG failed: %s", exc)
        if SUPPLIER_EMAIL and not sent:
            try:
                await self._send_email(to=SUPPLIER_EMAIL, subject=f"Заказ {order_id}", body=full_msg)
                sent.append("Email")
            except Exception as exc:
                logger.error("Supplier email failed: %s", exc)
        if sent:
            await update_order(order_id, {"supplier_notified": 1})
            await add_order_event(order_id, event_type="supplier_notified", source="bot", payload=",".join(sent))
            return f"Поставщик уведомлен ({', '.join(sent)})."
        return "Не удалось уведомить поставщика. Проверьте настройки поставщика в .env."

    async def _get_order_info(self, order_id: str) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."
        events = await get_order_events(order_id)
        last_event = events[-1]["event_type"] if events else "created"
        return (
            f"Заказ {order['id']}\n"
            f"Товар: {order['product_name']} x {order['quantity']}\n"
            f"Сумма: {order['total_price']:,.2f} ₽\n"
            f"Статус: {STATUS_LABELS.get(order['status'], order['status'])}\n"
            f"Последнее событие: {last_event}\n"
            f"Создан: {order['created_at'][:10]}"
        )

    async def _get_client_orders(self, client_chat_id: int) -> str:
        orders = await get_client_orders(client_chat_id)
        if not orders:
            return "Активных заказов нет."
        lines = [f"Заказов: {len(orders)}"]
        for order in orders:
            lines.append(f"- {order['id']} — {order['product_name']} x {order['quantity']} [{order['status']}]")
        return "\n".join(lines)

    async def _supplier_confirmed(self, order_id: str, raw: str) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {"status": "confirmed", "supplier_confirmed": 1, "notes": f"Подтверждено: {raw[:200]}"})
        await add_order_event(order_id, event_type="confirmed", source="supplier", payload=raw[:200])
        await upsert_lead(
            order["client_chat_id"],
            client_name=order.get("client_name", ""),
            client_contact=order.get("client_contact", ""),
            stage="confirmed",
            summary=f"Поставщик подтвердил заказ {order_id}",
            interested_product_ids=[order["product_id"]] if order.get("product_id") else None,
        )
        return (
            order["client_chat_id"],
            (
                f"Заказ {order_id} подтверждён.\n\n"
                f"Товар: {order['product_name']} x {order['quantity']}\n"
                f"Сумма: {order['total_price']:,.2f} ₽\n"
                "Дальше согласуем оплату и отгрузку."
            ),
        )

    async def _supplier_reserved(self, order_id: str) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {"status": "reserved"})
        await add_order_event(order_id, event_type="reserved", source="supplier")
        await upsert_lead(
            order["client_chat_id"],
            client_name=order.get("client_name", ""),
            client_contact=order.get("client_contact", ""),
            stage="reserved",
            summary=f"Заказ {order_id} зарезервирован",
            interested_product_ids=[order["product_id"]] if order.get("product_id") else None,
        )
        return (
            order["client_chat_id"],
            (
                f"Заказ {order_id} зарезервирован.\n\n"
                f"Товар: {order['product_name']} x {order['quantity']}\n"
                "Можно переходить к оплате и выдаче."
            ),
        )

    async def _supplier_cancelled(self, order_id: str, raw: str) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {"status": "cancelled", "notes": f"Отменено: {raw[:200]}"})
        await add_order_event(order_id, event_type="cancelled", source="supplier", payload=raw[:200])
        await upsert_lead(
            order["client_chat_id"],
            client_name=order.get("client_name", ""),
            client_contact=order.get("client_contact", ""),
            stage="recovery",
            summary=f"Нужна замена вместо заказа {order_id}",
            interested_product_ids=[order["product_id"]] if order.get("product_id") else None,
        )
        return (
            order["client_chat_id"],
            (
                f"По заказу {order_id} возникла проблема.\n\n"
                f"Товар {order['product_name']} сейчас недоступен.\n"
                "Подберу замену и сразу напишу."
            ),
        )

    async def _send_email(self, to: str, subject: str, body: str) -> None:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
