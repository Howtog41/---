import os
from pymongo import MongoClient
from telegram.ext import Application

from plugins.schedule_flow import register_schedulemcq_handlers
from plugins.setting import register_settings_handlers
from plugins.auth import register_auth_handlers
from plugins.start import register_start_handlers
from plugins.scheduler import start_scheduler, restore_jobs
from handlers.set_description import get_set_description_handler

BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"
MONGO_URI = "mongodb+srv://terabox255:a8its4KrW06OhifE@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"


DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- DB ----------
mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]

schedules = db["schedules"]
users = db["users"]


# ---------- STARTUP ----------
async def on_startup(app):
    app.bot_data["schedules"] = schedules
    app.bot_data["users"] = users

    start_scheduler()
    restore_jobs(app, schedules)

    print("✅ Scheduler restored")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(get_set_description_handler())
    # 🔹 REGISTER PLUGINS
    register_start_handlers(app)
    register_auth_handlers(app)
    register_schedulemcq_handlers(app)
    register_settings_handlers(app)

    print("🤖 BOT RUNNING")
    app.run_polling()


if __name__ == "__main__":
    main()
