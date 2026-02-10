# plugins/start.py

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from plugins.auth import ensure_user, is_authorized


ADMIN_LINK = "https://t.me/lkd_ak"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = context.application.bot_data["users"]
    user_id = update.effective_user.id

    # 🔐 ensure user exists (demo / paid)
    user = ensure_user(users, user_id)

    now = datetime.utcnow()

    # ---------- DEMO ACTIVE ----------
    if is_authorized(user):
        if user.get("is_demo", False):
            expires = user["expires_on"].strftime("%d %b %Y, %H:%M")

            text = (
                "👋 <b>Welcome to MCQ Scheduler Bot</b>\n\n"
                "🎁 <b>Demo Activated</b>\n"
                f"⏳ Demo valid till: <b>{expires}</b>\n\n"
                "📌 What this bot can do:\n"
                "• Schedule MCQs from CSV\n"
                "• Auto send MCQs daily\n"
                "• Pause / Resume anytime\n\n"
                "🚀 Commands:\n"
                "/schedulemcq – Create MCQ schedule\n"
                "/setting – Manage schedules"
            )
        else:
            # PAID USER
            text = (
                "👋 <b>Welcome back!</b>\n\n"
                "✅ Your plan is active\n\n"
                "🚀 Commands:\n"
                "/schedulemcq – Create MCQ schedule\n"
                "/setting – Manage schedules"
            )

        await update.message.reply_text(text, parse_mode="HTML")
        return

    # ---------- DEMO EXPIRED ----------
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💳 Contact Admin", url="https://t.me/lkd_ak")]]
    )

    await update.message.reply_text(
        "⛔ <b>Your Demo Plan has Expired</b>\n\n"
        "📦 To continue using this bot and send MCQs:\n"
        "👉 Please purchase a plan\n\n"
        "📞 Contact admin to activate your account",
        parse_mode="HTML",
        reply_markup=kb
    )


def register_start_handlers(app):
    app.add_handler(CommandHandler("start", start))
