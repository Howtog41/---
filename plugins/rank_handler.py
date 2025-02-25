import requests
import csv
import io
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_rank_handlers(bot, quiz_collection, rank_collection):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("rank_"))
    def show_rank(call):
        chat_id = call.message.chat.id
        quiz_id = call.data.replace("rank_", "")
        user_id = call.from_user.id
        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
            return

        sheet_id = quiz["sheet"]

        user_rank_data = rank_collection.find_one({"quiz_id": quiz_id, "user_id": user_id})
        
        if user_rank_data:
            send_rank_message(bot, chat_id, user_rank_data, rank_collection, quiz_id)
            return

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

            for row in rows[1:]:
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
                except:
                    continue

            if not valid_records:
                bot.send_message(chat_id, "❌ No valid scores found in the sheet! Check format.")
                return

            sorted_records = sorted(valid_records.items(), key=lambda x: x[1], reverse=True)

            for idx, (uid, score) in enumerate(sorted_records, 1):
                if uid == user_id:
                    user_rank = idx
                    user_score = score

            if not user_attempted:
                bot.send_message(chat_id, "❌ आपने यह टेस्ट नहीं दिया है या आपका रोल नंबर गलत है!")
                return
            
            rank_collection.insert_one({
                "quiz_id": quiz_id,
                "user_id": user_id,
                "rank": user_rank,
                "score": user_score,
                "total_marks": total_marks,
                "total_users": len(sorted_records)
            })

            send_rank_message(bot, chat_id, {
                "rank": user_rank,
                "score": user_score,
                "total_marks": total_marks,
                "total_users": len(sorted_records)
            }, rank_collection, quiz_id)

        except Exception as e:
            bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")

def send_rank_message(bot, chat_id, user_rank_data, rank_collection, quiz_id):
    all_ranks = list(rank_collection.find({"quiz_id": quiz_id}))
    sorted_records = sorted(all_ranks, key=lambda x: x['score'], reverse=True)
    
    top_5 = []
    for record in sorted_records[:5]:
        try:
            user_info = bot.get_chat(record["user_id"])
            username = f"@{user_info.username}" if user_info.username else user_info.first_name or "Unknown"
            top_5.append((username, record["score"]))
        except:
            continue
    
    rank_text = (
        f"📌 <b>Your Rank:</b> {user_rank_data['rank']}/{user_rank_data['total_users']}\n"
        f"📊 <b>Your Score:</b> {user_rank_data['score']}/{user_rank_data['total_marks']}\n\n"
        "<b>🏅 Top 5 Players:</b>\n"
    )

    for idx, (user_name, score) in enumerate(top_5, 1):
        rank_text += f"{idx}. {user_name} - {score} pts\n"

    bot.send_message(chat_id, rank_text, parse_mode="HTML")
