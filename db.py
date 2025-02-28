from telegram.ext import Application, MessageHandler, filters, CommandHandler
import asyncio

TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"

# ✅ Store last quizbot message to delete later
last_quizbot_message_id = {}

# ✅ Detect & store QuizBot message
async def detect_quizbot_message(update, context):
    message = update.message
    chat_id = message.chat_id

    # ✅ Check if message is from QuizBot
    if message.via_bot and message.via_bot.username == "QuizBot":
        last_quizbot_message_id[chat_id] = message.message_id  # Store the message ID
        print(f"✅ Stored QuizBot message ID: {message.message_id}")

# 🏆 Delete last QuizBot message & send leaderboard
async def delete_and_send_leaderboard(update, context):
    chat_id = update.effective_chat.id

    # ✅ Check if we have a stored QuizBot message
    if chat_id in last_quizbot_message_id:
        try:
            await context.bot.delete_message(chat_id, last_quizbot_message_id[chat_id])
            print(f"✅ Deleted QuizBot message ID: {last_quizbot_message_id[chat_id]}")
            del last_quizbot_message_id[chat_id]  # Remove from storage
        except Exception as e:
            print(f"❌ Error deleting message: {e}")

    # ✅ Send Leaderboard
    leaderboard_text = "🏆 **Final Leaderboard:**\n1️⃣ User1 - 100 pts\n2️⃣ User2 - 90 pts\n3️⃣ User3 - 80 pts"
    await context.bot.send_message(chat_id=chat_id, text=leaderboard_text)

# ✅ Setup Telegram Bot
app = Application.builder().token(TOKEN).build()

# 🟢 Detect & store QuizBot messages
app.add_handler(MessageHandler(filters.ALL, detect_quizbot_message))

# 🏆 Command to delete QuizBot message & send leaderboard
app.add_handler(CommandHandler("leaderboard", delete_and_send_leaderboard))

print("🤖 Bot Started...")
app.run_polling()
