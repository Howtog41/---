import telebot
import os
import importlib
import random
import requests
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from plugins import rank_handler
# ✅ MongoDB Connection
MONGO_URI = "mongodb+srv://terabox255:h9PjRSpCHsHw5zzt@cluster0.nakwhlt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["quiz_bot_db"]
quiz_collection = db["quizzes"]
rank_collection = db["rankings"]

# ✅ Bot Token
BOT_TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
bot = telebot.TeleBot(BOT_TOKEN)

# 🔍 Extract Google Sheet ID from the given link
def extract_sheet_id(sheet_url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    return match.group(1) if match else None

# 🔍 Extract Google Form Title from the HTML Content
def extract_form_title(form_url):
    try:
        response = requests.get(form_url)
        response.raise_for_status()
        title_match = re.search(r"<title>(.*?)</title>", response.text)
        return title_match.group(1) if title_match else "Quiz"
    except:
        return "Quiz"

# ✅ Dynamically Load Plugins
def load_plugins():
    plugin_folder = 'plugins'
    if not os.path.exists(plugin_folder):
        os.makedirs(plugin_folder)  # Create folder if not exists

    for file in os.listdir(plugin_folder):
        if file.endswith('.py') and file != '__init__.py':
            module_name = f"plugins.{file[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'register_handlers'):
                module.register_handlers(bot, quiz_collection, rank_collection)

# ✅ Load Plugins on Startup
load_plugins()

# ✅ Start Bot
print("Bot is running...")
bot.polling(none_stop=True)
