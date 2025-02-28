from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import csv
import io
import math

def register_handlers(bot, quiz_collection, rank_collection):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("leaderboard_"))
    def show_leaderboard(call):
        chat_id = call.message.chat.id
        data_parts = call.data.split("_")
        
        quiz_id = data_parts[1]
        page = int(data_parts[2]) if len(data_parts) > 2 else 1  # Default Page = 1

        quiz = quiz_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
            return

        # Fetch leaderboard directly from Google Sheet
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

        except requests.RequestException as e:
            bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")
            return

        # Pagination Logic
        users_per_page = 20
        total_pages = math.ceil(len(sorted_records) / users_per_page)
        start_idx = (page - 1) * users_per_page
        end_idx = start_idx + users_per_page
        current_records = sorted_records[start_idx:end_idx]

        # Generate Leaderboard Text
        leaderboard_text = f"📊 <b>Leaderboard for {quiz['title']} (Page {page}/{total_pages}):</b>\n"
        leaderboard_text += "🏆 Rank | 🏅 Score | 👤 Username\n"
        leaderboard_text += "--------------------------------\n"

        for idx, (uid, score) in enumerate(current_records, start=start_idx + 1):
            try:
                user_info = bot.get_chat(uid)
                username = f"@{user_info.username}" if user_info.username else user_info.first_name
            except Exception as e:
                print(f"Error fetching user {uid}: {e}")
                username = "Unknown"

            leaderboard_text += f"🏅 {idx}. {score} pts | {username}\n"

        # Create Inline Buttons for Pagination
        keyboard = InlineKeyboardMarkup()
        buttons = []

        if page > 1:
            buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"leaderboard_{quiz_id}_{page - 1}"))
        if page < total_pages:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"leaderboard_{quiz_id}_{page + 1}"))

        if buttons:
            keyboard.row(*buttons)

        bot.send_message(chat_id, leaderboard_text, parse_mode="HTML", reply_markup=keyboard)
