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

                except (ValueError, IndexError) as e:
                    print(f"Skipping invalid row: {row} | Error: {e}")  # 🔍 Debugging

            if not valid_records:
                bot.send_message(chat_id, "❌ No valid scores found in the sheet! Check format.")
                return

            # ✅ Sort Users Based on Score (Descending)
            sorted_records = sorted(valid_records.items(), key=lambda x: x[1], reverse=True)

            # 🔹 Generate Leaderboard Text
            leaderboard_text = f"📊 <b>Leaderboard for {quiz['title']}:</b>\n"
            leaderboard_text += "🏆 Rank | 🏅 Score | 👤 Username\n"
            leaderboard_text += "--------------------------------\n"

            for idx, (uid, score) in enumerate(sorted_records, 1):
                try:
                    user_info = bot.get_chat(uid)  # ✅ Fetch User Info
                    username = f"@{user_info.username}" if user_info.username else user_info.first_name
                except:
                    username = "Unknown"  # ✅ If username not found

                leaderboard_text += f"🏅 {idx}. {score} pts | {username}\n"

            bot.send_message(chat_id, leaderboard_text, parse_mode="HTML")

        except Exception as e:
            bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")
