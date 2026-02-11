import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

logger = logging.getLogger(__name__)

SET_CHOOSE, WAIT_DESCRIPTION = range(2)

DEFAULT_DESCRIPTION = "Join:- @How_To_Google"
MAX_LEN = 200


# =====================================================
# 🔹 GET DESCRIPTION FROM MONGODB
# =====================================================

def get_description_for_chat_id(users, chat_id: int):
    u = users.find_one({"channels.channel_id": chat_id})
    if not u:
        return DEFAULT_DESCRIPTION

    for ch in u.get("channels", []):
        if ch.get("channel_id") == chat_id:
            return ch.get("description", DEFAULT_DESCRIPTION)

    return DEFAULT_DESCRIPTION


# =====================================================
# 🔹 SAVE DESCRIPTION TO MONGODB
# =====================================================

def set_description(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    users = context.bot_data["users_collection"]

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    users.update_one(
        {
            "user_id": user_id,
            "channels.channel_id": chat_id
        },
        {
            "$set": {
                "channels.$.description": text
            }
        }
    )


# =====================================================
# 🔹 RESET DESCRIPTION (REMOVE FROM DB)
# =====================================================

def reset_to_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = context.bot_data["users_collection"]

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    users.update_one(
        {
            "user_id": user_id,
            "channels.channel_id": chat_id
        },
        {
            "$unset": {
                "channels.$.description": ""
            }
        }
    )


# =====================================================
# 🔹 COMMAND ENTRY
# =====================================================

async def set_channel_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = context.bot_data["users_collection"]
    chat_id = update.effective_chat.id

    desc = get_description_for_chat_id(users, chat_id)

    buttons = [
        InlineKeyboardButton("✏️ Edit Description", callback_data="edit_description")
    ]

    if desc != DEFAULT_DESCRIPTION:
        buttons.append(
            InlineKeyboardButton("❌ Delete Description", callback_data="delete_description")
        )

    reply_markup = InlineKeyboardMarkup([buttons])

    await update.message.reply_text(
        f"📌 Current Description:\n\n`{desc}`",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    return SET_CHOOSE


# =====================================================
# 🔹 BUTTON CALLBACK
# =====================================================

async def description_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "edit_description":
        await query.edit_message_text(
            "📝 Send new description (max 200 characters).\nSend /cancel to abort."
        )
        return WAIT_DESCRIPTION

    elif query.data == "delete_description":
        reset_to_default(update, context)

        await query.edit_message_text(
            f"🗑️ Description reset to default:\n\n`{DEFAULT_DESCRIPTION}`",
            parse_mode="Markdown"
        )
        return ConversationHandler.END


# =====================================================
# 🔹 RECEIVE NEW DESCRIPTION
# =====================================================

async def receive_new_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "⚠️ Empty description — please send some text or /cancel."
        )
        return WAIT_DESCRIPTION

    if len(text) > MAX_LEN:
        await update.message.reply_text(
            f"⚠️ Description {MAX_LEN} characters se zyada nahi ho sakti.\n"
            f"Abhi {len(text)} characters hain. Kripya chhota karke bhejein."
        )
        return WAIT_DESCRIPTION

    set_description(update, context, text)

    await update.message.reply_text(
        f"✅ New description set:\n\n`{text}`",
        parse_mode="Markdown"
    )

    return ConversationHandler.END


# =====================================================
# 🔹 CANCEL HANDLER
# =====================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Operation cancelled.")
    else:
        await update.message.reply_text("❌ Operation cancelled.")

    return ConversationHandler.END


# =====================================================
# 🔹 HANDLER EXPORT
# =====================================================

def get_set_description_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("setchanneldescription", set_channel_description)
        ],
        states={
            SET_CHOOSE: [
                CallbackQueryHandler(
                    description_choice_callback,
                    pattern="^(edit_description|delete_description)$"
                )
            ],
            WAIT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_description)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True,
        allow_reentry=True
    )
