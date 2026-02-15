import os
import pypdfium2 as pdfium
from paddleocr import PaddleOCR
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"
MAX_PAGES = 30

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    show_log=False
)

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📄 Processing PDF... ⏳")

    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    pdf = pdfium.PdfDocument(pdf_path)

    if len(pdf) > MAX_PAGES:
        await msg.edit_text("❌ Max 30 pages allowed.")
        os.remove(pdf_path)
        return

    full_text = ""

    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=2)  # 2 = ~200 DPI
        pil_image = bitmap.to_pil()

        img_path = f"page_{i}.png"
        pil_image.save(img_path)

        result = ocr.ocr(img_path)

        page_text = ""
        if result and result[0]:
            for line in result[0]:
                page_text += line[1][0] + "\n"

        full_text += f"\n\n===== Page {i+1} =====\n\n"
        full_text += page_text

        os.remove(img_path)

    txt_path = "output.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    await update.message.reply_document(document=open(txt_path, "rb"))

    await msg.delete()
    os.remove(pdf_path)
    os.remove(txt_path)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    print("🚀 OCR Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
