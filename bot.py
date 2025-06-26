import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import RetryAfter, BadRequest, Conflict, TelegramError
from dotenv import load_dotenv

# ===== Configuration =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in .env file!")

# ===== Logging Setup =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== Bot Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with instructions."""
    await update.message.reply_text(
        "🤖 **Admin-Safe Message Deleter Bot**\n\n"
        "🔹 **Command:** `/deleteall`\n"
        "   - Deletes *non-admin* messages\n"
        "   - Skips admin/anonymous posts\n\n"
        "⚠️ *Requirements:*\n"
        "- Add me as admin\n"
        "- Enable 'Delete Messages' permission",
        parse_mode="Markdown"
    )

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all non-admin messages in the chat."""
    chat = update.effective_chat
    user = update.effective_user
    bot = context.bot

    # Command validation
    if not update.message or not chat:
        logger.warning("Invalid update received")
        return

    # Private chat check
    if chat.type == "private":
        await update.message.reply_text("❌ This command works only in groups!")
        return

    try:
        # Verify bot is admin
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                "❌ I need admin privileges with:\n"
                "- 'Delete Messages' permission\n"
                "- 'Anonymous' admin rights (if needed)"
            )
            return

        # Start process
        status_msg = await chat.send_message("⚡ Starting deletion (skipping admins)...")
        start_msg_id = update.message.message_id
        current_msg_id = start_msg_id - 1  # Start from message before command
        deleted = 0
        skipped = 0
        batch_size = 20  # Update status every N messages

        while current_msg_id > 0:
            try:
                # Skip status message
                if current_msg_id == status_msg.message_id:
                    current_msg_id -= 1
                    continue

                # Get message info
                message = await bot.get_message(chat.id, current_msg_id)
                
                # Check if sender is admin
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

            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except BadRequest as e:
                if "not found" not in str(e) and "can't be deleted" not in str(e):
                    logger.warning(f"Error deleting {current_msg_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

            current_msg_id -= 1

            # Periodic status updates
            if (deleted + skipped) % batch_size == 0:
                try:
                    await status_msg.edit_text(
                        f"⏳ Progress:\n"
                        f"Deleted: {deleted}\n"
                        f"Skipped (admins): {skipped}"
                    )
                except:
                    pass

        # Final report
        await status_msg.edit_text(
            f"✅ Completed!\n"
            f"Total deleted: {deleted}\n"
            f"Admin messages preserved: {skipped}"
        )
        await asyncio.sleep(5)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        await chat.send_message("❌ Deletion failed due to an error. Check logs.")

# ===== Main Application =====
def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("deleteall", delete_all_messages))
        
        # Error handler
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Update {update} caused error: {context.error}")
            
        app.add_error_handler(error_handler)
        
        logger.info("Starting bot...")
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )

    except Conflict:
        logger.error("Another bot instance is already running!")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")

if __name__ == "__main__":
    main()
