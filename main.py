from telegram.ext import Application
from plugins import scheduler, setting

BOT_TOKEN = "8151017957:AAGUXHkgWeh1Bp3E358A8YZwtfEjer6Qpsk"

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # load plugins
    scheduler.setup(app)
    setting.setup(app)

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
