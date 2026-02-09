import os, asyncio, pandas as pd
from datetime import datetime
from pytz import timezone
from pymongo import MongoClient

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"
MONGO_URI = "mongodb+srv://terabox255:0S79LfRAeOMrOdYj@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"
TZ = timezone("Asia/Kolkata")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CSV, COUNT, TIME, CHANNEL, PREMSG = range(5)

# ================= DB =================
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

# ================= SCHEDULER =================
scheduler = AsyncIOScheduler(timezone=TZ)

# ================= STARTUP =================
async def on_startup(app):
    scheduler.start()
    restore_jobs(app.bot)
    print("✅ Scheduler started & jobs restored")

def restore_jobs(bot):
    for s in schedules.find({"status": "active"}):
        hour, minute = map(int, s["time"].split(":"))
        scheduler.add_job(
            send_mcqs,
            "cron",
            hour=hour,
            minute=minute,
            args=[s, bot],
            id=str(s["_id"]),
            replace_existing=True
        )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi\n"
        "/schedulemcq – MCQ schedule\n"
        "/setting – Change settings\n"
        "/pause /resume /delete"
    )

# ================= SCHEDULE FLOW =================
async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV file bhejo")
    return CSV

async def receive_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    uid = update.effective_user.id
    path = f"{DATA_DIR}/{uid}.csv"
    await file.download_to_drive(path)

    context.user_data["csv"] = path
    await update.message.reply_text("🔢 Daily kitne MCQ? (1–10)")
    return COUNT

async def mcq_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        c = int(update.message.text)
        if not 1 <= c <= 10:
            raise ValueError
    except:
        await update.message.reply_text("❌ 1–10 number bhejo")
        return COUNT

    context.user_data["limit"] = c
    await update.message.reply_text("⏰ Time bhejo (HH:MM)")
    return TIME

async def send_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        datetime.strptime(update.message.text, "%H:%M")
    except:
        await update.message.reply_text("❌ Galat time")
        return TIME

    context.user_data["time"] = update.message.text
    await update.message.reply_text("📝 Pre-MCQ message bhejo")
    return PREMSG

async def pre_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pre_message"] = update.message.text
    await update.message.reply_text("📢 Channel ID bhejo")
    return CHANNEL

async def channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = update.message.text
    bot = context.bot

    try:
        member = await bot.get_chat_member(channel, bot.id)
        if member.status not in ("administrator", "creator"):
            raise Exception
    except:
        await update.message.reply_text("❌ Bot admin nahi hai")
        return CHANNEL

    data = {
        "user_id": update.effective_user.id,
        "channel_id": channel,
        "csv_path": context.user_data["csv"],
        "daily_limit": context.user_data["limit"],
        "time": context.user_data["time"],
        "pre_message": context.user_data["pre_message"],
        "status": "active",
        "offset": 0,
    }

    schedules.insert_one(data)
    restore_jobs(bot)

    await update.message.reply_text("✅ MCQ Schedule Confirmed")
    return ConversationHandler.END

# ================= MCQ JOB =================
async def send_mcqs(data, bot):
    if data["status"] != "active":
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
        correct = ["A", "B", "C", "D"].index(row["Answer"])

        await bot.send_poll(
            chat_id=data["channel_id"],
            question=row["Question"],
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=True
        )

        await bot.send_message(
            data["channel_id"],
            f"📝 Explanation:\n{row['Description']}"
        )
        await asyncio.sleep(1)

    schedules.update_one(
        {"_id": data["_id"]},
        {"$set": {"offset": end}}
    )

# ================= SETTINGS =================
async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {"status": "paused"}}
    )
    await update.message.reply_text("⏸ Paused")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {"status": "active"}}
    )
    await update.message.reply_text("▶ Resumed")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = schedules.find_one({"user_id": update.effective_user.id})
    if s:
        scheduler.remove_job(str(s["_id"]))
        schedules.delete_one({"_id": s["_id"]})
    await update.message.reply_text("❌ Deleted")

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
            CSV: [MessageHandler(filters.Document.ALL, receive_csv)],
            COUNT: [MessageHandler(filters.TEXT, mcq_count)],
            TIME: [MessageHandler(filters.TEXT, send_time)],
            PREMSG: [MessageHandler(filters.TEXT, pre_message)],
            CHANNEL: [MessageHandler(filters.TEXT, channel_id)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("delete", delete))

    print("🤖 FULL MCQ BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
