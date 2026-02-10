import asyncio
import pandas as pd
from bson import ObjectId

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
async def send_mcqs(schedule_id, bot, schedules):
    s = schedules.find_one({"_id": ObjectId(schedule_id)})
    if not s or s["status"] != "active":
        return

    df = pd.read_csv(s["csv_path"])
    sent = int(s.get("sent_mcq", 0))
    limit = int(s.get("daily_limit", 1))

    if sent >= len(df):
        return

    batch = df.iloc[sent: sent + limit]

    await bot.send_message(s["channel_id"], s["pre_message"])

    for _, row in batch.iterrows():
        options = [
            row["Option A"],
            row["Option B"],
            row["Option C"],
            row["Option D"]
        ]
        correct = ["A","B","C","D"].index(row["Answer"])

        await bot.send_poll(
            chat_id=s["channel_id"],
            question=row["Question"][:300],
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=True
        )
        await asyncio.sleep(1)

    schedules.update_one(
        {"_id": s["_id"]},
        {"$inc": {"sent_mcq": len(batch)}}
    )
