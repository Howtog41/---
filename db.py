from telegram.ext import Application, MessageHandler, filters, CommandHandler
import asyncio

TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"

# ✅ Store last QuizBot message ID
last_quizbot_message_id = {}

# 🟢 `/start` command
async def start(update, context):
    await update.message.reply_text("🤖 Bot is running! Send a quiz result to test deletion.")

# ✅ Detect & store QuizBot message
async def detect_quizbot_message(update, context):
    message = update.message
    chat_id = message.chat_id

    # ✅ Check if message is from QuizBot
    if message.via_bot:
        print(f"📩 Received message from: {message.via_bot.username}")  # Debugging
        if message.via_bot.username == "QuizBot":  # Ensure it's from QuizBot
            last_quizbot_message_id[chat_id] = message.message_id
            print(f"✅ Stored QuizBot message ID: {message.message_id}")

# 🏆 Delete last QuizBot message & send leaderboard
async def delete_and_send_leaderboard(update, context):
    chat_id = update.effective_chat.id

    if chat_id in last_quizbot_message_id:
        try:
            print(f"🗑 Trying to delete message ID: {last_quizbot_message_id[chat_id]}")
            await asyncio.sleep(2)  # Short delay
            await context.bot.delete_message(chat_id, last_quizbot_message_id[chat_id])
            print(f"✅ Deleted QuizBot message ID: {last_quizbot_message_id[chat_id]}")
            del last_quizbot_message_id[chat_id]  # Remove from storage
        except Exception as e:
            print(f"❌ Error deleting message: {e}")

    # ✅ Send Leaderboard
    await asyncio.sleep(1)  # Short delay before sending leaderboard
    leaderboard_text = "🏆 **Final Leaderboard:**\n1️⃣ User1 - 100 pts\n2️⃣ User2 - 90 pts\n3️⃣ User3 - 80 pts"
    await context.bot.send_message(chat_id=chat_id, text=leaderboard_text)

# ✅ Setup Telegram Bot
app = Application.builder().token(TOKEN).build()

# 🟢 `/start` command
app.add_handler(CommandHandler("start", start))

# 🟢 Detect & store QuizBot messages
app.add_handler(MessageHandler(filters.ALL, detect_quizbot_message))

# 🏆 Command to delete QuizBot message & send leaderboard
app.add_handler(CommandHandler("leaderboard", delete_and_send_leaderboard))

print("🤖 Bot Started...")
app.run_polling()
