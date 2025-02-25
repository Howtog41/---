import telebot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI")

bot = telebot.TeleBot(TOKEN)

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
