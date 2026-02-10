# plugins/auth.py

from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

ADMIN_ID = 1922012735   # 🔴 apna admin id yaha dalo


# ---------- USER INIT ----------
def ensure_user(users, user_id: int):
    user = users.find_one({"user_id": user_id})
    if not user:
        users.insert_one({
            "user_id": user_id,
            "authorized": False,
            "demo_expires_at": datetime.utcnow() + timedelta(days=3),
            "authorized_on": None
        })
        return False
    return user.get("authorized", False)


# ---------- AUTH CHECK ----------
def is_user_allowed(user: dict) -> bool:
    if not user:
        return False

    if user.get("authorized"):
        return True

    demo_expiry = user.get("demo_expires_at")
    if demo_expiry and datetime.utcnow() < demo_expiry:
        return True

    return False


# ---------- /authorize ----------
async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage:\n/authorize <user_id> [days]"
        )
        return

    user_id = int(context.args[0])
    days = int(context.args[1]) if len(context.args) > 1 else None

    users = context.application.bot_data["users"]

    data = {
        "authorized": True,
        "authorized_on": datetime.utcnow()
    }

    if days:
        data["demo_expires_at"] = datetime.utcnow() + timedelta(days=days)

    users.update_one(
        {"user_id": user_id},
        {"$set": data},
        upsert=True
    )

    await update.message.reply_text(
        f"✅ User {user_id} authorized successfully"
    )


# ---------- REGISTER ----------
def register_auth_handlers(app):
    app.add_handler(CommandHandler("authorize", authorize))
