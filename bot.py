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

# In-memory storage for user join status
user_status = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_status[user.id] = False  # Default not joined
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
    ])
    
    await update.message.reply_text(
        "🤖 <b>Message Cleaner Bot</b>\n\n"
        "🔹 <b>Commands:</b>\n"
        "😄⚠️😒😄😄😁😒⚠️😆🫤😄"
        "/deleteall - Delete all messages\n"
        "/deletefrom - Delete from specific message (reply to message)\n\n"
        "⚠️ <b>You must join our channel first:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # Direct API check of channel membership
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, query.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            user_status[query.from_user.id] = True
            await query.edit_message_text(
                "✅ <b>Verification Successful!</b>\n\n"
                "You can now use deletion commands in groups where I'm admin. USE /deleteall OR /deletefrom",
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ You haven't joined the channel yet!", show_alert=True)
    except Exception as e:
        print(f"Verification error: {e}")
        await query.answer("⚠️ Couldn't verify. Try again later.", show_alert=True)

async def check_membership(user_id, context):
    """Check if user is in required channel"""
    try:
        if user_id in user_status and user_status[user_id]:
            return True
            
        # Double check with Telegram API
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            user_status[user_id] = True
            return True
        return False
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Verify channel membership
    if not await check_membership(user_id, context):
        await update.message.reply_text(
            f"❌ You must join {REQUIRED_CHANNEL} and verify first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
                [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
            ])
        )
        return
        
    # Check bot admin status
    chat_id = update.effective_chat.id
    try:
        chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges with delete rights!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Admin check failed: {e}")
        return
    
    # Start deletion from current message backwards
    start_msg = update.message.message_id
    status_msg = await update.message.reply_text("⚡ Starting deletion...")
    deleted = 0
    
    for current_msg in range(start_msg, 0, -1):
        try:
            await context.bot.delete_message(chat_id, current_msg)
            deleted += 1
            if deleted % 20 == 0:  # Update progress
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
                await asyncio.sleep(0.5)  # Rate limiting
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except BadRequest:  # Message not found
            continue
        except Exception as e:
            print(f"Deletion error: {e}")
            break
    
    await status_msg.edit_text(f"✅ Deleted {deleted} messages")

async def delete_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete from replied message to newest"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a message to use this command")
        return
    
    user_id = update.effective_user.id
    if not await check_membership(user_id, context):
        await update.message.reply_text(
            f"❌ You must join {REQUIRED_CHANNEL} and verify first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
                [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
            ])
        )
        return
        
    chat_id = update.effective_chat.id
    try:
        chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ I need admin privileges with delete rights!")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Admin check failed: {e}")
        return
    
    start_msg = update.message.reply_to_message.message_id
    end_msg = update.message.message_id
    status_msg = await update.message.reply_text(f"⚡ Deleting from message #{start_msg}...")
    deleted = 0
    
    for current_msg in range(end_msg, start_msg - 1, -1):
        try:
            await context.bot.delete_message(chat_id, current_msg)
            deleted += 1
            if deleted % 20 == 0:
                await status_msg.edit_text(f"⏳ Deleted {deleted} messages...")
                await asyncio.sleep(0.5)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except BadRequest:
            continue
        except Exception as e:
            print(f"Deletion error: {e}")
            break
    
    await status_msg.edit_text(f"✅ Deleted {deleted} messages (from #{start_msg} to newest)")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.add_handler(CommandHandler("deletefrom", delete_from_message))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
