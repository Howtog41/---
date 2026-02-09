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
MONGO_URI = "MONGO_URI", "mongodb+srv://terabox255:0S79LfRAeOMrOdYj@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"
TZ = timezone("Asia/Kolkata")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= DB =================
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

# ================= SCHEDULER =================
scheduler = AsyncIOScheduler(timezone=TZ)

async def on_startup(app):
    scheduler.start()
    restore_jobs(app.bot)

# ================= RESTORE =================
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

# ================= MCQ SENDER =================
async def send_mcqs(data, bot):
    if data["status"] != "active":
        return

    df = pd.read_csv(data["csv_path"])
    start = data["offset"]
    end = start + data["daily_limit"]

    batch = df.iloc[start:end]
    if batch.empty:
        return

    # Pre-message
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

# ================= COMMANDS =================
async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {"status": "paused"}}
    )
    await update.message.reply_text("⏸ MCQ paused")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {"status": "active"}}
    )
    await update.message.reply_text("▶ MCQ resumed")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = schedules.find_one({"user_id": update.effective_user.id})
    if s:
        scheduler.remove_job(str(s["_id"]))
        schedules.delete_one({"_id": s["_id"]})
    await update.message.reply_text("❌ Schedule deleted")

# ================= MAIN =================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("delete", delete))

    print("🤖 MCQ BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
