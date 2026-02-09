from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://USER:PASS@cluster.mongodb.net/"
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

async def setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_schedules = schedules.find({"user_id": update.effective_user.id})
    kb = []

    for s in user_schedules:
        kb.append([
            InlineKeyboardButton(
                s["csv_path"].split("/")[-1],
                callback_data=f"view:{s['_id']}"
            )
        ])

    await update.message.reply_text(
        "⚙ Your Schedules",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    act, sid = q.data.split(":")
    s = schedules.find_one({"_id": ObjectId(sid)})

    if act == "view":
        await q.edit_message_text(
            f"📊 Progress: {s['sent_mcq']} / {s['total_mcq']}\n"
            f"⏰ Time: {s['time']}\n"
            f"🔢 Daily: {s['daily_limit']}\n"
            f"🟢 Status: {s['status']}"
        )

def setup(app):
    app.add_handler(CommandHandler("setting", setting))
    app.add_handler(CallbackQueryHandler(action))
