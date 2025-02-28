from telegram.ext import Application, MessageHandler, filters, CommandHandler

TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"

# 🟢 Function to detect quiz bot messages & delete them
async def detect_and_delete(update, context):
    message = update.message
    chat_id = message.chat_id

    # ✅ Check if message is from QuizBot
    if message.via_bot and message.via_bot.username == "QuizBot":
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            print("✅ QuizBot message deleted successfully!")  
        except Exception as e:
            print(f"❌ Error deleting message: {e}")

# 🏆 Function to send leaderboard after deleting quizbot message
async def send_leaderboard(update, context):
    chat_id = update.effective_chat.id
    
    # ✅ Delete last quizbot message before sending leaderboard
    async for msg in context.bot.get_chat_history(chat_id, limit=10):
        if msg.via_bot and msg.via_bot.username == "QuizBot":
            await context.bot.delete_message(chat_id, msg.message_id)
            break  # Delete only the latest quiz result
    
    # ✅ Send Leaderboard
    leaderboard_text = "🏆 **Final Leaderboard:**\n1️⃣ User1 - 100 pts\n2️⃣ User2 - 90 pts\n3️⃣ User3 - 80 pts"
    await context.bot.send_message(chat_id=chat_id, text=leaderboard_text)

# ✅ Setup Telegram Bot
app = Application.builder().token(TOKEN).build()

# 🟢 Detect QuizBot messages & delete them
app.add_handler(MessageHandler(filters.ALL, detect_and_delete))

# 🏆 Leaderboard Command
app.add_handler(CommandHandler("leaderboard", send_leaderboard))

app.run_polling()
