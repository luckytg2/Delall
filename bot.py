import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import RetryAfter, BadRequest
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if BOT_TOKEN is None:
    raise ValueError("No BOT_TOKEN provided in .env file!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    await update.message.reply_text(
        "👋 Welcome to the Message Deleter Bot!\n\n"
        "Available Commands:\n"
        "/deleteall - Delete all messages in this chat.\n"
        "\n⚠️ Make sure I have admin permissions with delete rights.\n JOIN @SR_ROBOTS"
    )

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    bot = context.bot

    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Admin check failed: {e}")
        return

    start_msg = update.message.message_id
    status_msg = await update.message.reply_text("⚡ Starting deletion...")

    deleted = 0
    batch_size = 30
    current_msg = start_msg

    while current_msg > 1:
        try:
            await bot.delete_message(chat_id, current_msg)
            deleted += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except BadRequest as e:
            if "message to delete not found" in str(e).lower():
                pass
            else:
                break
        except Exception as e:
            print(f"Error: {e}")
            break

        current_msg -= 1

        if deleted % batch_size == 0:
            try:
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
            except BadRequest:
                pass
            await asyncio.sleep(1)

    try:
        await status_msg.edit_text(f"✅ Finished! Deleted {deleted} messages")
    except BadRequest:
        pass

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.run_polling()

if __name__ == '__main__':
    main()
