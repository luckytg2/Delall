import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import RetryAfter, BadRequest
from dotenv import load_dotenv

# ===== Load Environment Variables =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing from .env file!")

# ===== Logging =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start from {update.effective_user.id}")
    await update.message.reply_text(
        "🤖 *Admin-Safe Message Deleter*\n\n"
        "Commands:\n"
        "/test - Check bot\n"
        "/deleteall - Delete non-admin messages\n\n"
        "⚠️ *Bot needs admin & delete permissions*",
        parse_mode="Markdown"
    )

# ===== /test =====
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/test from {update.effective_user.id}")
    await update.message.reply_text("✅ Bot is running!")

# ===== /deleteall =====
async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    bot = context.bot

    if not chat or chat.type == "private":
        await update.message.reply_text("❌ Use this command in a group.")
        return

    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ I need admin + delete permissions.")
            return

        status_msg = await chat.send_message("🔄 Deleting non-admin messages...")
        current_msg_id = update.message.message_id - 1
        deleted, skipped = 0, 0

        while current_msg_id > 0:
            try:
                message = await bot.get_message(chat.id, current_msg_id)

                # Skip the bot's own status message
                if current_msg_id == status_msg.message_id:
                    current_msg_id -= 1
                    continue

                is_admin = False
                if message.sender_chat:  # Anonymous admin
                    is_admin = True
                elif message.from_user:
                    member = await bot.get_chat_member(chat.id, message.from_user.id)
                    is_admin = member.status in ["administrator", "creator"]

                if is_admin:
                    skipped += 1
                else:
                    await bot.delete_message(chat.id, current_msg_id)
                    deleted += 1

            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except BadRequest as e:
                if "not found" not in str(e):
                    logger.warning(f"BadRequest: {e}")
            except Exception as e:
                logger.error(f"Error at {current_msg_id}: {e}")

            current_msg_id -= 1

            if (deleted + skipped) % 20 == 0:
                try:
                    await status_msg.edit_text(f"🗑️ Deleted: {deleted} | Skipped: {skipped}")
                except:
                    pass

        await status_msg.edit_text(f"✅ Done!\nDeleted: {deleted}\nSkipped (admins): {skipped}")
        await asyncio.sleep(5)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Main deletion error: {e}")
        await chat.send_message("❌ Deletion failed. Check logs.")

# ===== MAIN =====
def main():
    logger.info("Bot is starting...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("deleteall", delete_all_messages))

    async def log_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.debug(f"Update: {update}")

    app.add_handler(MessageHandler(filters.ALL, log_all))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
