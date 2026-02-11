import asyncio
import pandas as pd
from bson import ObjectId
from plugins.auth import is_user_allowed
from plugins.set_description import get_description_for_chat_id, DEFAULT_DESCRIPTION

REQUIRED_COLUMNS = [
    "Question","Option A","Option B",
    "Option C","Option D","Answer","Description"
]

# ================= CSV VALIDATION =================
def validate_csv(path):
    try:
        df = pd.read_csv(path)
    except:
        return False, "❌ CSV read nahi ho rahi"

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            return False, f"❌ Missing column: {col}"

    if df.empty:
        return False, "❌ CSV empty hai"

    if not df["Answer"].isin(["A","B","C","D"]).all():
        return False, "❌ Answer sirf A/B/C/D hona chahiye"

    return True, df


# ================= SEND MCQS =================


async def send_mcqs(schedule_id, bot, schedules, users):
    s = schedules.find_one({"_id": ObjectId(schedule_id)})
    if not s or s["status"] != "active":
        return

    # 🔐 AUTH CHECK
    user = users.find_one({"user_id": s["user_id"]})
    if not is_user_allowed(user):
        await bot.send_message(
            chat_id=s["channel_id"],
            text=(
                "⛔ Your Plan Has Expired\n\n"
                "MCQ service is stopped.\n"
                "Please purchase a plan.\n\n"
                "📞 Contact Admin: @lkd_ak"
            )
        )
        return

    # ================= MCQ CONFIG =================
    ANSWER_MAP = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    MAX_Q_LEN = 300
    MAX_OPT_LEN = 100
    MAX_DESC_LEN = 200

    # 🏷️ MongoDB se Channel Description
    global_desc = get_description_for_chat_id(users, s["channel_id"])
    if not global_desc:
        global_desc = DEFAULT_DESCRIPTION

    # ================= CSV LOAD ===================
    df = pd.read_csv(s["csv_path"])
    sent = int(s.get("sent_mcq", 0))
    limit = int(s.get("daily_limit", 1))

    if sent >= len(df):
        return

    batch = df.iloc[sent: sent + limit]

    # 🔔 PRE MESSAGE
    if s.get("pre_message"):
        await bot.send_message(s["channel_id"], s["pre_message"])

    # ================= MCQ FLOW ===================
    for _, row in batch.iterrows():
        try:
            question = str(row.get("Question", "")).strip()

            options = [
                str(row.get("Option A", "")).strip(),
                str(row.get("Option B", "")).strip(),
                str(row.get("Option C", "")).strip(),
                str(row.get("Option D", "")).strip(),
            ]

            answer = str(row.get("Answer", "")).strip().upper()

            raw_description = str(row.get("Description", "")).strip()
            description = "" if raw_description.lower() == "nan" else raw_description

            correct_option_id = ANSWER_MAP.get(answer)

            # ❌ Validation
            if (
                not question
                or correct_option_id is None
                or any(not opt or opt.lower() == "nan" for opt in options)
                or len(set(options)) != 4
            ):
                print("Skipped invalid MCQ")
                continue

            # 🧠 DESCRIPTION + CHANNEL TAG MERGE
            if global_desc not in description:
                description = f"{description} {global_desc}".strip() if description else global_desc

            # Trim description safely
            if len(description) > MAX_DESC_LEN:
                description = description[:MAX_DESC_LEN].rsplit(" ", 1)[0] + "..."

            # ================= SEND MODE =================
            if (
                len(question) <= MAX_Q_LEN and
                all(len(opt) <= MAX_OPT_LEN for opt in options)
            ):
                await bot.send_poll(
                    chat_id=s["channel_id"],
                    question=question[:MAX_Q_LEN],
                    options=options,
                    type="quiz",
                    correct_option_id=correct_option_id,
                    explanation=description,
                    is_anonymous=True
                )
            else:
                await bot.send_message(
                    chat_id=s["channel_id"],
                    text=(
                        f"🆀🆄🅴🆂🆃🅸🅾🅽: {question}\n\n"
                        f"🅰 {options[0]}\n"
                        f"🅱 {options[1]}\n"
                        f"🅲 {options[2]}\n"
                        f"🅳 {options[3]}"
                    )
                )

                await bot.send_poll(
                    chat_id=s["channel_id"],
                    question="👆 Upr diye gaye question ka sahi answer kya hoga?",
                    options=["A", "B", "C", "D"],
                    type="quiz",
                    correct_option_id=correct_option_id,
                    explanation=description,
                    is_anonymous=True
                )

            await asyncio.sleep(1.2)

        except Exception as e:
            print("MCQ ERROR:", e)
            continue

    # ================= UPDATE COUNT =================
    schedules.update_one(
        {"_id": s["_id"]},
        {"$inc": {"sent_mcq": len(batch)}}
    )
