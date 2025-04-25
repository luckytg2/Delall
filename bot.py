from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import time

# Replace with your bot token
BOT_TOKEN = '8168443954:AAEfkUjLCAejSjfllVvYbaf1-q2LPLOXwe8'

def delete_all_messages(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    bot = context.bot
    
    # Check if bot is admin (simplified check)
    if not update.effective_chat.get_member(bot.id).status == 'administrator':
        update.message.reply_text("I need to be an admin to delete messages!")
        return
    
    # Get the last message ID to start from
    last_message = update.message.message_id
    
    # Delete messages in a loop
    while True:
        try:
            # Delete messages in batches
            for msg_id in range(last_message, last_message - 100, -1):
                try:
                    bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    # Message might not exist or no permission
                    pass
            
            last_message -= 100
            time.sleep(1)  # Avoid rate limiting
            
        except Exception as e:
            print(f"Error: {e}")
            break

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("deleteall", delete_all_messages))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
