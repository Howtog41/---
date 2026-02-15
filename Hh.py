import os
import fitz
from paddleocr import PaddleOCR
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# =========================
# CONFIG
# =========================
BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"
MAX_PAGES = 30

# Disable model source check (speed improvement)
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Initialize OCR (Global for speed)
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',  # change to 'hi' for Hindi
    show_log=False
)

# =========================
# PDF Handler
# =========================
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📄 Processing PDF... ⏳")

    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    doc = fitz.open(pdf_path)

    if len(doc) > MAX_PAGES:
        await msg.edit_text("❌ Max 30 pages allowed.")
        os.remove(pdf_path)
        return

    full_text = ""

    for page_no, page in enumerate(doc):
        pix = page.get_pixmap(dpi=220)  # 200-250 best for speed
        img_path = f"page_{page_no}.png"
        pix.save(img_path)

        result = ocr.ocr(img_path)

        page_text = ""
        if result and result[0]:
            for line in result[0]:
                page_text += line[1][0] + "\n"

        full_text += f"\n\n===== Page {page_no + 1} =====\n\n"
        full_text += page_text

        os.remove(img_path)

    txt_path = "output.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    await update.message.reply_document(document=open(txt_path, "rb"))

    await msg.delete()

    os.remove(pdf_path)
    os.remove(txt_path)


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    print("🚀 OCR Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
