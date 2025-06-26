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

# ===== SETUP =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing from .env file!")

# Debug logging (shows EVERYTHING)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with instructions."""
    logger.info(f"/start from {update.effective_user.id}")
    await update.message.reply_text(
        "🤖 **Admin-Safe Message Deleter**\n\n"
        "Commands:\n"
        "/test - Check if bot works\n"
        "/deleteall - Delete non-admin messages\n\n"
        "⚠️ *Requires:* Admin + Delete permissions",
        parse_mode="Markdown"
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple response to verify bot is alive."""
    logger.info(f"/test from {update.effective_user.id}")
    await update.message.reply_text("⚡ Bot is operational!")

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all non-admin messages in the chat."""
    chat = update.effective_chat
    user = update.effective_user
    bot = context.bot

    # Command validation
    if not chat or chat.type == "private":
        await update.message.reply_text("❌ Use this in groups only!")
        return

    try:
        # Verify bot is admin
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ I need admin + delete permissions!")
            return

        status_msg = await chat.send_message("⚡ Deleting non-admin messages...")
        current_msg_id = update.message.message_id - 1  # Start from message before /deleteall
        deleted = 0
        skipped = 0

        while current_msg_id > 0:
            try:
                message = await bot.get_message(chat.id, current_msg_id)
                
                # Skip status messages
                if current_msg_id == status_msg.message_id:
                    current_msg_id -= 1
                    continue
                
                # Skip admin messages (including anonymous)
                is_admin = False
                if message.sender_chat:  # Anonymous admin post
                    is_admin = True
                elif message.from_user:
                    sender = await bot.get_chat_member(chat.id, message.from_user.id)
                    is_admin = sender.status in ["administrator", "creator"]
                
                if is_admin:
                    skipped += 1
                else:
                    await bot.delete_message(chat.id, current_msg_id)
                    deleted += 1

            except RetryAfter as e:  # Rate limit
                await asyncio.sleep(e.retry_after)
            except BadRequest as e:  # Message already deleted
                if "not found" not in str(e):
                    logger.warning(f"Error deleting {current_msg_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

            current_msg_id -= 1

            # Update status every 20 messages
            if (deleted + skipped) % 20 == 0:
                try:
                    await status_msg.edit_text(
                        f"🗑️ Deleted: {deleted} | Skipped: {skipped}"
                    )
                except:
                    pass

        # Final report
        await status_msg.edit_text(
            f"✅ Finished!\n"
            f"Deleted: {deleted}\n"
            f"Skipped (admins): {skipped}"
        )
        await asyncio.sleep(5)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}")
        await chat.send_message("❌ Deletion failed. Check logs.")

# ===== MAIN =====
def main():
    logger.info("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("deleteall", delete_all_messages))
    
    # Log all updates (debug)
    async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.debug(f"Update: {update}")
    app.add_handler(MessageHandler(filters.ALL, log_updates))
    
    # Start polling
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
