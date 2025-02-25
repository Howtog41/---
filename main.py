import telebot
import os
from config import BOT_TOKEN
from importlib import import_module

bot = telebot.TeleBot(BOT_TOKEN)

# ✅ Auto-load all plugins from the 'plugins' folder
def load_plugins():
    
    for filename in os.listdir("plugins"):
        if filename.endswith(".py") and filename != "__init__.py":
            import_module(f"plugins.{filename[:-3]}")


if __name__ == "__main__":  # ✅ Avoid duplicate execution
    load_plugins()
    print("🚀 Bot started successfully!")
    bot.infinity_polling()
