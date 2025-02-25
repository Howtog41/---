import re
import random
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def extract_sheet_id(sheet_url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    return match.group(1) if match else None

def extract_form_title(form_url):
    try:
        response = requests.get(form_url)
        response.raise_for_status()
        title_match = re.search(r"<title>(.*?)</title>", response.text)
        return title_match.group(1) if title_match else "Quiz"
    except:
        return "Quiz"

def register_handlers(bot, quiz_collection, rank_collection):
    @bot.message_handler(commands=['form_quiz'])
    def register_quiz(message):
        chat_id = message.chat.id
        bot.send_message(chat_id, "📌 Send the Google Form link:")
        bot.register_next_step_handler(message, get_form_link, chat_id)

    def get_form_link(message, chat_id):
        form_link = message.text
        quiz_title = extract_form_title(form_link)
        bot.send_message(chat_id, "📌 Now send the Google Sheet (Responses) link:")
        bot.register_next_step_handler(message, get_sheet_link, chat_id, form_link, quiz_title)

    def get_sheet_link(message, chat_id, form_link, quiz_title):
        sheet_link = message.text
        sheet_id = extract_sheet_id(sheet_link)

        if not sheet_id:
            bot.send_message(chat_id, "❌ Invalid Google Sheet link! Please send a correct link.")
            return

        quiz_id = str(random.randint(1000, 9999))
        quiz_collection.insert_one({
            "quiz_id": quiz_id,
            "title": quiz_title,
            "form": form_link,
            "sheet": sheet_id
        })
        shareable_link = f"https://t.me/{bot.get_me().username}?start=quiz_{quiz_id}"

        bot.send_message(chat_id, f"✅ Quiz Registered!\n<b>Quiz ID:</b> <code>{quiz_id}</code>\n📢 Share this link:\n<a href='{shareable_link}'>Click Here</a>", parse_mode="HTML")
