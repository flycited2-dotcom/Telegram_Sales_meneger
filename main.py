"""Telegram sales bot entry point."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import (
    ADMIN_CHAT_IDS,
    COMPANY_NAME,
    GROQ_API_KEY,
    MANAGER_NAME,
    STATUS_LABELS,
    SUPPLIER_TELEGRAM_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
)
from database import (
    add_order_event,
    get_client_orders,
    get_order,
    get_order_events,
    init_db,
    list_recent_leads,
    search_leads,
    update_order,
)
from sales_agent import SalesAgent

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

agent = SalesAgent()


def _log_preview(text: str | None, limit: int = 300) -> str:
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


async def _send_long(update: Update, text: str) -> None:
    for i in range(0, len(text), 4096):
        await update.message.reply_text(text[i : i + 4096])


async def _safe_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception as exc:
        logger.warning("Typing action skipped for chat_id=%s: %s", chat_id, exc)


def _is_supplier(chat_id: int) -> bool:
    return bool(SUPPLIER_TELEGRAM_CHAT_ID) and str(chat_id) == str(SUPPLIER_TELEGRAM_CHAT_ID)


def _is_admin(update: Update) -> bool:
    if not ADMIN_CHAT_IDS:
        return False
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    return chat_id in ADMIN_CHAT_IDS or user_id in ADMIN_CHAT_IDS


async def _admin_only(update: Update) -> bool:
    if _is_admin(update):
        return True
    if update.message:
        await update.message.reply_text("Команда доступна только администратору.")
    return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name or "клиент"
    text = (
        f"Здравствуйте, {name}.\n\n"
        f"Я — {MANAGER_NAME}, менеджер компании {COMPANY_NAME}.\n"
        f"Помогу с подбором товара, ценой, наличием и оформлением заказа.\n\n"
        "Напишите, что нужно подобрать."
    )
    await update.message.reply_text(text)


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    orders = await get_client_orders(chat_id)
    if not orders:
        await update.message.reply_text("У вас нет активных заказов.")
        return

    lines = ["Ваши активные заказы:\n"]
    for order in orders:
        status = STATUS_LABELS.get(order["status"], order["status"])
        lines.append(
            f"{order['id']}\n"
            f"{order['product_name']} x {order['quantity']} = {order['total_price']:,.2f} ₽\n"
            f"Статус: {status}\n"
            f"Создан: {order['created_at'][:10]}\n"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await agent.reset_history(update.effective_chat.id)
    await update.message.reply_text("История диалога очищена.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Доступные команды:\n\n"
        "/start — приветствие\n"
        "/orders — мои активные заказы\n"
        "/clear — сбросить историю диалога\n"
        "/reload — перезагрузить каталог\n"
        "/help — эта справка\n\n"
        "Команды администратора:\n"
        "/leads [запрос] — последние лиды или поиск\n"
        "/order <ID> — подробности и события заказа\n"
        "/ship <ID> — отметить заказ как отгруженный\n"
        "/complete <ID> — отметить заказ как завершённый\n"
        "/cancelorder <ID> — отменить заказ вручную"
    )
    await update.message.reply_text(text)


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = agent.refresh()
    await update.message.reply_text(f"Каталог перезагружен: {count} товаров.")


async def cmd_leads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _admin_only(update):
        return
    query = " ".join(context.args).strip()
    leads = await search_leads(query) if query else await list_recent_leads()
    if not leads:
        await update.message.reply_text("Лиды не найдены.")
        return

    lines = ["Лиды:\n"]
    for lead in leads[:20]:
        lines.append(
            f"chat_id={lead['chat_id']} | стадия={lead['stage']} | "
            f"имя={lead.get('client_name') or '-'} | контакт={lead.get('client_contact') or '-'}\n"
            f"интересы={', '.join(lead.get('interested_product_ids', [])[:3]) or '-'}\n"
            f"summary={lead.get('summary') or '-'}\n"
        )
    await _send_long(update, "\n".join(lines))


async def cmd_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _admin_only(update):
        return
    if not context.args:
        await update.message.reply_text("Использование: /order ORD-XXXXXXXX")
        return

    order_id = context.args[0].strip().upper()
    order = await get_order(order_id)
    if not order:
        await update.message.reply_text(f"Заказ {order_id} не найден.")
        return

    events = await get_order_events(order_id)
    lines = [
        f"Заказ: {order['id']}",
        f"Клиент: {order.get('client_name') or '-'} / {order.get('client_contact') or '-'}",
        f"Товар: {order['product_name']}",
        f"Количество: {order['quantity']}",
        f"Сумма: {order['total_price']:,.2f} ₽",
        f"Статус: {STATUS_LABELS.get(order['status'], order['status'])}",
        f"Комментарий: {order.get('notes') or '-'}",
        "",
        "События:",
    ]
    if events:
        for event in events[-10:]:
            lines.append(f"{event['created_at'][:19]} | {event['event_type']} | {event['source']} | {event['payload'] or '-'}")
    else:
        lines.append("Нет событий.")
    await _send_long(update, "\n".join(lines))


async def _set_order_status(update: Update, order_id: str, status: str, event_type: str) -> None:
    order = await get_order(order_id)
    if not order:
        await update.message.reply_text(f"Заказ {order_id} не найден.")
        return
    await update_order(order_id, {"status": status})
    await add_order_event(order_id, event_type=event_type, source="admin")
    await update.message.reply_text(f"Заказ {order_id} переведён в статус {STATUS_LABELS.get(status, status)}.")


async def cmd_ship(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _admin_only(update):
        return
    if not context.args:
        await update.message.reply_text("Использование: /ship ORD-XXXXXXXX")
        return
    await _set_order_status(update, context.args[0].strip().upper(), "shipped", "shipped")


async def cmd_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _admin_only(update):
        return
    if not context.args:
        await update.message.reply_text("Использование: /complete ORD-XXXXXXXX")
        return
    await _set_order_status(update, context.args[0].strip().upper(), "completed", "completed")


async def cmd_cancelorder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _admin_only(update):
        return
    if not context.args:
        await update.message.reply_text("Использование: /cancelorder ORD-XXXXXXXX")
        return
    await _set_order_status(update, context.args[0].strip().upper(), "cancelled", "cancelled_by_admin")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    text = update.message.text
    user = update.effective_user
    user_name = (user.full_name or user.first_name or "Клиент") if user else "Клиент"
    logger.info(
        "Incoming message | chat_id=%s | user=%s | text=%s",
        chat_id,
        user_name,
        _log_preview(text),
    )

    if _is_supplier(chat_id):
        await _handle_supplier(update, context, text)
        return

    await _safe_typing(context, chat_id)
    try:
        reply = await agent.process_message(chat_id=chat_id, text=text, user_name=user_name)
        logger.info(
            "Outgoing reply | chat_id=%s | user=%s | text=%s",
            chat_id,
            user_name,
            _log_preview(reply, limit=500),
        )
        await _send_long(update, reply)
    except Exception:
        logger.exception("Error processing message from chat_id=%s", chat_id)
        await update.message.reply_text("Возникла техническая ошибка. Попробуйте ещё раз.")


async def _handle_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    logger.info(
        "Supplier message | chat_id=%s | text=%s",
        update.effective_chat.id if update.effective_chat else None,
        _log_preview(text),
    )
    result = await agent.process_supplier_message(text)
    if result:
        client_chat_id, notification = result
        try:
            logger.info(
                "Supplier notification to client | chat_id=%s | text=%s",
                client_chat_id,
                _log_preview(notification, limit=500),
            )
            await context.bot.send_message(chat_id=client_chat_id, text=notification)
            await update.message.reply_text("Клиент уведомлен.")
        except Exception as exc:
            logger.error("Failed to notify client %s: %s", client_chat_id, exc)
            await update.message.reply_text(f"Не удалось уведомить клиента: {exc}")
    else:
        await update.message.reply_text(
            "Сообщение получено.\n\n"
            "Для обновления статуса заказа используйте:\n"
            "ПОДТВЕРЖДАЮ ORD-XXXXXXXX\n"
            "РЕЗЕРВ ORD-XXXXXXXX\n"
            "ОТМЕНА ORD-XXXXXXXX"
        )


async def _post_init(application: Application) -> None:
    await init_db()
    agent.set_bot(application.bot)
    me = await application.bot.get_me()
    logger.info("Bot @%s started | manager=%s | company=%s", me.username, MANAGER_NAME, COMPANY_NAME)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        raise SystemExit(1)
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set in .env")
        raise SystemExit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("leads", cmd_leads))
    app.add_handler(CommandHandler("order", cmd_order))
    app.add_handler(CommandHandler("ship", cmd_ship))
    app.add_handler(CommandHandler("complete", cmd_complete))
    app.add_handler(CommandHandler("cancelorder", cmd_cancelorder))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
