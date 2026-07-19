"""
Telegram Sales Agent — entry point.

Run:
    python main.py

The bot handles:
  • Client messages  → forwarded to SalesAgent (Claude)
  • Supplier replies → parsed for order confirmations / reservations
  • /start           → welcome message
  • /orders          → list active orders for the calling client
  • /clear           → reset conversation history
  • /help            → usage hints
"""

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import COMPANY_NAME, GROQ_API_KEY, MANAGER_NAME, STATUS_LABELS, SUPPLIER_TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
from database import get_client_orders, init_db
from sales_agent import SalesAgent

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

agent = SalesAgent()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _send_long(update: Update, text: str) -> None:
    """Send a message, splitting at 4096 chars if needed."""
    for i in range(0, len(text), 4096):
        await update.message.reply_text(text[i : i + 4096])


def _is_supplier(chat_id: int) -> bool:
    return bool(SUPPLIER_TELEGRAM_CHAT_ID) and str(chat_id) == str(SUPPLIER_TELEGRAM_CHAT_ID)


# ─── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name or "клиент"
    text = (
        f"Здравствуйте, {name}! 👋\n\n"
        f"Я — {MANAGER_NAME}, менеджер по продажам компании *{COMPANY_NAME}*.\n\n"
        f"Помогу вам с:\n"
        f"• Подбором и консультацией по товарам\n"
        f"• Ценами, наличием и скидками\n"
        f"• Оформлением и отслеживанием заказов\n\n"
        f"Просто напишите, что вас интересует!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    orders = await get_client_orders(chat_id)
    if not orders:
        await update.message.reply_text("У вас нет активных заказов.")
        return

    lines = ["📋 *Ваши активные заказы:*\n"]
    for o in orders:
        status = STATUS_LABELS.get(o["status"], o["status"])
        lines.append(
            f"*{o['id']}*\n"
            f"  {o['product_name']} × {o['quantity']} = {o['total_price']:,.0f} ₽\n"
            f"  Статус: {status}\n"
            f"  Создан: {o['created_at'][:10]}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await agent.reset_history(update.effective_chat.id)
    await update.message.reply_text(
        "История диалога очищена. Начнём с чистого листа! 🔄"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "ℹ️ *Доступные команды:*\n\n"
        "/start — приветствие\n"
        "/orders — мои активные заказы\n"
        "/clear — сбросить историю диалога\n"
        "/reload — перезагрузить каталог товаров\n"
        "/help — эта справка\n\n"
        "Для консультации просто пишите в чат."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reload product catalog from products.json without restarting the bot."""
    count = agent.refresh()
    await update.message.reply_text(
        f"✅ Каталог перезагружен: {count} товаров.",
    )


# ─── Message handlers ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    text = update.message.text
    user = update.effective_user
    user_name = (user.full_name or user.first_name or "Клиент") if user else "Клиент"

    # Route supplier messages separately
    if _is_supplier(chat_id):
        await _handle_supplier(update, context, text)
        return

    # Typing status is cosmetic and must not block the actual reply.
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except TelegramError as exc:
        logger.warning("Could not send typing indicator for chat_id=%s: %s", chat_id, exc)

    try:
        reply = await agent.process_message(
            chat_id=chat_id, text=text, user_name=user_name
        )
        await _send_long(update, reply)
    except Exception:
        logger.exception("Error processing message from chat_id=%s", chat_id)
        await update.message.reply_text(
            "Извините, возникла техническая ошибка. Попробуйте ещё раз."
        )


async def _handle_supplier(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    """Process a message from the supplier chat."""
    logger.info("Supplier message: %.120s", text)

    result = await agent.process_supplier_message(text)
    if result:
        client_chat_id, notification = result
        try:
            await context.bot.send_message(chat_id=client_chat_id, text=notification)
            await update.message.reply_text("✅ Клиент уведомлён.")
            logger.info("Client %s notified about order update.", client_chat_id)
        except Exception as exc:
            logger.error("Failed to notify client %s: %s", client_chat_id, exc)
            await update.message.reply_text(
                f"⚠️ Клиент не найден или бот заблокирован: {exc}"
            )
    else:
        # Nothing matched — acknowledge receipt
        await update.message.reply_text(
            "Сообщение получено.\n\n"
            "Для обновления статуса заказа используйте команды:\n"
            "ПОДТВЕРЖДАЮ ORD-XXXXXXXX\n"
            "РЕЗЕРВ ORD-XXXXXXXX\n"
            "ОТМЕНА ORD-XXXXXXXX"
        )


# ─── Startup / main ────────────────────────────────────────────────────────────

async def _post_init(application: Application) -> None:
    """Called once after the Application is fully built."""
    await init_db()
    agent.set_bot(application.bot)
    me = await application.bot.get_me()
    logger.info(
        "Bot @%s started | manager=%s | company=%s",
        me.username,
        MANAGER_NAME,
        COMPANY_NAME,
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env — aborting.")
        raise SystemExit(1)
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set in .env — get free key at https://console.groq.com")
        raise SystemExit(1)

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling for updates…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
