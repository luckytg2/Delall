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

# Storage
verified_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
    ])
    
    await update.message.reply_text(
        "🤖 <b>Message Cleaner Bot</b>\n\n"
        "🔹 <b>Commands:</b>\n"
        "/deleteall - Delete all messages\n"
        "/deletefrom - Delete from specific message\n\n"
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
                "You can now use /deleteall in groups where I'm admin.",
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ You haven't properly joined the channel!", show_alert=True)
    except Exception as e:
        print(f"Verification error: {e}")
        await query.answer("⚠️ Couldn't verify. Try again later.", show_alert=True)

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verify membership
    if user_id not in verified_users:
        await update.message.reply_text(
            "❌ You must complete verification first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Verify Now", callback_data="verify_join")]
            ])
        )
        return
    
    # Check admin privileges
    try:
        chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges with delete rights!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error checking admin status: {e}")
        return
    
    # Start actual deletion
    start_msg = update.message.message_id
    status_msg = await update.message.reply_text("⚡ Starting deletion...")
    deleted = 0
    
    # Delete messages in batches (fixed syntax here)
    for current_msg in range(start_msg, max(start_msg - 1000, -1), -1):  # Limit to 1000 messages
        try:
            await context.bot.delete_message(chat_id, current_msg)
            deleted += 1
            if deleted % 20 == 0:  # Update progress every 20 messages
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
                await asyncio.sleep(0.3)  # Rate limiting
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except BadRequest:  # Message not found
            continue
        except Exception as e:
            print(f"Error deleting message {current_msg}: {e}")
            break
    
    # Final status update
    if deleted > 0:
        await status_msg.edit_text(f"✅ Successfully deleted {deleted} messages")
    else:
        await status_msg.edit_text("⚠️ No messages were deleted")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    
    print("🤖 Bot is running and ready to delete messages...")
    application.run_polling()

if __name__ == '__main__':
    main()
