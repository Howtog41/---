import os
from PyPDF2 import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "input.pdf"
    await file.download_to_drive(file_path)

    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() + "\n"

    txt_path = "output.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    await update.message.reply_document(document=open(txt_path, "rb"))

    os.remove(file_path)
    os.remove(txt_path)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

print("Bot Running...")
app.run_polling()
