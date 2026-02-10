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
from plugins.scheduler import schedule_job, remove_job

EDIT_INPUT = 100


async def setting(update, context, schedules):
    data = schedules.find({"user_id": update.effective_user.id})
    kb = []

    for s in data:
        txt = s["pre_message"][:40]
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


async def setting_action(update: Update, context: ContextTypes.DEFAULT_TYPE, schedules):
    q = update.callback_query
    await q.answer()

    action, sid = q.data.split(":")
    sid = ObjectId(sid)

    if action == "view":
        s = schedules.find_one({"_id": sid})

        premsg = s.get("pre_message", "No pre-message")
        premsg_title = premsg[:60] + ("..." if len(premsg) > 60 else "")

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
            f"✉️ <b>{premsg_title}</b>\n\n"
            f"⏰ Time: {s['time']}\n"
            f"🔢 Daily MCQ: {s['daily_limit']}\n"
            f"📊 Progress: {s['sent_mcq']} / {s['total_mcq']}\n"
            f"📌 Status: {s['status']}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

    elif action == "pause":
        schedules.update_one({"_id": sid}, {"$set": {"status": "paused"}})
        scheduler.remove_job(str(sid))
        await q.edit_message_text("⏸ Schedule paused")

    elif action == "resume":
        s = schedules.find_one({"_id": sid})
        h, m = map(int, s["time"].split(":"))
        scheduler.add_job(
            send_mcqs, "cron",
            hour=h, minute=m,
            args=[str(sid), context.bot],
            id=str(sid),
            replace_existing=True
        )
        schedules.update_one({"_id": sid}, {"$set": {"status": "active"}})
        await q.edit_message_text("▶ Schedule resumed")

    elif action == "delete":
        schedules.delete_one({"_id": sid})
        try:
            scheduler.remove_job(str(sid))
        except:
            pass
        await q.edit_message_text("❌ Schedule deleted")

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

# ================= EDIT =================
async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    sid = context.user_data["edit_sid"]
    s = schedules.find_one({"_id": sid})

    context.user_data["edit_state"] = EDIT_INPUT  # 🔥 IMPORTANT

    if q.data == "edit_time":
        context.user_data["edit_field"] = "time"
        await q.message.reply_text(
            f"⏰ <b>Current Time:</b> {s['time']}\n\n"
            f"Send new time (HH:MM)\n\n⬅️ /cancel to go back",
            parse_mode="HTML"
        )

    elif q.data == "edit_limit":
        context.user_data["edit_field"] = "daily_limit"
        await q.message.reply_text(
            f"🔢 <b>Current Daily MCQ:</b> {s['daily_limit']}\n\n"
            f"Send new limit\n\n⬅️ /cancel to go back",
            parse_mode="HTML"
        )

    elif q.data == "edit_premsg":
        context.user_data["edit_field"] = "pre_message"
        await q.message.reply_text(
            f"✉️ <b>Current Pre-message:</b>\n{s['pre_message']}\n\n"
            f"Send new pre-message\n\n⬅️ /cancel to go back",
            parse_mode="HTML"
        )

    return EDIT_INPUT


async def edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sid = context.user_data["edit_sid"]
    field = context.user_data["edit_field"]
    value = update.message.text

    if field == "limit":
        field = "daily_limit"
        value = int(value)

    schedules.update_one({"_id": sid}, {"$set": {field: value}})

    if field == "time":
        remove_old_job(sid)
        s = schedules.find_one({"_id": sid})
        schedule_job(s, context.bot)
        msg = "⏰ Time updated & rescheduled"
    else:
        msg = "✅ Change will apply from next schedule"

    await update.message.reply_text(msg)
    return ConversationHandler.END



async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    _, target = q.data.split(":")
    if target == "setting":
        await setting(q.message, context)


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Edit cancelled")
    context.user_data.clear()
    return ConversationHandler.END
