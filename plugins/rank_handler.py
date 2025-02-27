from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import csv
import io
    
def register_handlers(bot, quiz_collection, rank_collection):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("rank_"))
    def show_rank(call):
        chat_id = call.message.chat.id
        quiz_id = call.data.replace("rank_", "")
        user_id = call.from_user.id  # ✅ Store Current User ID
        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
            return
    
        sheet_id = quiz["sheet"]
    
       
    
        # ✅ If Not in MongoDB, Fetch Data from Google Sheet
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    
        try:
            response = requests.get(sheet_url)
            response.raise_for_status()
            data = response.text
    
            csv_reader = csv.reader(io.StringIO(data))
            rows = list(csv_reader)
    
            if len(rows) < 2:
                bot.send_message(chat_id, "❌ No quiz data found in the sheet!")
                return
    
            valid_records = {}
            total_marks = None
            user_score = None
            user_rank = None
            user_attempted = False  # ✅ Track if user attempted test
    
            for row in rows[1:]:  # Skip Header
                try:
                    if len(row) < 3:
                        continue  # ❌ Skip invalid rows
    
                    student_id = int(row[2].strip())  # ✅ Column C (3rd Column) → User ID
                    score_parts = row[1].strip().split("/")  # ✅ Column B (2nd Column) → "X / Y" Format
    
                    if len(score_parts) != 2:
                        continue  # ❌ Skip invalid score format
    
                    score = int(score_parts[0].strip())  # ✅ Extract Score
                    total = int(score_parts[1].strip())  # ✅ Extract Total Marks
    
                    if total_marks is None:
                        total_marks = total  # ✅ Set Total Marks
    
                    # ✅ Ignore Duplicate Attempts, Keep Only First Entry
                    if student_id not in valid_records:
                        valid_records[student_id] = score
    
                    # ✅ Track if user attempted test
                    if student_id == user_id:
                        user_attempted = True
    
                except (ValueError, IndexError) as e:
                    print(f"Skipping invalid row: {row} | Error: {e}")  # 🔍 Debugging
    
            if not valid_records:
                bot.send_message(chat_id, "❌ No valid scores found in the sheet! Check format.")
                return
    
            # ✅ Sort Users Based on Score (Descending)
            sorted_records = sorted(valid_records.items(), key=lambda x: x[1], reverse=True)
    
            # 🔹 Find User Rank
            for idx, (uid, score) in enumerate(sorted_records, 1):
                if uid == user_id:
                    user_rank = idx
                    user_score = score
    
            # ✅ If user did not attempt the test
            if not user_attempted:
                bot.send_message(chat_id, "❌ Aapne yeh test attend nahi kiya hai ya aapne apne predefined roll number ko badal diya hai!")
                return
            
            rank_text = f"📌 <b>Your Rank:</b> {user_rank}/{len(sorted_records)}\n"
            rank_text += f"📊 <b>Your Score:</b> {user_score}/{total_marks}\n\n"
            rank_text += "<b>🏅 Top 5 Players:</b>\n"
            top_5 = sorted_records[:5]
            for idx, (user_name, score) in enumerate(top_5, 1):
                rank_text += f"{idx}. {user_name} - {score} pts\n"
    
            bot.send_message(chat_id, rank_text, parse_mode="HTML")
    
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")
    
