import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import RetryAfter, BadRequest, TelegramError
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in .env file or environment variables!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    try:
        await update.message.reply_text(
            "👋 Welcome to the Message Deleter Bot!\n\n"
            "Available Commands:\n"
            "/deleteall - Delete all recent non-admin messages in this chat.\n"
            "\n⚠️ Make sure I have admin permissions with delete rights."
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /deleteall command."""
    if not update.message:
        logger.warning("Deleteall command received without message")
        return

    chat = update.effective_chat
    if not chat:
        logger.warning("No chat found in update")
        return

    try:
        bot = context.bot
        me = await bot.get_me()
        logger.info(f"Processing /deleteall in chat {chat.id} by user {update.effective_user.id}")

        # Check bot admin status
        try:
            chat_member = await bot.get_chat_member(chat.id, me.id)
            if chat_member.status not in ['administrator', 'creator']:
                await chat.send_message("❌ I need admin privileges to delete messages!")
                return
        except TelegramError as e:
            await chat.send_message(f"⚠️ Admin check failed: {e}")
            logger.error(f"Admin check failed: {e}")
            return

        start_msg = update.message.message_id
        status_msg = await chat.send_message("⚡ Starting deletion (skipping admin messages)...")
        logger.info(f"Starting deletion from message {start_msg}")

        deleted = 0
        skipped = 0
        batch_size = 30
        current_msg = start_msg - 1  # Start from one before the command message

        while current_msg > 1:
            if current_msg == status_msg.message_id:
                current_msg -= 1
                continue

            try:
                message = await bot.get_message(chat.id, current_msg)
                
                # Skip admin messages (including anonymous)
                if message.sender_chat or (message.from_user and 
                    (await bot.get_chat_member(chat.id, message.from_user.id)).status in ['administrator', 'creator']):
                    skipped += 1
                    current_msg -= 1
                    continue
                    
                await bot.delete_message(chat.id, current_msg)
                deleted += 1
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except BadRequest as e:
                if "not found" not in str(e) and "can't be deleted" not in str(e):
                    logger.warning(f"Error deleting {current_msg}: {e}")
            except TelegramError as e:
                logger.error(f"Error processing message {current_msg}: {e}")

            current_msg -= 1

            if (deleted + skipped) % batch_size == 0:
                try:
                    await status_msg.edit_text(f"⏳ Deleted {deleted}, skipped {skipped}...")
                except TelegramError:
                    pass
                await asyncio.sleep(1)

        # Final status
        try:
            await status_msg.edit_text(f"✅ Finished! Deleted {deleted}, skipped {skipped}")
        except TelegramError:
            pass

        # Clean up status after delay
        await asyncio.sleep(5)
        try:
            await bot.delete_message(chat.id, status_msg.message_id)
        except TelegramError:
            pass

    except Exception as e:
        logger.error(f"Unexpected error in delete_all: {e}", exc_info=True)
        try:
            await chat.send_message("❌ An error occurred during deletion!")
        except:
            pass

def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("deleteall", delete_all_messages))
        
        logger.info("Bot starting...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")

if __name__ == '__main__':
    main()
