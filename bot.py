import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.error import RetryAfter, BadRequest
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
REQUIRED_CHANNEL = "@sr_robots"  # Your channel username
ADMIN_IDS = [7174055187]  # Your Telegram user ID
MONGO_URI = os.getenv('MONGO_URI', "mongodb+srv://coolmicks112:adkhJm5kBrbhhm6N@delall.3xszyma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = "Delall"

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db["users"]
broadcasts_col = db["broadcasts"]
stats_col = db["stats"]

async def store_user(user_data):
    try:
        await users_col.update_one(
            {"user_id": user_data["user_id"]},
            {"$set": {**user_data, "last_interaction": datetime.now()}},
            upsert=True
        )
    except PyMongoError as e:
        print(f"MongoDB Error: {e}")

async def get_all_users():
    return await users_col.find({}).to_list(length=None)

async def record_deletion(count):
    await stats_col.update_one(
        {"type": "deletions"},
        {"$inc": {"count": count}},
        upsert=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "has_joined": False
    }
    await store_user(user_data)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_membership")]
    ])
    
    await update.message.reply_text(
        "🤖 <b>Message Cleaner Bot</b>\n\n"
        "🔹 <b>Commands:</b>\n"
        "/start - Show this message\n"
        "/deleteall - Delete all messages\n"
        "/broadcast - (Admin) Send message to all users\n"
        "/stats - (Admin) View bot statistics\n\n"
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
            await users_col.update_one(
                {"user_id": query.from_user.id},
                {"$set": {"has_joined": True, "channel_join_date": datetime.now()}}
            )
            await query.edit_message_text(
                "✅ Thanks for joining!\n\n"
                "Now you can use /deleteall in any group where I'm admin."
            )
        else:
            await query.answer("You haven't joined the channel yet!", show_alert=True)
    except Exception as e:
        await query.answer("Error checking membership. Please try again.", show_alert=True)

async def verify_membership(user_id):
    user = await users_col.find_one({"user_id": user_id})
    return user and user.get("has_joined", False)

async def delete_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verify_membership(update.effective_user.id):
        await update.message.reply_text(
            f"❌ You must join {REQUIRED_CHANNEL} first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")]
            ])
        )
        return
        
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
    
    await record_deletion(deleted)
    await status_msg.edit_text(f"✅ Finished! Deleted {deleted} messages")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = await get_all_users()
    success = 0
    failed = 0

    status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")

    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=message
            )
            success += 1
        except Exception as e:
            failed += 1
        await asyncio.sleep(0.1)

    await status_msg.edit_text(
        f"✅ Broadcast complete!\n"
        f"Success: {success}\n"
        f"Failed: {failed}"
    )

    await broadcasts_col.insert_one({
        "admin_id": update.effective_user.id,
        "message": message,
        "success_count": success,
        "failed_count": failed,
        "timestamp": datetime.now()
    })

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return

    try:
        # User Statistics
        total_users = await users_col.count_documents({})
        active_users = await users_col.count_documents({
            "last_interaction": {"$gte": datetime.now() - timedelta(days=30)}
        })
        channel_members = await users_col.count_documents({"has_joined": True})
        new_today = await users_col.count_documents({
            "last_interaction": {"$gte": datetime.now() - timedelta(days=1)}
        })

        # Broadcast Statistics
        total_broadcasts = await broadcasts_col.count_documents({})
        last_broadcast = await broadcasts_col.find_one({}, sort=[("timestamp", -1)])

        # Deletion Statistics
        deletions_data = await stats_col.find_one({"type": "deletions"})
        total_deletions = deletions_data["count"] if deletions_data else 0

        # Prepare stats message
        stats_msg = (
            "📊 <b>Bot Statistics</b>\n\n"
            f"👥 <b>Users:</b> {total_users} total\n"
            f"🟢 {active_users} active (30 days)\n"
            f"🆕 {new_today} new today\n"
            f"🔗 {channel_members} joined channel\n\n"
            f"🗑️ <b>Messages Deleted:</b> {total_deletions}\n\n"
            f"📢 <b>Broadcasts:</b> {total_broadcasts} sent\n"
        )

        if last_broadcast:
            last_bc_time = last_broadcast['timestamp'].strftime("%Y-%m-%d %H:%M")
            stats_msg += (
                f"Last broadcast: {last_bc_time}\n"
                f"Reached: {last_broadcast['success_count']} users\n"
            )

        await update.message.reply_text(stats_msg, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error generating stats: {e}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deleteall", delete_all_messages))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(check_membership, pattern="^check_membership$"))
    
    application.run_polling()

if __name__ == '__main__':
    main()
