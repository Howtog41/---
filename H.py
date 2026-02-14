import nest_asyncio
nest_asyncio.apply()

import os
import fitz
import easyocr
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

# Initialize OCR once
reader = easyocr.Reader(['en', 'hi'], gpu=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Send PDF file for OCR extraction.")


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⬇ Downloading PDF...")

    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    await update.message.reply_text("⏳ Processing PDF... Please wait.")

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    final_text = ""

    for page_num in range(total_pages):
        page = doc.load_page(page_num)

        # High resolution image for better OCR
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")

        result = reader.readtext(img_bytes)

        final_text += f"\n\n========== Page {page_num+1} ==========\n\n"

        for r in result:
            final_text += r[1] + "\n"

        # Progress message every page
        await update.message.reply_text(f"✅ Page {page_num+1}/{total_pages} done")

    output_file = "output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)

    await update.message.reply_document(document=open(output_file, "rb"))

    os.remove(pdf_path)
    os.remove(output_file)

    await update.message.reply_text("🎉 OCR Completed Successfully!")


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    print("🤖 Bot Running... Send PDF in Telegram.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()


asyncio.get_event_loop().run_until_complete(main())
