import os
import asyncio
import pandas as pd
from datetime import datetime
from pytz import timezone

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"
TZ = timezone("Asia/Kolkata")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CSV, COUNT, TIME, CHANNEL = range(4)

# ================= SCHEDULER =================
scheduler = AsyncIOScheduler(timezone=TZ)

# ================= STARTUP HOOK =================
async def on_startup(app: Application):
    scheduler.start()
    print("✅ Scheduler started successfully")

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi\n/schedulemcq use karo daily MCQ schedule ke liye"
    )

async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV file bhejo")
    return CSV

async def receive_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    user_id = update.effective_user.id
    path = f"{DATA_DIR}/{user_id}.csv"
    await file.download_to_drive(path)

    context.user_data["csv"] = path
    await update.message.reply_text("🔢 Daily kitne MCQ? (1–10)")
    return COUNT

async def mcq_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        if not 1 <= count <= 10:
            raise ValueError
    except:
        await update.message.reply_text("❌ 1–10 ke beech number bhejo")
        return COUNT

    context.user_data["count"] = count
    await update.message.reply_text("⏰ Time bhejo (HH:MM)")
    return TIME

async def send_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        datetime.strptime(update.message.text, "%H:%M")
    except:
        await update.message.reply_text("❌ Galat time format")
        return TIME

    context.user_data["time"] = update.message.text
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
        await update.message.reply_text("❌ Bot channel ka admin nahi hai")
        return CHANNEL

    context.user_data["channel"] = channel
    schedule_job(context)

    await update.message.reply_text("✅ Schedule confirm ho gaya")
    return ConversationHandler.END

# ================= JOB =================
def schedule_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    hour, minute = map(int, data["time"].split(":"))

    scheduler.add_job(
        send_mcqs,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[data, context.bot],
        id=f"{data['channel']}_{hour}_{minute}",
        replace_existing=True
    )

async def send_mcqs(data, bot):
    if not os.path.exists(data["csv"]):
        return

    df = pd.read_csv(data["csv"])
    if df.empty:
        return

    send_df = df.head(data["count"])
    remain_df = df.iloc[data["count"]:]

    for _, row in send_df.iterrows():
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

    remain_df.to_csv(data["csv"], index=False)

# ================= MAIN =================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)   # ✅ MOST IMPORTANT LINE
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("schedulemcq", schedulemcq)],
        states={
            CSV: [MessageHandler(filters.Document.ALL, receive_csv)],
            COUNT: [MessageHandler(filters.TEXT, mcq_count)],
            TIME: [MessageHandler(filters.TEXT, send_time)],
            CHANNEL: [MessageHandler(filters.TEXT, channel_id)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("🤖 BOT STARTING…")
    app.run_polling()

if __name__ == "__main__":
    main()
