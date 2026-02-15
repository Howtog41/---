import os
import easyocr
import pypdfium2 as pdfium
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"

# Initialize OCR (English only)
reader = easyocr.Reader(['en'])  
# Hindi + English ke liye:
# reader = easyocr.Reader(['en','hi'])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 Send me a PDF file.\nI will convert it to OCR TXT."
    )

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    await update.message.reply_text("⏳ Processing OCR...")

    # Convert PDF to images (No poppler needed)
    pdf = pdfium.PdfDocument(pdf_path)
    page_indices = list(range(len(pdf)))
    renderer = pdf.render_to(
        pdfium.BitmapConv.pil_image,
        page_indices=page_indices,
        scale=2
    )

    full_text = ""

    for i, image in zip(page_indices, renderer):
        img_path = f"page_{i}.png"
        image.save(img_path)

        result = reader.readtext(img_path, detail=0)
        full_text += "\n".join(result) + "\n\n"

        os.remove(img_path)

    txt_path = "output.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    await update.message.reply_document(open(txt_path, "rb"))

    os.remove(pdf_path)
    os.remove(txt_path)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
