import asyncio
import pandas as pd
from bson import ObjectId
from plugins.auth import is_user_allowed

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

    # 🏷️ Optional tag / description
    global_desc = s.get("tag", "").strip()

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
            # 🧹 SAFE READ
            question = str(row.get("Question", "")).strip()
            options = [
                str(row.get("Option A", "")).strip(),
                str(row.get("Option B", "")).strip(),
                str(row.get("Option C", "")).strip(),
                str(row.get("Option D", "")).strip(),
            ]
            answer = str(row.get("Answer", "")).strip().upper()
            description = str(row.get("Description", "")).strip()

            correct_option_id = ANSWER_MAP.get(answer)

            # ❌ MISSING DATA CHECK
            missing = []
            if not question:
                missing.append("Question")
            for i, opt in enumerate(options):
                if not opt or opt.lower() == "nan":
                    missing.append(f"Option {chr(65+i)}")
            if correct_option_id is None:
                missing.append("Answer")

            if missing:
                print("Skipped MCQ (missing):", missing)
                continue

            # ❌ DUPLICATE OPTIONS
            if len(set(options)) != 4:
                print("Skipped MCQ (duplicate options)")
                continue

            # 🧠 DESCRIPTION + TAG MERGE
            if global_desc and global_desc not in description:
                description = f"{description} {global_desc}" if description else global_desc

            if len(description) > MAX_DESC_LEN:
                description = description[:MAX_DESC_LEN].rsplit(" ", 1)[0] + "..."

            # ================= SEND MODE =================
            if (
                len(question) <= MAX_Q_LEN and
                all(len(opt) <= MAX_OPT_LEN for opt in options)
            ):
                # ✅ NORMAL QUIZ
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
                # 🔁 FALLBACK MODE (LONG TEXT)
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
