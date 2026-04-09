"""
Groq-powered Telegram sales agent (FREE, no Anthropic API needed).

Model: llama-3.3-70b-versatile via Groq API
Get free API key at: https://console.groq.com  (no credit card required)
Free tier: 14 400 requests/day, 500 000 tokens/minute
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
    MANAGER_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
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
    save_conversation_history,
    update_order,
)

logger = logging.getLogger(__name__)

# ─── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Ты — опытный менеджер по продажам компании {company}. Тебя зовут {name}.

═══ ТВОИ ЗАДАЧИ ═══
1. Консультировать клиентов по товарам, ценам и наличию
2. Предлагать подходящие товары, рассказывать о скидках
3. Оформлять заказы клиентов
4. Немедленно уведомлять поставщика о каждом новом заказе
5. Информировать клиентов о статусе их заказов

═══ СТИЛЬ ОБЩЕНИЯ ═══
• Вежливый, профессиональный тон; обращайся на «Вы»
• Давай конкретные ответы: цена, наличие, срок
• Будь инициативным — предлагай альтернативы и аксессуары
• Не расписывай лишнего — клиент ценит чёткость

═══ ПОРЯДОК РАБОТЫ С ЗАКАЗОМ ═══
1. Клиент хочет купить → уточни количество и контактные данные (имя + телефон или email)
2. Рассчитай цену (учти скидки при опте) через calculate_discount
3. Создай заказ через create_order
4. СРАЗУ уведоми поставщика через notify_supplier
5. Сообщи клиенту номер заказа и что уже уточняешь наличие у поставщика
6. Если клиент спрашивает статус — используй get_order_info

═══ ВАЖНО ═══
• Всегда вызывай notify_supplier сразу после create_order — не пропускай этот шаг
• Если товара нет на складе — всё равно оформляй заказ и уточняй у поставщика
• Номер заказа передавай клиенту в формате ORD-XXXXXXXX\
"""

# ─── Tool definitions (OpenAI/Groq format) ────────────────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Поиск товаров в каталоге по названию или категории.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Полная информация о товаре: описание, цена, наличие, скидки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "ID товара из каталога",
                    }
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Проверить наличие конкретного товара на складе.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Название или часть названия товара",
                    }
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_discount",
            "description": "Рассчитать итоговую цену с учётом оптовых скидок.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "ID товара"},
                    "quantity": {
                        "type": "integer",
                        "description": "Количество единиц",
                    },
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Оформить заказ для клиента и записать в базу.",
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
                        "description": "Телефон или email клиента",
                    },
                    "product_id": {
                        "type": "string",
                        "description": "ID товара (если известен)",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Название товара",
                    },
                    "quantity": {"type": "integer", "description": "Количество"},
                    "unit_price": {
                        "type": "number",
                        "description": "Цена за единицу (уже с учётом скидки)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Примечания к заказу",
                    },
                },
                "required": [
                    "client_chat_id",
                    "client_name",
                    "product_name",
                    "quantity",
                    "unit_price",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_supplier",
            "description": (
                "Отправить поставщику уведомление о заказе через Telegram или email. "
                "Вызывать сразу после create_order."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "ID заказа"},
                    "message": {
                        "type": "string",
                        "description": "Текст сообщения поставщику: товар, количество, контакт клиента",
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
            "description": "Получить информацию о заказе по его ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID заказа, например ORD-AB12CD34",
                    }
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
                    }
                },
                "required": ["client_chat_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_order_status",
            "description": "Обновить статус заказа (например, после подтверждения поставщика).",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "ID заказа"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "new",
                            "confirmed",
                            "in_stock",
                            "reserved",
                            "shipped",
                            "completed",
                            "cancelled",
                        ],
                        "description": "Новый статус",
                    },
                    "notes": {"type": "string", "description": "Комментарий"},
                },
                "required": ["order_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_client_notification",
            "description": "Отправить клиенту проактивное сообщение (например, о подтверждении заказа).",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_chat_id": {
                        "type": "integer",
                        "description": "Telegram chat_id клиента",
                    },
                    "message": {"type": "string", "description": "Текст сообщения"},
                },
                "required": ["client_chat_id", "message"],
            },
        },
    },
]


# ─── Agent class ───────────────────────────────────────────────────────────────


class SalesAgent:
    """Groq-powered sales manager agent (FREE tier)."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._system = _SYSTEM_PROMPT.format(company=COMPANY_NAME, name=MANAGER_NAME)
        self._bot = None

    def set_bot(self, bot) -> None:
        self._bot = bot

    # ── Public entry points ────────────────────────────────────────────────────

    async def process_message(
        self, chat_id: int, text: str, user_name: str = "Клиент"
    ) -> str:
        history = await get_conversation_history(chat_id)
        history.append({"role": "user", "content": text})

        reply = await self._run_loop(history, context_chat_id=chat_id)

        history.append({"role": "assistant", "content": reply})
        await save_conversation_history(chat_id, history, user_name)
        return reply

    async def process_supplier_message(
        self, raw_text: str
    ) -> Optional[tuple[int, str]]:
        upper = raw_text.upper()

        m = re.search(r"ПОДТВЕРЖДАЮ\s+(ORD-[A-Z0-9]+)", upper)
        if m:
            return await self._handle_supplier_confirmation(m.group(1), raw_text)

        m = re.search(r"РЕЗЕРВ\s+(ORD-[A-Z0-9]+)", upper)
        if m:
            return await self._handle_supplier_reservation(m.group(1))

        m = re.search(r"ОТМЕНА\s+(ORD-[A-Z0-9]+)", upper)
        if m:
            return await self._handle_supplier_cancellation(m.group(1), raw_text)

        return None

    async def reset_history(self, chat_id: int) -> None:
        await clear_conversation_history(chat_id)

    # ── Groq agentic loop ──────────────────────────────────────────────────────

    async def _run_loop(self, messages: list, context_chat_id: int) -> str:
        """Run Groq tool-use loop; return final text response."""
        working = [{"role": "system", "content": self._system}] + list(messages)

        for _ in range(10):  # safety cap
            response = await self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=working,
                tools=_TOOLS,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.4,
            )

            choice = response.choices[0]

            # No tool calls → final answer
            if choice.finish_reason != "tool_calls":
                return choice.message.content or "Готово."

            # Append assistant message with tool_calls
            working.append(choice.message.model_dump())

            # Execute each tool call
            for tool_call in choice.message.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                result = await self._execute_tool(
                    tool_call.function.name, args, context_chat_id
                )
                logger.info("Tool %s → %s", tool_call.function.name, result[:80])

                working.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "Произошла техническая ошибка. Пожалуйста, попробуйте снова."

    # ── Tool dispatcher ────────────────────────────────────────────────────────

    async def _execute_tool(
        self, name: str, inputs: dict, context_chat_id: int
    ) -> str:
        logger.info("Tool call: %s %s", name, inputs)
        try:
            match name:
                case "search_products":
                    return self._tool_search_products(inputs["query"])
                case "get_product_details":
                    return self._tool_get_product_details(inputs["product_id"])
                case "check_availability":
                    return self._tool_check_availability(inputs["product_name"])
                case "calculate_discount":
                    return self._tool_calculate_discount(
                        inputs["product_id"], inputs["quantity"]
                    )
                case "create_order":
                    return await self._tool_create_order(inputs)
                case "notify_supplier":
                    return await self._tool_notify_supplier(
                        inputs["order_id"], inputs["message"]
                    )
                case "get_order_info":
                    return await self._tool_get_order_info(inputs["order_id"])
                case "get_client_orders":
                    return await self._tool_get_client_orders(
                        inputs["client_chat_id"]
                    )
                case "update_order_status":
                    return await self._tool_update_order_status(
                        inputs["order_id"],
                        inputs["status"],
                        inputs.get("notes", ""),
                    )
                case "send_client_notification":
                    return await self._tool_send_client_notification(
                        inputs["client_chat_id"], inputs["message"]
                    )
                case _:
                    return f"Неизвестный инструмент: {name}"
        except Exception as exc:
            logger.exception("Tool %s raised an error", name)
            return f"Ошибка инструмента {name}: {exc}"

    # ── Tool implementations (same logic, no changes needed) ──────────────────

    def _tool_search_products(self, query: str) -> str:
        products = load_products()
        q = query.lower()
        matches = [
            p for p in products
            if q in p["name"].lower()
            or q in p.get("category", "").lower()
            or q in p.get("description", "").lower()
        ]
        if not matches:
            return f"Товары по запросу «{query}» не найдены."
        lines = [f"Найдено: {len(matches)} товар(ов)\n"]
        for p in matches[:10]:
            stock = f"{p['stock']} {p.get('unit','шт')}" if p["stock"] > 0 else "нет в наличии"
            lines.append(
                f"• {p['name']} (ID: {p['id']})\n"
                f"  Цена: {p['price']:,.0f} ₽ | {stock}"
            )
        return "\n".join(lines)

    def _tool_get_product_details(self, product_id: str) -> str:
        products = load_products()
        p = next((x for x in products if x["id"] == product_id), None)
        if not p:
            return f"Товар с ID «{product_id}» не найден."
        discounts = p.get("discounts", {})
        disc_block = ""
        if discounts:
            rows = [f"  от {k}: −{v}%" for k, v in discounts.items()]
            disc_block = "\nОптовые скидки:\n" + "\n".join(rows)
        return (
            f"Товар: {p['name']}\n"
            f"ID: {p['id']}\n"
            f"Описание: {p.get('description','—')}\n"
            f"Цена: {p['price']:,.0f} ₽ / {p.get('unit','шт')}\n"
            f"На складе: {p['stock']} {p.get('unit','шт')}\n"
            f"Категория: {p.get('category','—')}\n"
            f"Артикул поставщика: {p.get('supplier_sku','—')}"
            f"{disc_block}"
        )

    def _tool_check_availability(self, product_name: str) -> str:
        products = load_products()
        q = product_name.lower()
        matches = [p for p in products if q in p["name"].lower()]
        if not matches:
            return f"Товар «{product_name}» не найден в каталоге."
        lines = []
        for p in matches:
            if p["stock"] > 0:
                lines.append(f"✅ {p['name']}: {p['stock']} {p.get('unit','шт')} в наличии")
            else:
                lines.append(f"⏳ {p['name']}: нет на складе (уточним у поставщика)")
        return "\n".join(lines)

    def _tool_calculate_discount(self, product_id: str, quantity: int) -> str:
        products = load_products()
        p = next((x for x in products if x["id"] == product_id), None)
        if not p:
            return f"Товар с ID «{product_id}» не найден."
        base = p["price"]
        disc = 0
        for threshold_str, pct in p.get("discounts", {}).items():
            threshold = int(threshold_str.replace("+", ""))
            if quantity >= threshold:
                disc = max(disc, pct)
        if disc:
            final = base * (1 - disc / 100)
            total = final * quantity
            return (
                f"{p['name']}\n"
                f"Базовая цена: {base:,.0f} ₽\n"
                f"Скидка {disc}% → {final:,.0f} ₽/шт\n"
                f"Итого за {quantity} шт: {total:,.0f} ₽"
            )
        total = base * quantity
        return (
            f"{p['name']}\n"
            f"Цена: {base:,.0f} ₽/шт\n"
            f"Итого за {quantity} шт: {total:,.0f} ₽\n"
            f"(скидок для данного объёма нет)"
        )

    async def _tool_create_order(self, inp: dict) -> str:
        order_id = await db_create_order({
            "client_chat_id": inp["client_chat_id"],
            "client_name": inp["client_name"],
            "client_contact": inp.get("client_contact", ""),
            "product_id": inp.get("product_id", ""),
            "product_name": inp["product_name"],
            "quantity": inp["quantity"],
            "unit_price": inp["unit_price"],
            "notes": inp.get("notes", ""),
        })
        total = inp["unit_price"] * inp["quantity"]
        return (
            f"✅ Заказ оформлен!\n"
            f"Номер: {order_id}\n"
            f"Товар: {inp['product_name']}\n"
            f"Кол-во: {inp['quantity']}\n"
            f"Сумма: {total:,.0f} ₽\n"
            f"Клиент: {inp['client_name']} ({inp.get('client_contact','')})"
        )

    async def _tool_notify_supplier(self, order_id: str, message: str) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."
        full_msg = (
            f"🔔 НОВЫЙ ЗАКАЗ {order_id}\n\n"
            f"{message}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Ответьте одной из команд:\n"
            f"ПОДТВЕРЖДАЮ {order_id}\n"
            f"РЕЗЕРВ {order_id}\n"
            f"ОТМЕНА {order_id}"
        )
        notified_via = []
        if SUPPLIER_TELEGRAM_CHAT_ID and self._bot:
            try:
                await self._bot.send_message(
                    chat_id=int(SUPPLIER_TELEGRAM_CHAT_ID), text=full_msg
                )
                notified_via.append("Telegram")
            except Exception as exc:
                logger.error("Supplier Telegram notification failed: %s", exc)
        if SUPPLIER_EMAIL and not notified_via:
            try:
                await self._send_email(
                    to=SUPPLIER_EMAIL,
                    subject=f"Новый заказ {order_id} — {COMPANY_NAME}",
                    body=full_msg,
                )
                notified_via.append("Email")
            except Exception as exc:
                logger.error("Supplier email notification failed: %s", exc)
        if notified_via:
            await update_order(order_id, {"supplier_notified": 1})
            return f"Поставщик уведомлён через {', '.join(notified_via)}."
        return "⚠️ Не удалось уведомить поставщика. Проверьте SUPPLIER_TELEGRAM_CHAT_ID в .env"

    async def _tool_get_order_info(self, order_id: str) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."
        status_labels = {
            "new": "🆕 Новый", "confirmed": "✅ Подтверждён",
            "in_stock": "📦 Есть у поставщика", "reserved": "🔒 Зарезервирован",
            "shipped": "🚚 Отправлен", "completed": "✔️ Завершён",
            "cancelled": "❌ Отменён",
        }
        return (
            f"Заказ: {order['id']}\n"
            f"Клиент: {order.get('client_name','—')} / {order.get('client_contact','—')}\n"
            f"Товар: {order['product_name']}\n"
            f"Кол-во: {order['quantity']}\n"
            f"Цена: {order['unit_price']:,.0f} ₽/шт → итого {order['total_price']:,.0f} ₽\n"
            f"Статус: {status_labels.get(order['status'], order['status'])}\n"
            f"Уведомлён поставщик: {'✅' if order['supplier_notified'] else '⏳'}\n"
            f"Создан: {order['created_at'][:16]}"
        )

    async def _tool_get_client_orders(self, client_chat_id: int) -> str:
        orders = await get_client_orders(client_chat_id)
        if not orders:
            return "Активных заказов нет."
        lines = [f"Активные заказы ({len(orders)}):\n"]
        for o in orders:
            lines.append(
                f"• {o['id']} — {o['product_name']} × {o['quantity']} "
                f"({o['total_price']:,.0f} ₽) [{o['status']}]"
            )
        return "\n".join(lines)

    async def _tool_update_order_status(
        self, order_id: str, status: str, notes: str = ""
    ) -> str:
        order = await get_order(order_id)
        if not order:
            return f"Заказ {order_id} не найден."
        upd: dict = {"status": status}
        if notes:
            upd["notes"] = notes
        await update_order(order_id, upd)
        return f"Статус заказа {order_id} → {status}"

    async def _tool_send_client_notification(
        self, client_chat_id: int, message: str
    ) -> str:
        if not self._bot:
            return "Бот не инициализирован."
        try:
            await self._bot.send_message(chat_id=client_chat_id, text=message)
            return f"Уведомление отправлено клиенту {client_chat_id}."
        except Exception as exc:
            return f"Не удалось отправить уведомление: {exc}"

    # ── Supplier reply handlers ────────────────────────────────────────────────

    async def _handle_supplier_confirmation(
        self, order_id: str, raw_text: str
    ) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {
            "status": "confirmed",
            "supplier_confirmed": 1,
            "notes": f"Подтверждено поставщиком: {raw_text[:200]}",
        })
        msg = (
            f"✅ Хорошие новости!\n\n"
            f"Поставщик подтвердил ваш заказ #{order_id}.\n"
            f"Товар: {order['product_name']} × {order['quantity']}\n"
            f"Сумма: {order['total_price']:,.0f} ₽\n\n"
            f"Товар зарезервирован. Скоро свяжемся для уточнения доставки и оплаты."
        )
        return (order["client_chat_id"], msg)

    async def _handle_supplier_reservation(
        self, order_id: str
    ) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {"status": "reserved"})
        msg = (
            f"🔒 Ваш заказ #{order_id} зарезервирован!\n\n"
            f"Товар: {order['product_name']} × {order['quantity']}\n"
            f"Готов к выдаче. Свяжитесь с нами для согласования оплаты и доставки."
        )
        return (order["client_chat_id"], msg)

    async def _handle_supplier_cancellation(
        self, order_id: str, raw_text: str
    ) -> Optional[tuple[int, str]]:
        order = await get_order(order_id)
        if not order:
            return None
        await update_order(order_id, {
            "status": "cancelled",
            "notes": f"Отменено поставщиком: {raw_text[:200]}",
        })
        msg = (
            f"❗ К сожалению, по заказу #{order_id} возникла проблема.\n\n"
            f"Товар «{order['product_name']}» временно недоступен у поставщика.\n"
            f"Мы рассмотрим альтернативные варианты и свяжемся с вами."
        )
        return (order["client_chat_id"], msg)

    # ── Email helper ───────────────────────────────────────────────────────────

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
