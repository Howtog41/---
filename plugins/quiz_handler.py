import random
import re
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import quiz_collection
from main import bot  # Import bot instance
print("✅ quiz_handler.py loaded!") 
# 🔍 Extract Google Sheet ID
def extract_sheet_id(sheet_url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    return match.group(1) if match else None

# 🔍 Extract Google Form Title
def extract_form_title(form_url):
    try:
        response = requests.get(form_url)
        response.raise_for_status()
        title_match = re.search(r"<title>(.*?)</title>", response.text)
        return title_match.group(1) if title_match else "Quiz"
    except:
        return "Quiz"

# ✅ Register Quiz Command
@bot.message_handler(commands=['form_quiz'])
def register_quiz(message):
    print("✅ form_quiz command received!")
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
    
    # Store in MongoDB
    quiz_collection.insert_one({
        "quiz_id": quiz_id,
        "title": quiz_title,
        "form": form_link,
        "sheet": sheet_id
    })

    shareable_link = f"https://t.me/{bot.get_me().username}?start=quiz_{quiz_id}"

    bot.send_message(chat_id, f"✅ Quiz Registered!\n<b>Quiz ID:</b> <code>{quiz_id}</code>\n📢 Share this link:\n<a href='{shareable_link}'>Click Here</a>", parse_mode="HTML")

# ✅ Start Quiz from Link
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

    user_id = str(message.from_user.id)
    custom_form_link = form_link.replace("YourName", user_id)

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
