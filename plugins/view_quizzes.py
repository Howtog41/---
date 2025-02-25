from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_handlers(bot, quiz_collection, rank_collection):
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
        
        text = "<b>Your Quizzes</b>\n\n"
        for i, quiz in enumerate(quizzes, start=skip_count + 1):
            quiz_id = quiz.get("quiz_id", "N/A")
            quiz_title = quiz.get("title", "Untitled Quiz")
            creator = quiz.get("creator", "@SecondCoaching")
            participants = quiz.get("participants", 0)
            text += f"{i}. {quiz_title} by {creator}   {participants} people answered\n\n/view_{quiz_id}\n\n"
        
        # Pagination Buttons
        markup = InlineKeyboardMarkup()
        buttons = []
        total_pages = (total_quizzes + quizzes_per_page - 1) // quizzes_per_page
        
        if total_pages > 1:
            visible_pages = [1, 2, 3] if page < 4 else [page - 1, page, page + 1]
            if page > 4:
                visible_pages.insert(0, "...")
            if page < total_pages - 2:
                visible_pages.append("...")
            visible_pages.extend([total_pages - 1, total_pages])
        
            for p in visible_pages:
                if p == "...":
                    buttons.append(InlineKeyboardButton("...", callback_data="ignore"))
                else:
                    buttons.append(InlineKeyboardButton(str(p), callback_data=f"quizzes_page_{p}"))
            
            markup.add(*buttons)
        
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("quizzes_page_"))
    def paginate_quizzes(call):
        page = int(call.data.split("_")[2])
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=view_quizzes(call.message, page), parse_mode="HTML")
    
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
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"📌 <b>{quiz_title}</b>\n📝 {quiz_desc}", reply_markup=markup, parse_mode="HTML")
