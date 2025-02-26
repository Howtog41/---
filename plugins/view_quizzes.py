from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

def register_handlers(bot, quiz_collection, rank_collection):
    def get_pagination_buttons(page, total_pages):
        buttons = []
        if total_pages <= 5:
            pages = list(range(1, total_pages + 1))
        else:
            if page <= 3:
                pages = [1, 2, 3, '...', total_pages]
            elif page >= total_pages - 2:
                pages = [1, '...', total_pages - 2, total_pages - 1, total_pages]
            else:
                pages = [1, '...', page - 1, page, page + 1, '...', total_pages]
        
        for p in pages:
            if p == '...':
                buttons.append(InlineKeyboardButton("...", callback_data="ignore"))
            else:
                buttons.append(InlineKeyboardButton(str(p), callback_data=f"quizzes_page_{p}"))
        
        return buttons
    
    @bot.message_handler(commands=['view_quizzes'])
    def view_quizzes(message, page=1, edit=False, call=None):
        chat_id = message.chat.id if not call else call.message.chat.id
        quizzes_per_page = 10
        skip_count = (page - 1) * quizzes_per_page
        
        quizzes = list(quiz_collection.find().skip(skip_count).limit(quizzes_per_page))
        total_quizzes = quiz_collection.count_documents({})
        total_pages = -(-total_quizzes // quizzes_per_page)
        
        if not quizzes:
            bot.send_message(chat_id, "❌ No quizzes found!")
            return
        
        markup = InlineKeyboardMarkup()
        for quiz in quizzes:
            quiz_id = quiz.get("quiz_id", "N/A")
            quiz_title = quiz.get("title", "Untitled Quiz")
            markup.add(InlineKeyboardButton(f"📋 {quiz_title}", callback_data=f"quiz_details_{quiz_id}"))
        
        if total_pages > 1:
            pagination_buttons = get_pagination_buttons(page, total_pages)
            markup.add(*pagination_buttons)
        
        if edit:
            bot.edit_message_text("📚 <b>Available Quizzes:</b>", chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "📚 <b>Available Quizzes:</b>", reply_markup=markup, parse_mode="HTML")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("quizzes_page_"))
    def paginate_quizzes(call):
        page = int(call.data.split("_")[2])
        view_quizzes(call.message, page=page, edit=True, call=call)
    
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
        
        bot.edit_message_text(f"📌 <b>{quiz_title}</b>\n📝 {quiz_desc}", chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
    def edit_quiz(call):
        quiz_id = call.data.replace("edit_", "")
        bot.send_message(call.message.chat.id, f"📝 Editing quiz {quiz_id}... (Functionality to be added)")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
    def delete_quiz(call):
        quiz_id = call.data.replace("delete_", "").strip()  # Extra spaces remove karo

        print(f"🔍 Trying to delete quiz with ID: {quiz_id}")
        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        print(type(quiz["quiz_id"]))
        result = quiz_collection.delete_one({"quiz_id": quiz_id})  # ✅ Directly delete

        if result.deleted_count > 0:
            bot.answer_callback_query(call.id, "✅ Quiz deleted successfully!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)

    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("leaderboard_"))
    def quiz_leaderboard(call):
        quiz_id = call.data.replace("leaderboard_", "")
        bot.send_message(call.message.chat.id, f"📊 Fetching leaderboard for quiz {quiz_id}... (Functionality to be added)")

