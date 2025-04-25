import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter, BadRequest
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
REQUIRED_CHANNEL = "@sr_robots"  # Change to your channel username

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await query.edit_message_text(
                "✅ Thanks for joining!\n\n"
                "Now you can use /deleteall in any group where I'm admin.\n"
                "I'll delete all messages starting from the /deleteall command."
            )
        else:
            await query.answer("You haven't joined the channel yet!", show_alert=True)
    except Exception as e:
        await query.answer("Error checking membership. Please try again.", show_alert=True)

async def verify_membership(user_id):
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    # Check channel membership
    if not await verify_membership(update.effective_user.id):
        await update.message.reply_text(
            f"❌ You must join {REQUIRED_CHANNEL} first!\n\n"
            "Please join and try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")]
            ])
        )
        return
        
    # Rest of your deletion code...
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
            current_msg -= 1
            
            if deleted % batch_size == 0:
                await asyncio.sleep(1)
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
                
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except BadRequest as e:
            if "message to delete not found" in str(e):
                current_msg -= 1
                continue
            break
        except Exception as e:
            print(f"Error: {e}")
            break
    
    await status_msg.edit_text(f"✅ Finished! Deleted {deleted} messages")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.add_handler(CallbackQueryHandler(check_membership, pattern="^check_membership$"))
    
    application.run_polling()

if __name__ == '__main__':
    main()
