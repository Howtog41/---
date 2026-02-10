# plugins/start.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from plugins.auth import ensure_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = context.application.bot_data["users"]

    # 🔐 ensure demo / auth user entry
    ensure_user(users, update.effective_user.id)

    await update.message.reply_text(
        "👋 <b>Welcome to MCQ Scheduler Bot</b>\n\n"
        "📌 Commands:\n"
        "/schedulemcq – Create new MCQ schedule\n"
        "/setting – Manage schedules",
        parse_mode="HTML"
    )


def register_start_handlers(app):
    app.add_handler(CommandHandler("start", start))
