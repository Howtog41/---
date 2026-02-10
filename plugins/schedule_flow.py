import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)

from plugins.mcqsend import validate_csv
from plugins.scheduler import schedule_job

# ===== STATES =====
CSV, LIMIT, TIME, CHANNEL, PREMSG = range(5)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


# ================= SCHEDULE FLOW =================
async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV file bhejo")
    return CSV


async def get_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = f"{DATA_DIR}/{update.effective_user.id}_{int(datetime.now().timestamp())}.csv"
    await file.download_to_drive(path)

    ok, res = validate_csv(path)
    if not ok:
        await update.message.reply_text(res)
        return ConversationHandler.END

    context.user_data["csv"] = path
    context.user_data["total"] = len(res)

    await update.message.reply_text("🔢 Daily MCQ limit")
    return LIMIT


async def get_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["limit"] = int(update.message.text)
    except:
        await update.message.reply_text("❌ Sirf number bhejo ⏰ Time (HH:MM)")
        return LIMIT

    await update.message.reply_text("⏰ Time (HH:MM)")
    return TIME


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    await update.message.reply_text("📢 Channel ID / @username")
    return CHANNEL


async def get_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["channel"] = update.message.text
    await update.message.reply_text("✉️ Pre-message")
    return PREMSG


async def get_premsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    schedules = context.application.bot_data["schedules"]

    s = {
        "user_id": update.effective_user.id,
        "csv_path": d["csv"],
        "total_mcq": d["total"],
        "sent_mcq": 0,
        "daily_limit": d["limit"],
        "time": d["time"],
        "channel_id": d["channel"],
        "pre_message": update.message.text,
        "status": "active",
        "created_at": datetime.now()
    }

    r = schedules.insert_one(s)

    schedule_job(s | {"_id": r.inserted_id}, context.bot, schedules)

    await update.message.reply_text("✅ Schedule created")
    context.user_data.clear()
    return ConversationHandler.END
