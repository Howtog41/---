import telebot
import importlib
import os
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

# ✅ Auto-load all plugins from the 'plugins' folder
def load_plugins():
    plugin_path = "plugins"
    for filename in os.listdir(plugin_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{plugin_path}.{filename[:-3]}"
            print(f"🔄 Loading {module_name}")
            importlib.import_module(module_name)

load_plugins()

print("Bot started successfully!")
bot.polling(none_stop=True)
