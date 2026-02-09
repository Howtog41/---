import os, asyncio, pandas as pd
from datetime import datetime
from pytz import timezone
from pymongo import MongoClient
from bson import ObjectId

from telegram import Update
from telegram.ext import (
    CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
TZ = timezone("Asia/Kolkata")
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

MONGO_URI = "mongodb+srv://terabox255:0S79LfRAeOMrOdYj@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

CSV, LIMIT, TIME, CHANNEL, PREMSG = range(5)

REQUIRED_COLUMNS = [
    "Question","Option A","Option B",
    "Option C","Option D","Answer","Description"
]

scheduler = AsyncIOScheduler(timezone=TZ)

# ================= CSV VALIDATION =================
def validate_csv(path):
    df = pd.read_csv(path)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            return False, f"Missing column: {col}"

    if not df["Answer"].isin(["A","B","C","D"]).all():
        return False, "Answer must be A/B/C/D"

    return True, df

# ================= STARTUP =================
async def on_startup(app):
    scheduler.start()
    for s in schedules.find({"status": "active"}):
        h, m = map(int, s["time"].split(":"))
        scheduler.add_job(
            send_mcqs,
            "cron",
            hour=h,
            minute=m,
            args=[str(s["_id"]), app.bot],
            id=str(s["_id"]),
            replace_existing=True
        )

# ================= SEND MCQ =================
async def send_mcqs(schedule_id, bot):
    s = schedules.find_one({"_id": ObjectId(schedule_id)})
    if not s or s["status"] != "active":
        return

    df = pd.read_csv(s["csv_path"])
    sent = s["sent_mcq"]
    limit = s["daily_limit"]

    batch = df.iloc[sent: sent + limit]
    if batch.empty:
        return

    await bot.send_message(s["channel_id"], s["pre_message"])

    for _, row in batch.iterrows():
        options = [
            row["Option A"], row["Option B"],
            row["Option C"], row["Option D"]
        ]
        correct = ["A","B","C","D"].index(row["Answer"])

        question = f"{row['Question']}\n\n📝 {row['Description']}"

        await bot.send_poll(
            chat_id=s["channel_id"],
            question=question[:300],
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=True
        )
        await asyncio.sleep(1)

    schedules.update_one(
        {"_id": s["_id"]},
        {"$inc": {"sent_mcq": len(batch)}}
    )

# ================= FLOW =================
async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV bhejo")
    return CSV

async def get_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = f"{DATA_DIR}/{update.effective_user.id}_{int(datetime.now().timestamp())}.csv"
    await file.download_to_drive(path)

    ok, df = validate_csv(path)
    if not ok:
        await update.message.reply_text(df)
        return ConversationHandler.END

    context.user_data["csv"] = path
    context.user_data["total"] = len(df)
    await update.message.reply_text("🔢 Daily MCQ limit")
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
    await update.message.reply_text("✉️ Pre message")
    return PREMSG

async def get_premsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    s = {
        "user_id": update.effective_user.id,
        "csv_path": d["csv"],
        "total_mcq": d["total"],
        "sent_mcq": 0,
        "daily_limit": d["limit"],
        "time": d["time"],
        "channel_id": d["channel"],
        "pre_message": update.message.text,
        "status": "active"
    }
    r = schedules.insert_one(s)

    h, m = map(int, s["time"].split(":"))
    scheduler.add_job(
        send_mcqs,
        "cron",
        hour=h,
        minute=m,
        args=[str(r.inserted_id), context.bot],
        id=str(r.inserted_id),
        replace_existing=True
    )

    await update.message.reply_text("✅ Schedule created")
    return ConversationHandler.END

# ================= SETUP =================
def setup(app):
    app.post_init = on_startup

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
    app.add_handler(conv)
