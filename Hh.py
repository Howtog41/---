import os
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from paddleocr import PaddleOCR
import pypdfium2 as pdfium
from PIL import Image

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

# Initialize OCR (Hindi + English)
ocr = PaddleOCR(use_angle_cls=True, lang='en')  # Change to 'hi' for Hindi

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 Send me a PDF file.\n"
        "I will convert it to TXT using OCR.\n"
        "Supports multiple languages."
    )

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ Please send a valid PDF file.")
        return

    await update.message.reply_text("⏳ Processing PDF... Please wait.")

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = os.path.join(temp_dir, "input.pdf")
        txt_path = os.path.join(temp_dir, "output.txt")

        file = await document.get_file()
        await file.download_to_drive(pdf_path)

        # Convert PDF to images
        pdf = pdfium.PdfDocument(pdf_path)
        text_output = ""

        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=2).to_pil()
            image_path = os.path.join(temp_dir, f"page_{i}.jpg")
            bitmap.save(image_path)

            # OCR on image
            result = ocr.ocr(image_path)
            for line in result[0]:
                text_output += line[1][0] + "\n"

        # Save text file
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_output)

        await update.message.reply_document(document=open(txt_path, "rb"))

    await update.message.reply_text("✅ Conversion Complete!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    app.run_polling()

if __name__ == "__main__":
    main()
