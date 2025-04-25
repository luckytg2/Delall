import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import time
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

BOT_TOKEN = os.getenv('BOT_TOKEN')

def delete_all_messages(update: Update, context: CallbackContext):
    if not update.message:
        return
        
    chat_id = update.effective_chat.id
    bot = context.bot
    
    # Admin check
    try:
        if not update.effective_chat.get_member(bot.id).status == 'administrator':
            update.message.reply_text("❌ I need admin privileges with delete permissions!")
            return
    except Exception as e:
        update.message.reply_text(f"⚠️ Error checking admin status: {e}")
        return
    
    last_message = update.message.message_id
    update.message.reply_text("🚀 Starting message deletion...")
    
    deleted_count = 0
    while True:
        try:
            for msg_id in range(last_message, max(last_message - 100, 1), -1):
                try:
                    bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted_count += 1
                except:
                    continue
            
            last_message -= 100
            time.sleep(0.5)  # Respect rate limits
            
        except Exception as e:
            print(f"Stopping: {e}")
            break
    
    update.message.reply_text(f"✅ Deleted {deleted_count} messages!")

def main():
    if not BOT_TOKEN:
        raise ValueError("No BOT_TOKEN set in environment variables")
        
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("deleteall", delete_all_messages))
    
    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
