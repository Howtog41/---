import os
from datetime import datetime
from pymongo import MongoClient
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, ConversationHandler,
    CallbackQueryHandler, filters
)
from plugins.schedule_flow import (
    schedulemcq, get_csv, get_limit,
    get_time, get_channel, get_premsg,
    CSV, LIMIT, TIME, CHANNEL, PREMSG
)
from plugins.mcqsend import validate_csv
from plugins.scheduler import start_scheduler, restore_jobs, schedule_job
from plugins.setting import setting, setting_action

BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"
MONGO_URI = "mongodb+srv://terabox255:a8its4KrW06OhifE@cluster0.1gfjb8w.mongodb.net/?appName=Cluster0"

CSV, LIMIT, TIME, CHANNEL, PREMSG = range(5)

mongo = MongoClient(MONGO_URI)
db = mongo["mcq_bot"]
schedules = db["schedules"]

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


async def on_startup(app):
    app.bot_data["schedules"] = schedules
    start_scheduler()
    restore_jobs(app, schedules)
    print("✅ Scheduler restored")


async def start(update, context):
    await update.message.reply_text(
        "/schedulemcq – New schedule\n"
        "/setting – Manage schedules"
    )


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(
        "setting",
        lambda u, c: setting(u, c, schedules)
    ))
    app.add_handler(
        CallbackQueryHandler(
            lambda u, c: setting_action(u, c, schedules),
            pattern="^(pause|resume|delete|view):"
        )
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("schedulemcq", schedulemcq)],
        states={
            CSV: [MessageHandler(filters.Document.ALL, get_csv)],
            LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_limit)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channel)],
            PREMSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_premsg)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)


    
    print("🤖 BOT RUNNING")
    app.run_polling()


if __name__ == "__main__":
    main()
