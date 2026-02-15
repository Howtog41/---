import os
import fitz
import easyocr
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

# Hindi + English OCR
reader = easyocr.Reader(['hi', 'en'])

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text("📄 Processing PDF with OCR... Please wait ⏳")

    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    doc = fitz.open(pdf_path)
    full_text = ""

    for page_number, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        img_path = f"page_{page_number}.png"
        pix.save(img_path)

        result = reader.readtext(img_path, detail=0)
        page_text = "\n".join(result)
        full_text += f"\n\n===== Page {page_number + 1} =====\n\n"
        full_text += page_text

        os.remove(img_path)

    txt_path = "output.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    await update.message.reply_document(document=open(txt_path, "rb"))

    await message.delete()

    os.remove(pdf_path)
    os.remove(txt_path)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

print("🤖 OCR Bot Running...")
app.run_polling()
