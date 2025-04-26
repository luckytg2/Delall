import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import RetryAfter, BadRequest
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
REQUIRED_CHANNEL = "@sr_robots"

# Persistent verification storage
verified_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
    ])
    
    await update.message.reply_text(
        "🤖 <b>Message Cleaner Bot</b>\n\n"
        "🔹 <b>Commands:</b>\n"
        "/deleteall - Delete all messages from this point\n"
        "/deletefrom - Delete from specific message (reply to message)\n\n"
        "⚠️ <b>You must join and verify first:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, query.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            verified_users.add(query.from_user.id)
            await query.edit_message_text(
                "✅ <b>Verification Successful!</b>\n\n"
                "You can now use deletion commands in groups where I'm admin.\n\n"
                "<b>Available commands:</b>\n"
                "/deleteall - Delete all messages from command point\n"
                "/deletefrom - Delete from specific message (reply to message)",
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ You haven't properly joined the channel!", show_alert=True)
    except Exception as e:
        print(f"Verification error: {e}")
        await query.answer("⚠️ Couldn't verify. Try again later.", show_alert=True)

async def check_membership(user_id):
    return user_id in verified_users

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_membership(user_id):
        await update.message.reply_text(
            "❌ You must complete verification first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Verify Now", callback_data="verify_join")]
            ])
        )
        return
        
    chat_id = update.effective_chat.id
    bot = context.bot
    
    # Check if bot is admin
    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges with delete rights!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error checking admin status: {e}")
        return
    
    # Start actual deletion
    start_msg = update.message.message_id
    status_msg = await update.message.reply_text("⚡ Starting message deletion...")
    deleted = 0
    
    # Delete messages in batches
    for current_msg in range(start_msg, 0, -1):
        try:
            await bot.delete_message(chat_id, current_msg)
            deleted += 1
            # Update progress every 20 deletions
            if deleted % 20 == 0:
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
                await asyncio.sleep(0.3)  # Rate limiting
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except BadRequest:  # Message not found
            continue
        except Exception as e:
            print(f"Deletion error: {e}")
            break
    
    await status_msg.edit_text(f"✅ Successfully deleted {deleted} messages")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    
    print("🚀 Bot is running and ready...")
    application.run_polling()

if __name__ == '__main__':
    main()
