import os
import csv
import asyncio
from PyPDF2 import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import g4f

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

# -------- PDF Handler -------- #

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("📄 PDF mil gaya...\n⏳ AI se MCQ bana raha hoon...")

    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    # Extract Text
    reader = PdfReader(pdf_path)
    extracted_text = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"

    # -------- AI Prompt -------- #

    prompt = f"""
    Neeche diye gaye text se MCQ banao.

    Format strictly CSV jaisa hona chahiye:

    "Question","Option A","Option B","Option C","Option D","Answer","Description"

    Rules:
    - Answer sirf A/B/C/D me ho
    - Description 240 characters ke andar ho
    - Har question alag line me ho
    - Sirf CSV output do, extra text nahi

    Text:
    {extracted_text[:6000]}
    """

    try:
        response = await asyncio.to_thread(
            g4f.ChatCompletion.create,
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        csv_content = response.strip()

        csv_path = "output.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)

        await update.message.reply_document(document=open(csv_path, "rb"))

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists("output.csv"):
            os.remove("output.csv")


# -------- Run Bot -------- #

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

print("🚀 Bot Running...")
app.run_polling()
