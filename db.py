from telegram.ext import Application, MessageHandler, filters

TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"

async def debug_message(update, context):
    message = update.message
    chat_id = message.chat_id

    print("\n📩 NEW MESSAGE RECEIVED:")
    print(f"- Chat ID: {chat_id}")
    print(f"- Message ID: {message.message_id}")
    print(f"- Text: {message.text if message.text else 'No Text'}")
    print(f"- Via Bot: {message.via_bot.username if message.via_bot else 'No Bot'}")
    print(f"- Forwarded: {'Yes' if message.forward_date else 'No'}")
    print(f"- Reply To: {message.reply_to_message.message_id if message.reply_to_message else 'No Reply'}")

app = Application.builder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, debug_message))

print("🤖 Debugging Bot Started...")
app.run_polling()
