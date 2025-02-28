from telegram.ext import Application, MessageHandler, filters
from telegram import Update 
TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"


async def raw_update(update: Update, context):
    print(f"\n📩 FULL RAW UPDATE:\n{update.to_dict()}")  # Yeh poora JSON structure print karega

app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, raw_update))

print("🤖 Debugging Bot Started...")
app.run_polling()
