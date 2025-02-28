from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import csv
import io

def register_handlers(bot, quiz_collection, rank_collection):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("leaderboard_"))
    def show_leaderboard(call):
        chat_id = call.message.chat.id
        quiz_id = call.data.replace("leaderboard_", "")

        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
            return

        sheet_id = quiz["sheet"]
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

            for row in rows[1:]:  # Skip header
                try:
                    if len(row) < 3:
                        continue  # Skip invalid rows

                    student_id = int(row[2].strip())  # Column C (User ID)
                    score_parts = row[1].strip().split("/")  # Column B ("X / Y")

                    if len(score_parts) != 2:
                        continue  # Skip invalid score format

                    score = int(score_parts[0].strip())  # Extract Score
                    total = int(score_parts[1].strip())  # Extract Total Marks

                    if total_marks is None:
                        total_marks = total  # Set Total Marks

                    # Store only first valid attempt per user
                    if student_id not in valid_records:
                        valid_records[student_id] = score

                except (ValueError, IndexError) as e:
                    print(f"Skipping invalid row: {row} | Error: {e}")  # Debugging

            if not valid_records:
                bot.send_message(chat_id, "❌ No valid scores found in the sheet! Check format.")
                return

            # Sort Users Based on Score (Descending)
            sorted_records = sorted(valid_records.items(), key=lambda x: x[1], reverse=True)

            # Store in MongoDB for caching
            rank_collection.update_one(
                {"quiz_id": quiz_id},
                {"$set": {"leaderboard": sorted_records}},
                upsert=True
            )

            # Generate Leaderboard Text
            leaderboard_text = f"📊 <b>Leaderboard for {quiz['title']}:</b>\n"
            leaderboard_text += "🏆 Rank | 🏅 Score | 👤 Username\n"
            leaderboard_text += "--------------------------------\n"

            for idx, (uid, score) in enumerate(sorted_records[:20], 1):  # Limit to top 20
                try:
                    user_info = bot.get_chat(uid)
                    username = f"@{user_info.username}" if user_info.username else user_info.first_name
                except Exception as e:
                    print(f"Error fetching user {uid}: {e}")
                    username = "Unknown"

                leaderboard_text += f"🏅 {idx}. {score} pts | {username}\n"

            # Paginate if too long
            if len(leaderboard_text) > 4000:
                chunks = [leaderboard_text[i:i+4000] for i in range(0, len(leaderboard_text), 4000)]
                for chunk in chunks:
                    bot.send_message(chat_id, chunk, parse_mode="HTML")
            else:
                bot.send_message(chat_id, leaderboard_text, parse_mode="HTML")

        except requests.RequestException as e:
            bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")
