import telebot
import os
from dotenv import load_dotenv
from config import BOT_TOKEN

# Load environment variables
load_dotenv()

bot = telebot.TeleBot(BOT_TOKEN)

# Load plugins dynamically
def load_plugins():
    plugins_dir = "plugins"
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"plugins.{filename[:-3]}"
            __import__(module_name)

load_plugins()

# Start the bot
print("Bot is running...")
bot.infinity_polling()
