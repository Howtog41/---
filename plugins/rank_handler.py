from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import csv
import io

def register_handlers(bot, rank_collection, quiz_collection):
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

        # ✅ Check if user rank is in MongoDB
        user_rank_data = rank_collection.find_one({"quiz_id": quiz_id, "user_id": user_id})

        if user_rank_data:
            bot.send_message(chat_id, f"📌 Your Rank: {user_rank_data['rank']} / {user_rank_data['total_users']}\n"
                                      f"📊 Your Score: {user_rank_data['score']} / {user_rank_data['total_marks']}", parse_mode="HTML")
            return

        # ✅ Fetch Data from Google Sheet
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
            user_attempted = False  

            for row in rows[1:]:  # Skip Header
                try:
                    if len(row) < 3:
                        continue  

                    student_id = int(row[2].strip())  
                    score_parts = row[1].strip().split("/")  

                    if len(score_parts) != 2:
                        continue  

                    score = int(score_parts[0].strip())  
                    total = int(score_parts[1].strip())  

                    if total_marks is None:
                        total_marks = total  

                    if student_id not in valid_records:
                        valid_records[student_id] = score

                    if student_id == user_id:
                        user_attempted = True

                except (ValueError, IndexError) as e:
                    print(f"Skipping invalid row: {row} | Error: {e}")  

            if not valid_records:
                bot.send_message(chat_id, "❌ No valid scores found in the sheet! Check format.")
                return

            sorted_records = sorted(valid_records.items(), key=lambda x: x[1], reverse=True)

            for idx, (uid, score) in enumerate(sorted_records, 1):
                if uid == user_id:
                    user_rank = idx
                    user_score = score

            if not user_attempted:
                bot.send_message(chat_id, "❌ आपने यह टेस्ट नहीं दिया या आपका Telegram ID डेटा में नहीं है!")
                return

            rank_collection.insert_one({
                "quiz_id": quiz_id,
                "user_id": user_id,
                "rank": user_rank,
                "score": user_score,
                "total_marks": total_marks,
                "total_users": len(sorted_records)
            })

            bot.send_message(chat_id, f"📌 Your Rank: {user_rank}/{len(sorted_records)}\n"
                                      f"📊 Your Score: {user_score}/{total_marks}", parse_mode="HTML")

        except Exception as e:
            bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")

