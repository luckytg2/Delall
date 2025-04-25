import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import time
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

BOT_TOKEN = os.getenv('BOT_TOKEN')

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    chat_id = update.effective_chat.id
    bot = context.bot
    
    # Admin check
    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges with delete permissions!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error checking admin status: {e}")
        return
    
    last_message = update.message.message_id
    await update.message.reply_text("🚀 Starting message deletion...")
    
    deleted_count = 0
    while True:
        try:
            for msg_id in range(last_message, max(last_message - 100, 1), -1):
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted_count += 1
                except:
                    continue
            
            last_message -= 100
            time.sleep(0.5)  # Respect rate limits
            
        except Exception as e:
            print(f"Stopping: {e}")
            break
    
    await update.message.reply_text(f"✅ Deleted {deleted_count} messages!")

def main():
    if not BOT_TOKEN:
        raise ValueError("No BOT_TOKEN set in environment variables")
        
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
