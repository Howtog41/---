import os
import pandas as pd
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from config import BOT_TOKEN
from scheduler import scheduler

# -------- STATES ----------
CSV, COUNT, TIME, CHANNEL = range(4)

DATA_DIR = "users_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi!\nUse /schedulemcq to schedule daily MCQs"
    )

# ---------- STEP 1 ----------
async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV file bhejo")
    return CSV

# ---------- STEP 2 ----------
async def receive_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    user_id = update.effective_user.id
    path = f"{DATA_DIR}/{user_id}.csv"
    await file.download_to_drive(path)

    context.user_data["csv"] = path
    await update.message.reply_text("🔢 Daily kitne MCQ bhejne hain? (Max 10)")
    return COUNT

# ---------- STEP 3 ----------
async def mcq_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = int(update.message.text)
    if count > 10 or count < 1:
        await update.message.reply_text("❌ 1–10 ke beech number bhejo")
        return COUNT

    context.user_data["count"] = count
    await update.message.reply_text("⏰ Time bhejo (HH:MM format)")
    return TIME

# ---------- STEP 4 ----------
async def send_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        datetime.strptime(update.message.text, "%H:%M")
    except:
        await update.message.reply_text("❌ Time format galat hai")
        return TIME

    context.user_data["time"] = update.message.text
    await update.message.reply_text("📢 Channel ID bhejo")
    return CHANNEL

# ---------- STEP 5 ----------
async def channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = update.message.text
    bot = context.bot

    try:
        member = await bot.get_chat_member(channel, bot.id)
        if member.status not in ["administrator", "creator"]:
            raise Exception
    except:
        await update.message.reply_text("❌ Bot admin nahi hai channel me")
        return CHANNEL

    context.user_data["channel"] = channel

    schedule_job(context)
    await update.message.reply_text("✅ Schedule confirm ho gaya")
    return ConversationHandler.END

# ---------- JOB ----------
def schedule_job(context):
    data = context.user_data
    user_id = context._user_id

    hour, minute = map(int, data["time"].split(":"))

    scheduler.add_job(
        send_mcqs,
        "cron",
        hour=hour,
        minute=minute,
        args=[data, context.bot],
        id=str(user_id),
        replace_existing=True
    )

# ---------- MCQ SENDER ----------
async def send_mcqs(data, bot):
    df = pd.read_csv(data["csv"])
    count = data["count"]

    send = df.head(count)
    remain = df.iloc[count:]

    for _, row in send.iterrows():
        text = (
            f"❓ {row['Question']}\n\n"
            f"A. {row['Option A']}\n"
            f"B. {row['Option B']}\n"
            f"C. {row['Option C']}\n"
            f"D. {row['Option D']}\n\n"
            f"✅ Answer: {row['Answer']}\n"
            f"📝 {row['Description']}"
        )
        await bot.send_message(data["channel"], text)
        await asyncio.sleep(1)

    remain.to_csv(data["csv"], index=False)

# ---------- MAIN ----------



def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ✅ YAHI SAFE PLACE HAI
    scheduler.start()

    conv = ConversationHandler(
        entry_points=[CommandHandler("schedulemcq", schedulemcq)],
        states={
            CSV: [MessageHandler(filters.Document.ALL, receive_csv)],
            COUNT: [MessageHandler(filters.TEXT, mcq_count)],
            TIME: [MessageHandler(filters.TEXT, send_time)],
            CHANNEL: [MessageHandler(filters.TEXT, channel_id)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("🤖 Bot running...")
    app.run_polling()
