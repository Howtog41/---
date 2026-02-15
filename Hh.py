import os
import pytesseract
from pdf2image import convert_from_path
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# 🔐 Yaha apna Bot Token dalo
BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

DOWNLOAD_DIR = "downloads"
OUTPUT_DIR = "outputs"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello!\n\n"
        "📄 Mujhe koi bhi PDF bhejo.\n"
        "Main use OCR karke TXT file bana dunga.\n\n"
        "✅ Hindi + English Supported"
    )


async def pdf_to_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        return

    doc = update.message.document

    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ Sirf PDF file bheje.")
        return

    await update.message.reply_text("📥 PDF receive ho gaya...\n⏳ OCR process start ho raha hai...")

    file = await doc.get_file()
    pdf_path = os.path.join(DOWNLOAD_DIR, doc.file_name)
    await file.download_to_drive(pdf_path)

    try:
        images = convert_from_path(pdf_path, dpi=300)
        full_text = ""

        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang='eng+hin')
            full_text += f"\n\n--- Page {i+1} ---\n\n{text}"

        output_txt_path = os.path.join(
            OUTPUT_DIR, doc.file_name.replace(".pdf", ".txt")
        )

        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        await update.message.reply_document(
            document=open(output_txt_path, "rb")
        )

        await update.message.reply_text("✅ OCR Complete!")

    except Exception as e:
        await update.message.reply_text(f"⚠ Error: {str(e)}")

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.PDF, pdf_to_txt))
    app.add_handler(MessageHandler(filters.COMMAND, start))

    print("🤖 Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
