from bson import ObjectId
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from plugins.scheduler import schedule_job, remove_job

EDIT_INPUT = 100


# ================= SETTINGS LIST =================
async def setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    schedules = context.application.bot_data["schedules"]

    data = schedules.find({"user_id": user.id})
    kb = []

    for s in data:
        txt = s.get("pre_message", "")[:40]
        if len(s.get("pre_message", "")) > 40:
            txt += "..."
        kb.append([
            InlineKeyboardButton(
                f"✉️ {txt or 'No pre-message'}",
                callback_data=f"view:{s['_id']}"
            )
        ])

    if not kb:
        await update.message.reply_text("❌ No schedules found")
        return

    await update.message.reply_text(
        "⚙️ <b>Your schedules</b>",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )


# ================= CALLBACK ACTION =================
async def setting_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules = context.application.bot_data["schedules"]

    q = update.callback_query
    await q.answer()

    action, sid = q.data.split(":")
    sid = ObjectId(sid)

    s = schedules.find_one({"_id": sid})
    if not s:
        await q.edit_message_text("❌ Schedule not found")
        return

    # ---------- VIEW ----------
    if action == "view":
        premsg = s.get("pre_message", "No pre-message")
        title = premsg[:60] + ("..." if len(premsg) > 60 else "")

        kb = [
            [InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{sid}")],
            [InlineKeyboardButton(
                "⏸ Pause" if s["status"] == "active" else "▶ Resume",
                callback_data=f"{'pause' if s['status']=='active' else 'resume'}:{sid}"
            )],
            [InlineKeyboardButton("❌ Delete", callback_data=f"delete:{sid}")]
        ]

        await q.edit_message_text(
            f"✉️ <b>{title}</b>\n\n"
            f"⏰ Time: {s['time']}\n"
            f"🔢 Daily MCQ: {s['daily_limit']}\n"
            f"📊 Progress: {s['sent_mcq']} / {s['total_mcq']}\n"
            f"📌 Status: {s['status']}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

    # ---------- PAUSE ----------
    elif action == "pause":
        schedules.update_one({"_id": sid}, {"$set": {"status": "paused"}})
        remove_job(sid)
        await q.edit_message_text("⏸ Schedule paused")

    # ---------- RESUME ----------
    elif action == "resume":
        schedules.update_one({"_id": sid}, {"$set": {"status": "active"}})
        schedule_job(s, context.bot, schedules)
        await q.edit_message_text("▶ Schedule resumed")

    # ---------- DELETE ----------
    elif action == "delete":
        schedules.delete_one({"_id": sid})
        remove_job(sid)
        await q.edit_message_text("❌ Schedule deleted")

    # ---------- EDIT MENU ----------
    elif action == "edit":
        context.user_data["edit_sid"] = sid

        kb = [
            [InlineKeyboardButton("⏰ Edit Time", callback_data="edit_time")],
            [InlineKeyboardButton("🔢 Edit Daily MCQ", callback_data="edit_limit")],
            [InlineKeyboardButton("✉️ Edit Pre-message", callback_data="edit_premsg")]
        ]

        await q.edit_message_text(
            f"✏️ <b>Edit Schedule</b>\n\n"
            f"⏰ Time: {s['time']}\n"
            f"🔢 Daily MCQ: {s['daily_limit']}\n"
            f"✉️ Pre-message:\n{s['pre_message']}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )


# ================= EDIT SELECT =================
async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules = context.application.bot_data["schedules"]
    q = update.callback_query
    await q.answer()

    sid = context.user_data.get("edit_sid")
    if not sid:
        await q.message.reply_text("❌ Please select schedule again using /setting")
        return ConversationHandler.END

    s = schedules.find_one({"_id": sid})
    if not s:
        await q.message.reply_text("❌ Schedule not found")
        return ConversationHandler.END

    if q.data == "edit_time":
        context.user_data["edit_field"] = "time"
        text = f"⏰ Current Time: {s['time']}\nSend new time (HH:MM)"

    elif q.data == "edit_limit":
        context.user_data["edit_field"] = "daily_limit"
        text = f"🔢 Current Daily MCQ: {s['daily_limit']}\nSend new limit"

    elif q.data == "edit_premsg":
        context.user_data["edit_field"] = "pre_message"
        text = f"✉️ Current Pre-message:\n{s['pre_message']}\n\nSend new text"

    else:
        return ConversationHandler.END

    await q.message.reply_text(text)
    return EDIT_INPUT


# ================= EDIT INPUT =================
async def edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules = context.application.bot_data["schedules"]

    sid = context.user_data.get("edit_sid")
    field = context.user_data.get("edit_field")

    if not sid or not field:
        await update.message.reply_text("❌ Edit expired, use /setting again")
        return ConversationHandler.END

    value = update.message.text

    if field == "daily_limit":
        value = int(value)

    schedules.update_one({"_id": sid}, {"$set": {field: value}})

    if field == "time":
        remove_job(sid)
        s = schedules.find_one({"_id": sid})
        schedule_job(s, context.bot, schedules)
        msg = "⏰ Time updated & rescheduled"
    else:
        msg = "✅ Updated successfully"

    await update.message.reply_text(msg)
    return ConversationHandler.END


# ================= CANCEL =================
async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Edit cancelled")
    return ConversationHandler.END


# ================= REGISTER =================
def register_settings_handlers(app):
    app.add_handler(CommandHandler("setting", setting))

    app.add_handler(
        CallbackQueryHandler(
            setting_action,
            pattern="^(view|pause|resume|delete|edit):"
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(edit_select, pattern="^edit_")
            ],
            states={
                EDIT_INPUT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, edit_input)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_edit)],
            per_user=True,
            per_chat=True
        )
    )
