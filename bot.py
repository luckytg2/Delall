import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import RetryAfter, BadRequest, TelegramError
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in .env file or environment variables!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    try:
        await update.message.reply_text(
            "👋 Welcome to the Admin-Safe Message Cleaner!\n\n"
            "Commands:\n"
            "/clean - Delete non-admin messages\n"
            "\n⚠️ I need admin rights with delete permission!"
        )
    except Exception as e:
        print(f"Start command error: {e}")

async def get_chat_admins(bot, chat_id):
    """Get set of admin user IDs."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return {admin.user.id for admin in admins}
    except Exception as e:
        print(f"Admin fetch error: {e}")
        return set()

async def is_anonymous_admin(message):
    """Check if message is from anonymous admin."""
    try:
        return (message.sender_chat and 
                message.sender_chat.id == message.chat.id and
                message.sender_chat.type == "channel")
    except:
        return False

async def clean_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /clean command."""
    if not update.message:
        return

    chat = update.effective_chat
    bot = context.bot

    try:
        # Verify bot is admin
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await chat.send_message("❌ I'm not an admin! Promote me first.")
            return
        if not bot_member.can_delete_messages:
            await chat.send_message("❌ I need message delete permission!")
            return

        admin_ids = await get_chat_admins(bot, chat.id)
        if not admin_ids:
            await chat.send_message("⚠️ Couldn't fetch admin list. Aborting.")
            return

        status_msg = await chat.send_message("⚡ Cleaning non-admin messages...")
        deleted = 0
        current_msg = update.message.message_id - 1  # Start from previous message

        while current_msg > 0:
            if current_msg == status_msg.message_id:
                current_msg -= 1
                continue

            try:
                msg = await bot.get_message(chat.id, current_msg)
                
                # Skip admin and anonymous admin messages
                if ((msg.from_user and msg.from_user.id in admin_ids) or 
                    await is_anonymous_admin(msg)):
                    current_msg -= 1
                    continue
                    
                await bot.delete_message(chat.id, current_msg)
                deleted += 1

                # Update status every 20 deletions
                if deleted % 20 == 0:
                    try:
                        await status_msg.edit_text(f"🧹 Deleted {deleted} messages...")
                    except:
                        pass
                    await asyncio.sleep(1)

            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except BadRequest:
                pass  # Message already deleted or inaccessible
            except TelegramError as e:
                print(f"Error processing message {current_msg}: {e}")
            finally:
                current_msg -= 1

        await status_msg.edit_text(f"✅ Cleaned {deleted} non-admin messages")
        await asyncio.sleep(5)
        await status_msg.delete()

    except Exception as e:
        print(f"Clean error: {e}")
        try:
            await chat.send_message(f"❌ Error: {str(e)}")
        except:
            pass

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("clean", clean_messages))
        
        print("Bot is running...")
        app.run_polling()
    except Exception as e:
        print(f"Bot failed to start: {e}")

if __name__ == '__main__':
    main()
