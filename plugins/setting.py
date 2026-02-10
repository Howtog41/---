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
    schedules = context.application.bot_data["schedules"]

    data = schedules.find({"user_id": message.from_user.id})
    kb = []

    for s in data:
        txt = s["pre_message"][:40]
        if len(s["pre_message"]) > 40:
            txt += "..."
        kb.append([
            InlineKeyboardButton(
                f"✉️ {txt}",
                callback_data=f"view:{s['_id']}"
            )
        ])

    if not kb:
        await update.message.reply_text("❌ No schedules")
        return

    await update.message.reply_text(
        "⚙ Your schedules",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ================= CALLBACK ACTION =================
async def setting_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules = context.application.bot_data["schedules"]

    q = update.callback_query
    await q.answer()

    action, sid = q.data.split(":")
    sid = ObjectId(sid)

    # ---------- VIEW ----------
    if action == "view":
        s = schedules.find_one({"_id": sid})

        premsg = s.get("pre_message", "No pre-message")
        title = premsg[:60] + ("..." if len(premsg) > 60 else "")

        kb = [
            [InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{sid}")],
            [InlineKeyboardButton(
                "⏸ Pause" if s["status"] == "active" else "▶ Resume",
                callback_data=f"{'pause' if s['status']=='active' else 'resume'}:{sid}"
            )],
            [InlineKeyboardButton("❌ Delete", callback_data=f"delete:{sid}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back:setting")]
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
        s = schedules.find_one({"_id": sid})
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
        s = schedules.find_one({"_id": sid})
        context.user_data["edit_sid"] = sid

        kb = [
            [InlineKeyboardButton("⏰ Edit Time", callback_data="edit_time")],
            [InlineKeyboardButton("🔢 Edit Daily MCQ", callback_data="edit_limit")],
            [InlineKeyboardButton("✉️ Edit Pre-message", callback_data="edit_premsg")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"view:{sid}")]
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
        await q.message.reply_text("❌ No schedule selected")
        return ConversationHandler.END

    s = schedules.find_one({"_id": sid})
    if not s:
        await q.message.reply_text("❌ Schedule not found")
        return ConversationHandler.END

    if q.data == "edit_time":
        context.user_data["edit_field"] = "time"
        text = f"⏰ Current Time: {s.get('time','Not set')}\nSend new time (HH:MM)"

    elif q.data == "edit_limit":
        context.user_data["edit_field"] = "daily_limit"
        text = f"🔢 Current Daily MCQ: {s.get('daily_limit',0)}\nSend new limit"

    elif q.data == "edit_premsg":
        context.user_data["edit_field"] = "pre_message"
        text = f"✉️ Current Pre-message:\n{s.get('pre_message','Not set')}\n\nSend new text"

    else:
        return ConversationHandler.END

    await q.message.reply_text(text)
    return EDIT_INPUT


# ================= EDIT INPUT =================
async def edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules = context.application.bot_data["schedules"]

    sid = context.user_data["edit_sid"]
    field = context.user_data["edit_field"]
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
        msg = "✅ Change will apply from next schedule"

    await update.message.reply_text(msg)
    context.user_data.clear()
    return ConversationHandler.END


# ================= BACK =================
async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, target = q.data.split(":")
    if target == "setting":
        await setting(q.message, context)


# ================= CANCEL =================
async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Edit cancelled")
    return ConversationHandler.END



def register_settings_handlers(app):

    app.add_handler(
        CommandHandler("setting", lambda u, c: setting(u.message, c))
    )
    app.add_handler(
        CallbackQueryHandler(
            setting_action,
            pattern="^(view|pause|resume|delete|edit):"
        )
    )
    app.add_handler(
        CallbackQueryHandler(back_handler, pattern="^back:")
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
