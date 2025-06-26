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
from telegram.error import TelegramError
from dotenv import load_dotenv

# ===== SETUP =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing from .env file!")

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug: Verify if commands are received."""
    logger.info(f"Received /start from {update.effective_user.id}")
    await update.message.reply_text(
        "🔍 Bot is alive!\n"
        "Try /deleteall in a group where I'm admin."
    )

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug: Check if this command triggers."""
    logger.info(f"Received /deleteall from {update.effective_user.id}")
    await update.message.reply_text(
        "⚡ Delete command received!\n"
        "If you don't see further action, check:\n"
        "- Am I a group admin?\n"
        "- Do I have 'Delete Messages' permission?"
    )

# ===== ERROR HANDLING =====
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log all errors."""
    logger.error(f"Update {update} caused error: {context.error}")

# ===== MAIN =====
def main():
    logger.info("Starting bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deleteall", delete_all_messages))
    app.add_error_handler(error_handler)
    
    # Debug: Log all incoming updates
    async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Update received: {update}")
    
    app.add_handler(MessageHandler(filters.ALL, log_updates))
    
    # Start polling
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
