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
    GROQ_MODEL_FALLBACK,
    MANAGER_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    SUPPLIER_API_KEY,
    SUPPLIER_API_URL,
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

# ─── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Ты — {name}, менеджер по продажам компании «{company}». Живой, опытный, приятный в общении человек.

═══ ХАРАКТЕР И СТИЛЬ ═══
• Тёплый, но деловой. Не сухой чиновник и не назойливый продавец — просто хороший знакомый, который разбирается в товаре.
• Обращайся на «Вы», но без формализма. «Отличный выбор», «Хорошая идея», «Давайте разберёмся» — это твой стиль.
• Короткие ёмкие ответы. Клиент не читает романы — 3–5 предложений максимум на обычный вопрос.
• Используй цифры и конкретику: «8 штук есть прямо сейчас», «скидка 7% — выходит 57 600 ₽ за штуку».
• Иногда уместно лёгкое одобрение: «Хороший выбор — надёжная модель», но без лести.
• Никогда не говори «Я языковая модель» или «Я ИИ». Ты — {name}, и точка.

═══ КАК ОТВЕЧАТЬ НА РАЗНЫЕ СИТУАЦИИ ═══

На приветствие («привет», «здравствуйте»):
→ Ответь тепло, спроси чем можешь помочь. Одно-два предложения.

На вопрос о товаре:
→ Сначала вызови search_products или get_product_details, потом ответь.
→ Назови цену, наличие и главное преимущество. Предложи 1 альтернативу если уместно.

На вопрос о цене:
→ Сразу называй цену. Если есть оптовые скидки — упомяни («от 5 штук — минус 5%»).

На сравнение товаров:
→ Сделай краткую таблицу или список «плюсов» каждого. Порекомендуй конкретный.

На возражение «дорого»:
→ Не спорь. Уточни бюджет, предложи более доступный вариант или объясни ценность.

На «буду думать» / «позже»:
→ Не дави. «Конечно, я здесь — как надумаете, пишите.»

═══ ФОТО И ХАРАКТЕРИСТИКИ ═══
• Фото товара — ТОЛЬКО если клиент явно просит: «покажи», «фото», «как выглядит», «картинку».
  Без запроса фото не отправлять.
• Характеристики ищи через search_product_specs когда клиент спрашивает «что внутри»,
  «какие параметры», «технические характеристики». Представь кратким списком.

═══ ДОПРОДАЖИ И АКСЕССУАРЫ ═══
• После выбора основного товара ненавязчиво предложи 1–2 сопутствующих (кабели к монитору, мышь к ноутбуку, сумку).
• Один раз — не повторяй если клиент отказал.

═══ ПОРЯДОК ОФОРМЛЕНИЯ ЗАКАЗА ═══
1. Клиент готов купить → уточни количество (если не сказал) и имя + телефон/email
2. Вызови calculate_discount — рассчитай итоговую сумму с учётом скидок
3. Озвучь итоговую сумму клиенту и попроси подтвердить
4. После подтверждения → create_order → СРАЗУ notify_supplier
5. Скажи клиенту номер заказа (ORD-XXXXXXXX) и что уже уточняешь наличие у поставщика
6. Если спрашивает статус → get_order_info

═══ СИНХРОНИЗАЦИЯ ОСТАТКОВ ═══
• Если настроен API поставщика — используй sync_stock для получения актуальных остатков перед ответом о наличии.
• Если товара нет в наших остатках — всё равно оформляй заказ, поставщик уточнит наличие.

═══ КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО — ЧИТАЙ ВНИМАТЕЛЬНО ═══
• НИКОГДА не называй цену из своих знаний. Цена — ТОЛЬКО из результата search_products.
• НИКОГДА не говори что товара нет если не вызвал search_products и не убедился.
• НИКОГДА не придумывай модели, бренды, характеристики из головы.
• Если search_products не нашёл — скажи "уточню у поставщика" или предложи похожее что нашёл.
• Называть себя ботом, ИИ или программой запрещено.

КАТАЛОГ ТОВАРОВ (актуальные данные):
{catalog_summary}\
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
    {
        "type": "function",
        "function": {
            "name": "search_product_image",
            "description": (
                "Найти и отправить клиенту фото товара из открытых источников (без вотермарок поставщика). "
                "Вызывай когда клиент спрашивает как выглядит товар, или при первом упоминании конкретного товара. "
                "Фото отправляется прямо в чат клиенту."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Полное название товара для поиска фото (на русском или английском)",
                    },
                    "client_chat_id": {
                        "type": "integer",
                        "description": "Telegram chat_id клиента, которому отправить фото",
                    },
                },
                "required": ["product_name", "client_chat_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_product_specs",
            "description": (
                "Найти технические характеристики товара в интернете. "
                "Используй когда клиент спрашивает характеристики, параметры, спецификации, "
                "или когда в каталоге недостаточно информации о товаре."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Полное название товара для поиска характеристик",
                    },
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_stock",
            "description": (
                "Получить актуальные остатки напрямую с API поставщика. "
                "Используй перед ответом о наличии, если клиент спрашивает «есть ли сейчас», «сколько в наличии». "
                "Возвращает список товаров с актуальными остатками от поставщика."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Артикул (supplier_sku) конкретного товара. Если пустой — получить все остатки.",
                    }
                },
                "required": [],
            },
        },
    },
]


# ─── Agent class ───────────────────────────────────────────────────────────────


class SalesAgent:
    """Groq-powered sales manager agent (FREE tier)."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._bot = None
        self._active_model = GROQ_MODEL  # switches to fallback on rate limit
        self._system = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt with live catalog summary so the model knows what's available."""
        products = reload_products()
        if not products:
            catalog_summary = (
                "⚠️ КАТАЛОГ ПУСТ. Скажи клиенту что уточняешь наличие у поставщика "
                "и предложи перезвонить. НЕ придумывай товары."
            )
        else:
            # Build category → brands/count summary
            from collections import defaultdict
            cat_data: dict = defaultdict(list)
            for p in products:
                cat = p.get("category") or "Без категории"
                brand = ""
                # Extract brand from name (first word often is brand)
                words = p["name"].split()
                if len(words) >= 2:
                    brand = words[0]
                if brand and brand not in cat_data[cat]:
                    cat_data[cat].append(brand)

            lines = [f"В каталоге {len(products)} товаров в {len(cat_data)} категориях:"]
            for cat, brands in sorted(cat_data.items()):
                brands_str = ", ".join(brands[:6])
                if len(brands) > 6:
                    brands_str += f" и ещё {len(brands)-6}"
                lines.append(f"• {cat}: {brands_str}")
            lines.append(
                "\nДля поиска ВСЕГДА вызывай search_products с ключевым словом "
                "(например 'фен', 'утюг', 'холодильник', 'Babyliss')."
            )
            catalog_summary = "\n".join(lines)

        return _SYSTEM_PROMPT.format(
            company=COMPANY_NAME,
            name=MANAGER_NAME,
            catalog_summary=catalog_summary,
        )

    def set_bot(self, bot) -> None:
        self._bot = bot

    # ── Public entry points ────────────────────────────────────────────────────

    async def process_message(
        self, chat_id: int, text: str, user_name: str = "Клиент"
    ) -> str:
        history = await get_conversation_history(chat_id)

        # RAG: find relevant products BEFORE calling LLM.
        # This guarantees the model uses catalog data instead of its training knowledge.
        catalog_ctx = self._rag_search(text)
        if catalog_ctx:
            # Inject as hidden system note inside user turn
            augmented = (
                f"{text}\n\n"
                f"[ДАННЫЕ ИЗ КАТАЛОГА — используй ТОЛЬКО эти цены и наличие, "
                f"не придумывай ничего своего]\n{catalog_ctx}"
            )
            history.append({"role": "user", "content": augmented})
        else:
            history.append({"role": "user", "content": text})

        reply = await self._run_loop(history, context_chat_id=chat_id)

        # Save original text (without injected catalog) to keep history clean
        history[-1] = {"role": "user", "content": text}
        history.append({"role": "assistant", "content": reply})
        await save_conversation_history(chat_id, history, user_name)
        return reply

    def _rag_search(self, text: str) -> str:
        """Pre-search catalog by keywords in user message (Retrieval-Augmented Generation).
        Returns formatted product list to inject into the LLM context."""
        products = load_products()
        if not products:
            return ""

        # Strip common stop-words, keep meaningful tokens (len > 2)
        _STOP = {
            "нужен","нужна","нужно","хочу","хочет","хотим","дайте","покажи","есть",
            "ли","что","как","где","сколько","стоит","цена","цены","покажи","расскажи",
            "меня","интересует","интересуют","нас","мне","нам","вас","вам","у","в",
            "на","и","или","но","так","не","это","который","которая","которые",
            "про","для","от","до","по","за","при","под","над","без","из","со",
        }
        words = [
            w for w in re.split(r"[\s,./!?()\[\]]+", text.lower())
            if len(w) > 2 and w not in _STOP
        ]
        if not words:
            return ""

        scored: list[tuple[int, dict]] = []
        for p in products:
            name_l    = p["name"].lower()
            cat_l     = p.get("category", "").lower()
            desc_l    = p.get("description", "").lower()
            sku_l     = p.get("supplier_sku", "").lower()
            haystack  = f"{name_l} {cat_l} {desc_l} {sku_l}"
            score = 0
            for w in words:
                if w in name_l:
                    score += 3
                elif w in cat_l:
                    score += 2
                elif w in haystack:
                    score += 1
            if score > 0:
                scored.append((score, p))

        if not scored:
            return ""

        scored.sort(key=lambda x: (-x[0], x[1]["price"]))
        top = scored[:12]

        lines = [f"Найдено {len(scored)} позиций в каталоге:"]
        for _, p in top:
            stock_str = f"{p['stock']} шт" if p["stock"] > 0 else "под заказ"
            lines.append(
                f"• {p['name']} | {p['price']:.2f} ₽ | {stock_str} | арт: {p.get('supplier_sku','—')}"
            )
        if len(scored) > 12:
            lines.append(f"... и ещё {len(scored) - 12} позиций")
        return "\n".join(lines)

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
        import asyncio
        working = [{"role": "system", "content": self._system}] + list(messages)

        for iteration in range(10):  # safety cap
            # ── Retry up to 3x on transient Groq errors ───────────────────────
            response = None
            last_err = None
            for attempt in range(3):
                try:
                    response = await self._client.chat.completions.create(
                        model=self._active_model,
                        messages=working,
                        tools=_TOOLS,
                        tool_choice="auto",
                        max_tokens=1024,
                        temperature=0.3,
                    )
                    last_err = None
                    break
                except Exception as exc:
                    last_err = exc
                    err_str = str(exc).lower()
                    # Rate limit → switch to fallback model immediately
                    if "rate_limit" in err_str or "rate limit" in err_str:
                        if self._active_model != GROQ_MODEL_FALLBACK:
                            logger.warning(
                                "Rate limit on %s → switching to fallback %s",
                                self._active_model, GROQ_MODEL_FALLBACK,
                            )
                            self._active_model = GROQ_MODEL_FALLBACK
                        else:
                            logger.error("Rate limit on fallback model too: %s", exc)
                            await asyncio.sleep(5)
                        continue
                    if any(k in err_str for k in (
                        "failed_generation", "service_unavailable",
                        "timeout", "overloaded",
                    )):
                        logger.warning("Groq transient error (attempt %d/3): %s", attempt + 1, exc)
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break  # non-retryable, don't retry

            # ── If all retries failed → try once more without tools ────────────
            if last_err is not None:
                logger.error("Groq error after 3 attempts: %s", last_err)
                try:
                    fallback = await self._client.chat.completions.create(
                        model=self._active_model,
                        messages=working,
                        max_tokens=512,
                        temperature=0.3,
                    )
                    return fallback.choices[0].message.content or (
                        "Добрый день! Уточните, пожалуйста, что вас интересует?"
                    )
                except Exception as fallback_err:
                    logger.error("Fallback also failed: %s", fallback_err)
                    return (
                        "Добрый день! Сервис чуть перегружен — напишите ещё раз "
                        "через 30 секунд, я отвечу."
                    )

            choice = response.choices[0]

            # No tool calls → final answer
            if choice.finish_reason != "tool_calls":
                content = choice.message.content or ""
                return content if content.strip() else "Готово."

            # ── Append assistant message — explicit dict (safer than model_dump) ─
            tool_calls_raw = []
            for tc in (choice.message.tool_calls or []):
                tool_calls_raw.append({
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
                "tool_calls": tool_calls_raw,
            })

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
                case "search_product_image":
                    return await self._tool_search_product_image(
                        inputs["product_name"],
                        inputs.get("client_chat_id", context_chat_id),
                    )
                case "search_product_specs":
                    return await self._tool_search_product_specs(inputs["product_name"])
                case "sync_stock":
                    return await self._tool_sync_stock(inputs.get("sku", ""))
                case _:
                    return f"Неизвестный инструмент: {name}"
        except Exception as exc:
            logger.exception("Tool %s raised an error", name)
            return f"Ошибка инструмента {name}: {exc}"

    # ── Tool implementations (same logic, no changes needed) ──────────────────

    def _tool_search_products(self, query: str) -> str:
        products = load_products()
        if not products:
            return "⚠️ Каталог пуст. Запустите import_excel.py чтобы загрузить прайс."

        # Word-based scoring search
        words = [w for w in re.split(r"[\s,./\\-]+", query.lower()) if len(w) > 1]
        if not words:
            return "Пустой поисковый запрос."

        scored = []
        for p in products:
            name_l   = p["name"].lower()
            cat_l    = p.get("category", "").lower()
            desc_l   = p.get("description", "").lower()
            sku_l    = p.get("supplier_sku", "").lower()
            haystack = f"{name_l} {cat_l} {desc_l} {sku_l}"
            score = 0
            for w in words:
                if w in name_l:
                    score += 3
                elif w in cat_l:
                    score += 2
                elif w in haystack:
                    score += 1
            if score > 0:
                scored.append((score, p))

        if not scored:
            return (
                f"Товары по запросу «{query}» не найдены в каталоге.\n"
                f"Всего в каталоге: {len(products)} позиций.\n"
                f"Попробуй другое ключевое слово (например: бренд или тип товара)."
            )

        scored.sort(key=lambda x: (-x[0], x[1]["price"]))
        top = [p for _, p in scored[:15]]

        lines = [f"Найдено: {len(scored)} позиций по запросу «{query}»\n"]
        for p in top:
            stock_str = f"✅ {p['stock']} {p.get('unit','шт')}" if p["stock"] > 0 else "⏳ под заказ"
            lines.append(
                f"• {p['name']} (ID: {p['id']})\n"
                f"  Цена: {p['price']:,.2f} ₽ | {stock_str}"
            )
        if len(scored) > 15:
            lines.append(f"\n...и ещё {len(scored)-15} позиций. Уточни запрос.")
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

    async def _tool_search_product_image(
        self, product_name: str, client_chat_id: int
    ) -> str:
        """Search a clean product image online and send it to the client via Telegram."""
        try:
            import asyncio
            import io
            from duckduckgo_search import DDGS

            # Prioritise manufacturer/review sites, skip marketplaces with watermarks
            query = (
                f"{product_name} product photo"
                " -site:aliexpress.com -site:ebay.com -site:avito.ru"
                " -site:wildberries.ru -site:ozon.ru"
            )

            def _ddg_images():
                with DDGS() as ddgs:
                    return list(ddgs.images(
                        keywords=query,
                        max_results=15,
                        size="Medium",
                        type_image="photo",
                    ))

            results = await asyncio.to_thread(_ddg_images)

            if not results:
                return f"Фото для «{product_name}» не найдено в открытых источниках."

            import aiohttp
            async with aiohttp.ClientSession() as session:
                for result in results:
                    img_url = result.get("image", "")
                    source = result.get("url", "")
                    if not img_url:
                        continue
                    # Skip obviously watermarked / low-quality sources
                    skip_domains = ("aliexpress", "ebay", "avito", "wildberries", "ozon", "taobao")
                    if any(d in img_url.lower() for d in skip_domains):
                        continue
                    try:
                        async with session.get(
                            img_url,
                            timeout=aiohttp.ClientTimeout(total=10),
                            headers={"User-Agent": "Mozilla/5.0"},
                        ) as resp:
                            if resp.status != 200:
                                continue
                            content_type = resp.headers.get("Content-Type", "")
                            if "image" not in content_type:
                                continue
                            img_bytes = await resp.read()
                            if len(img_bytes) < 5000:   # skip tiny/broken images
                                continue
                            await self._bot.send_photo(
                                chat_id=client_chat_id,
                                photo=io.BytesIO(img_bytes),
                                caption=f"📷 {product_name}",
                            )
                            return f"Фото товара «{product_name}» отправлено клиенту."
                    except Exception:
                        continue

            # Fallback: send URL directly (Telegram can fetch it)
            for result in results:
                img_url = result.get("image", "")
                if img_url:
                    try:
                        await self._bot.send_photo(
                            chat_id=client_chat_id,
                            photo=img_url,
                            caption=f"📷 {product_name}",
                        )
                        return f"Фото товара «{product_name}» отправлено клиенту."
                    except Exception:
                        continue

            return f"Не удалось отправить фото «{product_name}» — все источники недоступны."

        except ImportError:
            return "Установите библиотеку: pip install duckduckgo-search"
        except Exception as exc:
            logger.error("search_product_image error: %s", exc)
            return f"Ошибка поиска фото: {exc}"

    async def _tool_search_product_specs(self, product_name: str) -> str:
        """Search product specifications online via DuckDuckGo and return key specs."""
        try:
            import asyncio
            from duckduckgo_search import DDGS

            def _ddg_text():
                with DDGS() as ddgs:
                    return list(ddgs.text(
                        keywords=f"{product_name} характеристики технические specifications",
                        max_results=6,
                        region="ru-ru",
                    ))

            results = await asyncio.to_thread(_ddg_text)

            if not results:
                # Try in English if Russian search yielded nothing
                def _ddg_text_en():
                    with DDGS() as ddgs:
                        return list(ddgs.text(
                            keywords=f"{product_name} full specifications",
                            max_results=6,
                        ))
                results = await asyncio.to_thread(_ddg_text_en)

            if not results:
                return f"Характеристики для «{product_name}» не найдены в открытых источниках."

            # Build a context blob for the LLM to summarize
            lines = [
                f"Данные из интернета по запросу «{product_name} характеристики».\n"
                "Извлеки из этого текста ключевые технические параметры и представь "
                "клиенту в виде краткого структурированного списка.\n"
            ]
            for r in results[:4]:
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                if body:
                    lines.append(f"[{title}] ({href})\n{body}\n")

            return "\n".join(lines)

        except ImportError:
            return "Установите библиотеку: pip install duckduckgo-search"
        except Exception as exc:
            logger.error("search_product_specs error: %s", exc)
            return f"Ошибка поиска характеристик: {exc}"

    async def _tool_sync_stock(self, sku: str = "") -> str:
        """Fetch live stock from supplier API (SUPPLIER_API_URL + SUPPLIER_API_KEY)."""
        if not SUPPLIER_API_URL:
            return (
                "API поставщика не настроен. "
                "Укажите SUPPLIER_API_URL и SUPPLIER_API_KEY в файле .env"
            )
        try:
            import aiohttp
            headers = {}
            if SUPPLIER_API_KEY:
                headers["Authorization"] = f"Bearer {SUPPLIER_API_KEY}"
                headers["X-Api-Key"] = SUPPLIER_API_KEY

            url = SUPPLIER_API_URL.rstrip("/")
            params = {}
            if sku:
                # Try common parameter names for SKU filtering
                params["sku"] = sku
                params["article"] = sku

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return f"API поставщика вернул ошибку {resp.status}."
                    data = await resp.json(content_type=None)

            # ── Parse common API response formats ────────────────────────────
            items = []

            # Format 1: {"items": [...]} or {"products": [...]} or {"data": [...]}
            if isinstance(data, dict):
                for key in ("items", "products", "data", "stock", "goods", "result"):
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                if not items and all(isinstance(v, (int, float)) for v in data.values()):
                    # Format 2: {"SKU-001": 10, "SKU-002": 5}
                    items = [{"sku": k, "stock": v} for k, v in data.items()]

            # Format 3: list of objects directly
            elif isinstance(data, list):
                items = data

            if not items:
                return f"API поставщика ответил, но данные не распознаны. Ответ: {str(data)[:300]}"

            # ── Update local products.json with fresh stock levels ────────────
            from database import load_products
            import json as _json

            products = load_products()
            product_map = {p["supplier_sku"].lower(): p for p in products if p.get("supplier_sku")}
            updated = []

            for item in items:
                # Detect SKU field
                item_sku = (
                    item.get("sku") or item.get("article") or item.get("artikul")
                    or item.get("code") or item.get("id") or ""
                ).lower()
                # Detect stock field
                item_stock = (
                    item.get("stock") or item.get("quantity") or item.get("qty")
                    or item.get("count") or item.get("balance") or item.get("остаток") or 0
                )
                try:
                    item_stock = int(item_stock)
                except (TypeError, ValueError):
                    item_stock = 0

                if item_sku and item_sku in product_map:
                    old = product_map[item_sku]["stock"]
                    product_map[item_sku]["stock"] = item_stock
                    updated.append(
                        f"  {product_map[item_sku]['name']}: {old} → {item_stock} шт"
                    )

            if updated:
                # Save updated products.json
                from config import PRODUCTS_FILE
                with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
                    _json.dump({"products": products}, f, ensure_ascii=False, indent=2)
                return (
                    f"✅ Остатки обновлены ({len(updated)} позиций):\n"
                    + "\n".join(updated)
                )

            return (
                f"API ответил ({len(items)} позиций), но совпадений с нашим каталогом "
                f"по полю supplier_sku не найдено. Проверьте артикулы в products.json."
            )

        except ImportError:
            return "Установите aiohttp: pip install aiohttp"
        except Exception as exc:
            logger.error("sync_stock error: %s", exc)
            return f"Ошибка при обращении к API поставщика: {exc}"

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
