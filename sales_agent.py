"""
Telegram Sales Agent — Groq/Llama powered.

Architecture: RAG-first, minimal tools.
  • Products are ALWAYS pre-fetched from catalog and injected into context.
  • The model's only job: present catalog data nicely + create orders via tools.
  • No tool calls needed for search — RAG handles it, eliminating hallucinations.

Tools kept (only what MUST hit the database/network):
  create_order, notify_supplier, get_order_info, get_client_orders
"""

import json
import logging
import re
from typing import Optional

from groq import AsyncGroq

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
    clear_conversation_history,
    create_order as db_create_order,
    get_client_orders,
    get_conversation_history,
    get_order,
    load_products,
    reload_products,
    save_conversation_history,
    update_order,
)

logger = logging.getLogger(__name__)

# ─── Stop-words for RAG keyword extraction ────────────────────────────────────

_STOP = {
    "нужен","нужна","нужно","нужны","хочу","хочет","хотим","хотите",
    "дайте","покажи","покажите","есть","ли","что","как","где","сколько",
    "стоит","цена","цены","расскажи","расскажите","меня","интересует",
    "интересуют","нас","мне","нам","вас","вам","про","для","купить",
    "куплю","заказать","хочется","подойдет","подойдёт","посоветуйте",
    "посоветуй","помогите","помоги","ищу","найдите","найди","какой",
    "какая","какие","это","тот","та","те","тот","самый","очень","или",
    "ещё","еще","также","тоже","более","менее","дешевле","дороже",
    "лучше","хуже","и","в","на","с","по","из","от","до","за","при",
    "под","над","без","со","но","так","не","у","а","к","ко",
}

# ─── System prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Ты — {name}, менеджер по продажам компании «{company}».
Ты живой человек — клиент не должен чувствовать, что говорит с ботом.

ХАРАКТЕР И СТИЛЬ:
• Общайся тепло и естественно — как опытный менеджер, которому не всё равно
• Задавай уточняющие вопросы когда нужно понять задачу клиента
• Не начинай фразы с "Конечно!", "Отлично!", "Разумеется!" — это звучит шаблонно
• Используй живые переходы: "Смотрите...", "Тут такой момент...", "Как раз есть..."
• Если клиент шутит или пишет неформально — можно ответить легко
• Обращайся на «Вы», но без официоза — по-деловому и с теплотой

ДЛИНА ОТВЕТОВ:
• Простой вопрос → 2-3 предложения
• Сравнение товаров, подбор → столько, сколько нужно для ясности
• Не перечисляй всё подряд — вычли главное под запрос клиента

ПРАВИЛА (строго):
• Цены и наличие — ТОЛЬКО из раздела [КАТАЛОГ] в сообщении пользователя
• Никогда не придумывай цены, характеристики или сроки самостоятельно
• Если товара нет в каталоге — скажи что уточнишь у поставщика лично
• При оформлении заказа: сначала узнай имя и номер телефона клиента,
  потом вызови create_order, потом notify_supplier — оба вызова обязательны\
"""

# ─── Tools (only DB/network operations — product search done via RAG) ─────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": (
                "Оформить заказ и записать в базу. "
                "Вызывать только после получения имени клиента, "
                "контакта, товара и количества."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "client_chat_id": {
                        "type": "integer",
                        "description": "Telegram chat_id клиента",
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Имя клиента",
                    },
                    "client_contact": {
                        "type": "string",
                        "description": "Телефон или email",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Точное название товара из каталога",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Количество штук",
                    },
                    "unit_price": {
                        "type": "number",
                        "description": "Цена за 1 штуку из каталога (в рублях)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Дополнительные пожелания клиента",
                    },
                },
                "required": [
                    "client_chat_id", "client_name", "product_name",
                    "quantity", "unit_price",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_supplier",
            "description": (
                "Отправить поставщику уведомление о заказе "
                "(Telegram или email). Вызывать сразу после create_order."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID заказа вида ORD-XXXXXXXX",
                    },
                    "message": {
                        "type": "string",
                        "description": "Текст для поставщика: товар, кол-во, контакт клиента",
                    },
                },
                "required": ["order_id", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_info",
            "description": "Получить статус и детали заказа по его ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID заказа, например ORD-AB12CD34",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_client_orders",
            "description": "Получить список активных заказов клиента.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_chat_id": {
                        "type": "integer",
                        "description": "Telegram chat_id клиента",
                    },
                },
                "required": ["client_chat_id"],
            },
        },
    },
]


# ─── Agent ────────────────────────────────────────────────────────────────────


class SalesAgent:
    """RAG-first sales agent. Products come from catalog, not from LLM memory."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._bot = None
        self._active_model = GROQ_MODEL
        self._system = _SYSTEM_PROMPT.format(
            name=MANAGER_NAME, company=COMPANY_NAME
        )
        # Sanity check on startup
        products = reload_products()
        if not products:
            logger.warning("⚠️  Catalog is EMPTY. Run: py import_excel.py <price.xlsx>")
        else:
            logger.info("✅ Catalog loaded: %d products", len(products))

    def set_bot(self, bot) -> None:
        self._bot = bot

    def refresh(self) -> int:
        """Reload catalog and rebuild system prompt. Returns product count."""
        products = reload_products()
        self._system = _SYSTEM_PROMPT.format(
            name=MANAGER_NAME, company=COMPANY_NAME
        )
        return len(products)

    # ── RAG: pre-fetch catalog context ────────────────────────────────────────

    def _rag(self, text: str) -> str:
        """
        Search catalog by keywords in user message.
        Returns a compact product list to inject into the LLM context.
        If nothing matches — returns list of available categories.
        """
        products = load_products()
        if not products:
            return "[КАТАЛОГ: пуст — скажи клиенту что уточнишь у поставщика]"

        # Extract meaningful tokens
        tokens = [
            w for w in re.split(r"[\s,./!?()\[\]«»\"]+", text.lower())
            if len(w) > 2 and w not in _STOP
        ]

        if not tokens:
            # No searchable keywords — just show categories
            return self._catalog_categories(products)

        # Score each product
        scored: list[tuple[int, dict]] = []
        for p in products:
            name_l = p["name"].lower()
            cat_l  = p.get("category", "").lower()
            desc_l = p.get("description", "").lower()
            sku_l  = p.get("supplier_sku", "").lower()
            full   = f"{name_l} {cat_l} {desc_l} {sku_l}"
            score  = sum(
                3 if t in name_l else 2 if t in cat_l else 1 if t in full else 0
                for t in tokens
            )
            if score > 0:
                scored.append((score, p))

        if not scored:
            return self._catalog_categories(products)

        scored.sort(key=lambda x: (-x[0], x[1]["price"]))
        top = [p for _, p in scored[:8]]

        lines = [f"[КАТАЛОГ: {len(scored)} найдено, показано {len(top)}]"]
        for p in top:
            stock = f"{p['stock']}шт" if p.get("stock", 0) > 0 else "под заказ"
            # Include discount hint if available
            disc = p.get("discounts", {})
            disc_str = ""
            if disc:
                best = max(disc.values())
                disc_str = f" (опт -{best}%)"
            lines.append(
                f"• {p['name']} — {p['price']:.0f}₽{disc_str} | {stock}"
            )
        return "\n".join(lines)

    @staticmethod
    def _catalog_categories(products: list) -> str:
        """Return compact category list when no products match."""
        cats: dict[str, int] = {}
        for p in products:
            cat = p.get("category") or "Разное"
            cats[cat] = cats.get(cat, 0) + 1
        lines = [f"[КАТАЛОГ: {len(products)} товаров, категории:]"]
        for cat, cnt in sorted(cats.items()):
            lines.append(f"• {cat} ({cnt} позиций)")
        return "\n".join(lines)

    # ── Main entry points ──────────────────────────────────────────────────────

    async def process_message(
        self, chat_id: int, text: str, user_name: str = "Клиент"
    ) -> str:
        history = await get_conversation_history(chat_id)

        # Inject catalog data into user message — this is the anti-hallucination core
        catalog_block = self._rag(text)
        user_content = f"{text}\n\n{catalog_block}"

        history.append({"role": "user", "content": user_content})
        # Trim to MAX_HISTORY_MESSAGES for LLM (DB stores more for future context)
        llm_history = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history
        reply = await self._run_loop(llm_history, context_chat_id=chat_id)

        # Save clean history (without injected catalog) — DB stores full history
        history[-1] = {"role": "user", "content": text}
        history.append({"role": "assistant", "content": reply})
        await save_conversation_history(chat_id, history, user_name)
        return reply

    async def process_supplier_message(
        self, raw_text: str
    ) -> Optional[tuple[int, str]]:
        upper = raw_text.upper()
        m = re.search(r"ПОДТВЕРЖДАЮ\s+(ORD-[A-Z0-9]+)", upper)
        if m:
            return await self._supplier_confirmed(m.group(1), raw_text)
        m = re.search(r"РЕЗЕРВ\s+(ORD-[A-Z0-9]+)", upper)
        if m:
            return await self._supplier_reserved(m.group(1))
        m = re.search(r"ОТМЕНА\s+(ORD-[A-Z0-9]+)", upper)
        if m:
            return await self._supplier_cancelled(m.group(1), raw_text)
        return None

    async def reset_history(self, chat_id: int) -> None:
        await clear_conversation_history(chat_id)

    # ── Groq loop ─────────────────────────────────────────────────────────────

    async def _run_loop(self, messages: list, context_chat_id: int) -> str:
        import asyncio

        working = [{"role": "system", "content": self._system}] + list(messages)

        for _iteration in range(6):  # max 6 tool-call cycles
            response = None
            last_err = None

            for attempt in range(3):
                try:
                    response = await self._client.chat.completions.create(
                        model=self._active_model,
                        messages=working,
                        tools=_TOOLS,
                        tool_choice="auto",
                        max_tokens=512,   # 350→512: даёт полные ответы без обрезки
                        temperature=0.4,  # 0.2→0.4: живее, меньше шаблонности
                    )
                    last_err = None
                    break
                except Exception as exc:
                    last_err = exc
                    err = str(exc).lower()
                    if "rate_limit" in err or "rate limit" in err or "429" in err:
                        if self._active_model != GROQ_MODEL_FALLBACK:
                            logger.warning(
                                "Rate limit on %s → fallback %s",
                                self._active_model, GROQ_MODEL_FALLBACK,
                            )
                            self._active_model = GROQ_MODEL_FALLBACK
                        else:
                            await asyncio.sleep(3)
                        continue
                    if any(k in err for k in ("failed_generation", "overloaded", "timeout", "503")):
                        logger.warning("Groq transient (attempt %d): %s", attempt + 1, exc)
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

            if last_err is not None:
                logger.error("Groq failed after retries: %s", last_err)
                return "Секунду, небольшая техническая задержка — напишите ещё раз."

            choice = response.choices[0]

            if choice.finish_reason != "tool_calls":
                content = choice.message.content or ""
                return content.strip() or "Чем могу помочь?"

            # Build assistant message dict explicitly (avoid model_dump issues)
            tool_calls_list = []
            for tc in (choice.message.tool_calls or []):
                tool_calls_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })
            working.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": tool_calls_list,
            })

            for tc in (choice.message.tool_calls or []):
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = await self._exec(tc.function.name, args, context_chat_id)
                logger.info("Tool %s → %.120s", tc.function.name, result)
                working.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        return "Произошла ошибка — попробуйте ещё раз."

    # ── Tool dispatcher ────────────────────────────────────────────────────────

    async def _exec(self, name: str, args: dict, chat_id: int) -> str:
        try:
            match name:
                case "create_order":
                    return await self._create_order(args, chat_id)
                case "notify_supplier":
                    return await self._notify_supplier(args["order_id"], args["message"])
                case "get_order_info":
                    return await self._get_order_info(args["order_id"])
                case "get_client_orders":
                    return await self._get_client_orders(args.get("client_chat_id", chat_id))
                case _:
                    return f"Неизвестный инструмент: {name}"
        except Exception as exc:
            logger.exception("Tool %s error", name)
            return f"Ошибка: {exc}"

    # ── Tool implementations ───────────────────────────────────────────────────

    async def _create_order(self, inp: dict, default_chat_id: int) -> str:
        quantity = inp.get("quantity", 0)
        unit_price = inp.get("unit_price", 0)
        if not isinstance(quantity, int) or quantity <= 0:
            return "Ошибка: количество должно быть целым числом больше нуля."
        if not isinstance(unit_price, (int, float)) or unit_price <= 0:
            return "Ошибка: цена должна быть положительным числом."
        if not inp.get("product_name", "").strip():
            return "Ошибка: не указан товар."
        order_id = await db_create_order({
            "client_chat_id": inp.get("client_chat_id", default_chat_id),
            "client_name":    inp.get("client_name", ""),
            "client_contact": inp.get("client_contact", ""),
            "product_id":     "",
            "product_name":   inp["product_name"],
            "quantity":       inp["quantity"],
            "unit_price":     inp["unit_price"],
            "notes":          inp.get("notes", ""),
        })
        total = inp["unit_price"] * inp["quantity"]
        return (
            f"Заказ создан: {order_id}\n"
            f"Товар: {inp['product_name']} × {inp['quantity']} = {total:,.0f} ₽\n"
            f"Клиент: {inp.get('client_name','')} / {inp.get('client_contact','')}"
        )

    async def _notify_supplier(self, order_id: str, message: str) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."
        full_msg = (
            f"🔔 НОВЫЙ ЗАКАЗ {order_id}\n\n{message}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
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
            except Exception as e:
                logger.error("Supplier TG failed: %s", e)
        if SUPPLIER_EMAIL and not sent:
            try:
                await self._send_email(
                    to=SUPPLIER_EMAIL,
                    subject=f"Заказ {order_id}",
                    body=full_msg,
                )
                sent.append("Email")
            except Exception as e:
                logger.error("Supplier email failed: %s", e)
        if sent:
            await update_order(order_id, {"supplier_notified": 1})
            return f"Поставщик уведомлён ({', '.join(sent)})."
        return "⚠️ Не удалось уведомить поставщика. Проверьте SUPPLIER_TELEGRAM_CHAT_ID в .env"

    async def _get_order_info(self, order_id: str) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."
        return (
            f"Заказ {order['id']}\n"
            f"Товар: {order['product_name']} × {order['quantity']}\n"
            f"Сумма: {order['total_price']:,.0f} ₽\n"
            f"Статус: {STATUS_LABELS.get(order['status'], order['status'])}\n"
            f"Создан: {order['created_at'][:10]}"
        )

    async def _get_client_orders(self, client_chat_id: int) -> str:
        orders = await get_client_orders(client_chat_id)
        if not orders:
            return "Активных заказов нет."
        lines = [f"Заказов: {len(orders)}"]
        for o in orders:
            lines.append(f"• {o['id']} — {o['product_name']} × {o['quantity']} [{o['status']}]")
        return "\n".join(lines)

    # ── Supplier reply handlers ────────────────────────────────────────────────

    async def _supplier_confirmed(self, order_id: str, raw: str) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {
            "status": "confirmed",
            "supplier_confirmed": 1,
            "notes": f"Подтверждено: {raw[:200]}",
        })
        msg = (
            f"✅ Хорошие новости!\n\n"
            f"Поставщик подтвердил заказ {order_id}.\n"
            f"Товар: {order['product_name']} × {order['quantity']}\n"
            f"Сумма: {order['total_price']:,.0f} ₽\n\n"
            f"Свяжемся для уточнения доставки и оплаты."
        )
        return (order["client_chat_id"], msg)

    async def _supplier_reserved(self, order_id: str) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {"status": "reserved"})
        msg = (
            f"🔒 Заказ {order_id} зарезервирован!\n\n"
            f"Товар: {order['product_name']} × {order['quantity']}\n"
            f"Готов к выдаче. Свяжитесь для оплаты."
        )
        return (order["client_chat_id"], msg)

    async def _supplier_cancelled(self, order_id: str, raw: str) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {
            "status": "cancelled",
            "notes": f"Отменено: {raw[:200]}",
        })
        msg = (
            f"❗ По заказу {order_id} возникла проблема.\n\n"
            f"Товар «{order['product_name']}» временно недоступен.\n"
            f"Рассмотрим альтернативы и свяжемся с вами."
        )
        return (order["client_chat_id"], msg)

    # ── Email ──────────────────────────────────────────────────────────────────

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
