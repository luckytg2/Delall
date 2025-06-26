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
    await update.effective_chat.send_message(
        "👋 Welcome to the Message Deleter Bot!\n\n"
        "Available Commands:\n"
        "/deleteall - Delete all recent non-admin messages in this chat.\n"
        "\n⚠️ Make sure I have admin permissions with delete rights."
    )

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /deleteall command."""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    bot = context.bot

    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.effective_chat.send_message("❌ I need admin privileges to delete messages!")
            return
    except Exception as e:
        await update.effective_chat.send_message(f"⚠️ Admin check failed: {e}")
        return

    start_msg = update.message.message_id
    status_msg = await update.effective_chat.send_message("⚡ Starting deletion (skipping admin messages)...")

    deleted = 0
    skipped = 0
    batch_size = 30
    current_msg = start_msg - 1  # Start from one before the command message

    while current_msg > 1:
        # Skip the status message
        if current_msg == status_msg.message_id:
            current_msg -= 1
            continue

        try:
            # Get message information
            message = await bot.get_message(chat_id, current_msg)
            
            # Skip if message was sent by an admin or anonymously
            if message.sender_chat or (message.from_user and 
                                       (await bot.get_chat_member(chat_id, message.from_user.id)).status in ['administrator', 'creator']):
                skipped += 1
                current_msg -= 1
                continue
                
            await bot.delete_message(chat_id, current_msg)
            deleted += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except BadRequest as e:
            if "Message to delete not found" not in str(e) and "message can't be deleted" not in str(e):
                print(f"Error deleting message {current_msg}: {e}")
            pass  # Message not found or cannot delete, just skip
        except Exception as e:
            print(f"Error: {e}")
            pass

        current_msg -= 1

        if (deleted + skipped) % batch_size == 0:
            try:
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages, skipped {skipped} admin messages...")
            except BadRequest:
                pass
            await asyncio.sleep(1)

    # Final status update
    try:
        await status_msg.edit_text(f"✅ Finished! Deleted {deleted} messages, skipped {skipped} admin messages")
    except BadRequest:
        pass

    # Optional: clean up status message after 5 seconds
    await asyncio.sleep(5)
    try:
        await bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.run_polling()

if __name__ == '__main__':
    main()
