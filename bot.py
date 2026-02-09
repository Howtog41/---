import os, asyncio, pandas as pd
from datetime import datetime
from pytz import timezone
from pymongo import MongoClient

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, CallbackQueryHandler, filters
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"
MONGO_URI = "mongodb+srv://terabox255:0S79LfRAeOMrOdYj@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"
TZ = timezone("Asia/Kolkata")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CSV, LIMIT, TIME, CHANNEL, PREMSG = range(5)

# ================= DB =================
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

# ================= SCHEDULER =================
scheduler = AsyncIOScheduler(timezone=TZ)

# ================= STARTUP =================
async def on_startup(app: Application):
    scheduler.start()
    restore_jobs(app.bot)
    print("✅ Scheduler restored")

def restore_jobs(bot):
    for s in schedules.find({"status": "active"}):
        h, m = map(int, s["time"].split(":"))
        scheduler.add_job(
            send_mcqs,
            "cron",
            hour=h,
            minute=m,
            args=[s["_id"], bot],
            id=str(s["_id"]),
            replace_existing=True
        )

# ================= SEND MCQS =================
async def send_mcqs(schedule_id, bot):
    data = schedules.find_one({"_id": schedule_id})
    if not data or data["status"] != "active":
        return

    df = pd.read_csv(data["csv_path"])
    start = data["offset"]
    end = start + data["daily_limit"]
    batch = df.iloc[start:end]

    if batch.empty:
        return

    await bot.send_message(data["channel_id"], data["pre_message"])

    for _, row in batch.iterrows():
        options = [
            row["Option A"],
            row["Option B"],
            row["Option C"],
            row["Option D"],
        ]
        correct = ["A","B","C","D"].index(row["Answer"])

        await bot.send_poll(
            chat_id=data["channel_id"],
            question=f"{row['Question']}\n\n📝 {row['Description']}",
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=True,
            explanation=row["Description"][:200],
        )
        await asyncio.sleep(1)

    schedules.update_one(
        {"_id": schedule_id},
        {"$set": {"offset": end}}
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 MCQ Scheduler Bot\n\n"
        "/schedulemcq – MCQ schedule\n"
        "/setting – manage schedule"
    )

# ================= SCHEDULE FLOW =================
async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV bhejo")
    return CSV

async def get_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = f"{DATA_DIR}/{update.effective_user.id}.csv"
    await file.download_to_drive(path)
    context.user_data["csv"] = path
    await update.message.reply_text("🔢 Daily MCQ limit?")
    return LIMIT

async def get_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["limit"] = int(update.message.text)
    await update.message.reply_text("⏰ Time (HH:MM)")
    return TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    await update.message.reply_text("📢 Channel ID")
    return CHANNEL

async def get_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["channel"] = update.message.text
    await update.message.reply_text("✉️ Pre-message")
    return PREMSG

async def get_premsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    s = {
        "user_id": update.effective_user.id,
        "csv_path": data["csv"],
        "daily_limit": data["limit"],
        "time": data["time"],
        "channel_id": data["channel"],
        "pre_message": update.message.text,
        "offset": 0,
        "status": "active"
    }
    r = schedules.insert_one(s)

    h, m = map(int, s["time"].split(":"))
    scheduler.add_job(
        send_mcqs,
        "cron",
        hour=h,
        minute=m,
        args=[r.inserted_id, context.bot],
        id=str(r.inserted_id),
        replace_existing=True
    )

    await update.message.reply_text("✅ MCQ Scheduled")
    return ConversationHandler.END

# ================= SETTINGS =================
async def setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("👁 View", callback_data="view")],
        [InlineKeyboardButton("⏸ Pause", callback_data="pause"),
         InlineKeyboardButton("▶ Resume", callback_data="resume")],
        [InlineKeyboardButton("✏ Edit Time", callback_data="edit_time")],
        [InlineKeyboardButton("✏ Edit Message", callback_data="edit_msg")],
        [InlineKeyboardButton("❌ Delete", callback_data="delete")]
    ]
    await update.message.reply_text("⚙ Settings", reply_markup=InlineKeyboardMarkup(kb))

async def setting_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    s = schedules.find_one({"user_id": q.from_user.id})
    if not s:
        await q.edit_message_text("❌ No schedule")
        return

    if q.data == "view":
        await q.edit_message_text(
            f"📂 CSV: {s['csv_path']}\n"
            f"⏰ Time: {s['time']}\n"
            f"📊 Daily: {s['daily_limit']}\n"
            f"📈 Sent: {s['offset']}\n"
            f"🟢 Status: {s['status']}"
        )

    elif q.data == "pause":
        schedules.update_one({"_id": s["_id"]}, {"$set": {"status": "paused"}})
        await q.edit_message_text("⏸ Paused")

    elif q.data == "resume":
        schedules.update_one({"_id": s["_id"]}, {"$set": {"status": "active"}})
        await q.edit_message_text("▶ Resumed")

    elif q.data == "delete":
        scheduler.remove_job(str(s["_id"]))
        schedules.delete_one({"_id": s["_id"]})
        await q.edit_message_text("❌ Deleted")

# ================= MAIN =================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("schedulemcq", schedulemcq)],
        states={
            CSV: [MessageHandler(filters.Document.ALL, get_csv)],
            LIMIT: [MessageHandler(filters.TEXT, get_limit)],
            TIME: [MessageHandler(filters.TEXT, get_time)],
            CHANNEL: [MessageHandler(filters.TEXT, get_channel)],
            PREMSG: [MessageHandler(filters.TEXT, get_premsg)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("setting", setting))
    app.add_handler(CallbackQueryHandler(setting_action))

    print("🤖 BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
