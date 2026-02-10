import os
from datetime import datetime
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButtonRequestChat
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from plugins.mcqsend import validate_csv
from plugins.scheduler import schedule_job


# ================= STATES =================
CSV, LIMIT, TIME, CHANNEL, PREMSG = range(5)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


# ================= START =================
async def schedulemcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 CSV file bhejo")
    return CSV


# ================= CSV =================
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


# ================= LIMIT =================
async def get_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        limit = int(update.message.text)
        if not 1 <= limit <= 10:
            raise ValueError
        context.user_data["limit"] = limit
    except:
        await update.message.reply_text(
            "❌ Daily MCQ limit sirf 1 se 10 ke beech hona chahiye\n\n🔢 Dubara bhejo (1–10)"
        )
        return LIMIT

    await update.message.reply_text("⏰ Time bhejo (HH:MM)")
    return TIME


# ================= TIME =================
def valid_time(t: str) -> bool:
    try:
        h, m = map(int, t.split(":"))
        return 0 <= h <= 23 and 0 <= m <= 59
    except:
        return False


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()

    if not valid_time(t):
        await update.message.reply_text(
            "❌ Galat time format\n\n⏰ Example: 07:30, 18:45"
        )
        return TIME

    context.user_data["time"] = t

    # show channel selector button
    kb = [[
        KeyboardButton(
            "📢 Channel / Group Select",
            request_chat=KeyboardButtonRequestChat(
                request_id=1,
                chat_is_channel=False,
                bot_is_member=True
            )
        )
    ]]

    await update.message.reply_text(
        "👇 Channel ya Group select karo\n\n⚠️ Bot waha member/admin hona chahiye",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
    )
    return CHANNEL


# ================= CHANNEL =================
async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_shared = update.message.chat_shared
    bot = context.bot

    if not chat_shared:
        await update.message.reply_text("❌ Button se hi channel/group select karo")
        return CHANNEL

    chat_id = chat_shared.chat_id

    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "member"):
            raise Exception
    except:
        await update.message.reply_text(
            "❌ Bot us channel/group me member ya admin nahi hai\n\n"
            "👉 Pehle bot add karo, fir dubara select karo"
        )
        return CHANNEL

    chat = await bot.get_chat(chat_id)

    context.user_data["channel"] = chat_id
    context.user_data["channel_title"] = chat.title

    await update.message.reply_text(
        f"✅ Selected: {chat.title}\n\n✉️ Pre-message bhejo (max 60 words)",
        reply_markup=ReplyKeyboardMarkup([[]], remove_keyboard=True)
    )
    return PREMSG


# ================= PRE MESSAGE =================
async def get_premsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    words = text.split()

    if len(words) > 60:
        await update.message.reply_text(
            f"❌ Pre-message me sirf 60 words allowed hain\n\n"
            f"📊 Aapke words: {len(words)}"
        )
        return PREMSG

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
        "pre_message": text,
        "status": "active",
        "created_at": datetime.now()
    }

    r = schedules.insert_one(s)
    schedule_job(s | {"_id": r.inserted_id}, context.bot, schedules)

    await update.message.reply_text("✅ Schedule created successfully 🎉")
    context.user_data.clear()
    return ConversationHandler.END


# ================= REGISTER =================
def register_schedulemcq_handlers(app):

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("schedulemcq", schedulemcq)
        ],
        states={
            CSV: [
                MessageHandler(filters.Document.ALL, get_csv)
            ],
            LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_limit)
            ],
            TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)
            ],
            CHANNEL: [
                MessageHandler(filters.StatusUpdate.CHAT_SHARED, receive_channel)
            ],
            PREMSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_premsg)
            ],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True
    )

    app.add_handler(conv)
