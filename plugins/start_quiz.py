from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_handlers(bot, quiz_collection, rank_collection):
    @bot.message_handler(commands=['start'])
    def start_quiz_from_link(message):
        chat_id = message.chat.id
        msg_parts = message.text.split()

        if len(msg_parts) < 2 or not msg_parts[1].startswith("quiz_"):
            bot.send_message(chat_id, "❌ Invalid Quiz Link! Please use a valid shared link.")
            return

        quiz_id = msg_parts[1].replace("quiz_", "")
        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            bot.send_message(chat_id, "❌ Quiz not found! Please check the link and try again.")
            return

        quiz_title = quiz["title"]
        form_link = quiz["form"]

        # ✅ Extract Telegram User ID & Generate Prefilled Link
        user_id = str(message.from_user.id)  # Convert to string for URL
        custom_form_link = form_link.replace("YourName", user_id)  

        # ✅ Inline Keyboard for Start Test & Your Rank
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🟢 Start Test", url=custom_form_link),
            InlineKeyboardButton("📊 Your Rank", callback_data=f"rank_{quiz_id}")
        )

        bot.send_message(
            chat_id,
            f"📌 *{quiz_title}*\n\nClick below to start the test or check your rank.",
            parse_mode="Markdown",
            reply_markup=markup
        )
