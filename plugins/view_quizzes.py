from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_handlers(bot, quiz_collection):
    @bot.message_handler(commands=['view_quizzes'])
    def view_quizzes(message, page=1):
        chat_id = message.chat.id
        quizzes_per_page = 10
        skip_count = (page - 1) * quizzes_per_page
        
        # Fetch quizzes from MongoDB
        quizzes = list(quiz_collection.find().skip(skip_count).limit(quizzes_per_page))
        total_quizzes = quiz_collection.count_documents({})
        
        if not quizzes:
            bot.send_message(chat_id, "❌ No quizzes found!")
            return
        
        markup = InlineKeyboardMarkup()
        for quiz in quizzes:
            quiz_id = quiz.get("quiz_id", "N/A")
            quiz_title = quiz.get("title", "Untitled Quiz")
            markup.add(InlineKeyboardButton(f"📋 {quiz_title}", callback_data=f"quiz_details_{quiz_id}"))
        
        # Pagination buttons
        buttons = []
        if page > 1:
            buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"quizzes_page_{page-1}"))
        if skip_count + quizzes_per_page < total_quizzes:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"quizzes_page_{page+1}"))
        
        if buttons:
            markup.add(*buttons)
        
        bot.send_message(chat_id, "📚 <b>Available Quizzes:</b>", reply_markup=markup, parse_mode="HTML")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("quizzes_page_"))
    def paginate_quizzes(call):
        page = int(call.data.split("_")[2])
        view_quizzes(call.message, page)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_details_"))
    def quiz_details(call):
        chat_id = call.message.chat.id
        quiz_id = call.data.replace("quiz_details_", "")
        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        
        if not quiz:
            bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
            return
        
        quiz_title = quiz.get("title", "Untitled Quiz")
        quiz_desc = quiz.get("description", "No description available.")
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✏️ Edit Quiz", callback_data=f"edit_quiz_{quiz_id}"))
        markup.add(InlineKeyboardButton("📤 Share Quiz", switch_inline_query=quiz_id))
        markup.add(InlineKeyboardButton("🗑️ Delete Quiz", callback_data=f"delete_quiz_{quiz_id}"))
        markup.add(InlineKeyboardButton("📊 Leaderboard", callback_data=f"leaderboard_{quiz_id}"))
        
        bot.send_message(chat_id, f"📌 <b>{quiz_title}</b>\n📝 {quiz_desc}", reply_markup=markup, parse_mode="HTML")
