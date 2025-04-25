import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import RetryAfter, BadRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
REQUIRED_CHANNEL = "@sr_robots"  # Your channel username

# Store user join status in memory (replaces MongoDB)
user_status = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_status[user.id] = False  # Default not joined
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_membership")]
    ])
    
    await update.message.reply_text(
        "🤖 <b>Message Cleaner Bot</b>\n\n"
        "🔹 <b>Commands:</b>\n"
        "/start - Show this message\n"
        "/deleteall - Delete all messages\n\n"
        "⚠️ <b>You must join our channel first:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, query.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            user_status[query.from_user.id] = True
            await query.edit_message_text("✅ Thanks for joining! You can now use /deleteall.")
        else:
            await query.answer("You haven't joined the channel yet!", show_alert=True)
    except Exception as e:
        await query.answer("Error checking membership. Please try again.", show_alert=True)

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not user_status.get(user_id, False):
        await update.message.reply_text(
            f"❌ You must join {REQUIRED_CHANNEL} first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")]
            ])
        )
        return
        
    chat_id = update.effective_chat.id
    bot = context.bot
    
    # Admin check
    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Admin check failed: {e}")
        return
    
    # Deletion logic
    start_msg = update.message.message_id
    status_msg = await update.message.reply_text("⚡ Starting deletion...")
    deleted = 0
    
    for current_msg in range(start_msg, 0, -1):
        try:
            await bot.delete_message(chat_id, current_msg)
            deleted += 1
            if deleted % 20 == 0:  # Update progress every 20 deletions
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
                await asyncio.sleep(0.5)  # Rate limiting
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except BadRequest:  # Message not found
            continue
        except Exception as e:
            print(f"Error: {e}")
            break
    
    await status_msg.edit_text(f"✅ Finished! Deleted {deleted} messages")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.add_handler(CallbackQueryHandler(check_membership, pattern="^check_membership$"))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
