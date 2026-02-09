import os, asyncio, pandas as pd
from datetime import datetime
from pytz import timezone
from pymongo import MongoClient
from bson import ObjectId

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes,
    CallbackQueryHandler, filters
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"
MONGO_URI = "mongodb+srv://terabox255:a8its4KrW06OhifE@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"
TZ = timezone("Asia/Kolkata")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CSV, LIMIT, TIME, CHANNEL, PREMSG = range(5)

REQUIRED_COLUMNS = [
    "Question","Option A","Option B",
    "Option C","Option D","Answer","Description"
]

# ================= DB =================
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

# ================= SCHEDULER =================
scheduler = AsyncIOScheduler(timezone=TZ)

# ================= CSV VALIDATION =================
def validate_csv(path):
    try:
        df = pd.read_csv(path)
    except:
        return False, "❌ CSV read nahi ho rahi"

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            return False, f"❌ Missing column: {col}"

    if df.empty:
        return False, "❌ CSV empty hai"

    if not df["Answer"].isin(["A","B","C","D"]).all():
        return False, "❌ Answer sirf A/B/C/D hona chahiye"

    return True, df

# ================= STARTUP =================
async def on_startup(app: Application):
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
    print("✅ Scheduler restored")

# ================= SEND MCQS =================
async def send_mcqs(schedule_id, bot):
    s = schedules.find_one({"_id": ObjectId(schedule_id)})
    if not s or s["status"] != "active":
        return

    df = pd.read_csv(s["csv_path"])
    total = len(df)
    sent = s["sent_mcq"]
    limit = s["daily_limit"]

    if sent >= total:
        return

    batch = df.iloc[sent: sent + limit]

    await bot.send_message(s["channel_id"], s["pre_message"])

    for _, row in batch.iterrows():
        options = [
            row["Option A"],
            row["Option B"],
            row["Option C"],
            row["Option D"]
        ]
        correct = ["A","B","C","D"].index(row["Answer"])

        question = (
            f"{row['Question']}\n\n"
            f"📝 {row['Description']}"
        )

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

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 MCQ Scheduler Bot\n\n"
        "/schedulemcq – New schedule\n"
        "/setting – Manage schedules"
    )

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

    await update.message.reply_text("🔢 Daily MCQ limit (1–10)")
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
        "status": "active",
        "created_at": datetime.now()
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

# ================= SETTINGS =================
async def setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_schedules = list(schedules.find({"user_id": update.effective_user.id}))
    if not user_schedules:
        await update.message.reply_text("❌ No schedules found")
        return

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

async def setting_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, sid = q.data.split(":")
    s = schedules.find_one({"_id": ObjectId(sid)})
    if not s:
        await q.edit_message_text("❌ Schedule not found")
        return

    if action == "view":
        await q.edit_message_text(
            f"📂 CSV: {s['csv_path']}\n"
            f"📊 Progress: {s['sent_mcq']} / {s['total_mcq']}\n"
            f"⏰ Time: {s['time']}\n"
            f"🔢 Daily: {s['daily_limit']}\n"
            f"🟢 Status: {s['status']}"
        )

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
