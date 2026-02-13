import os
import requests
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"
CHAT_ID = -1001911273978   

executor = ThreadPoolExecutor(max_workers=3)

# ================= FAST PDF =================
def download_pdf(title, link):
    filename = title.replace(" ", "_") + ".pdf"

    response = requests.get(link, stream=True)
    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)

    return filename

# ================= FAST M3U8 =================
def download_m3u8(title, link):
    filename = title.replace(" ", "_") + ".mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-threads", "8",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-protocol_whitelist", "file,http,https,tcp,tls",
        "-i", link,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        filename
    ]

    subprocess.run(cmd)

    if os.path.exists(filename):
        return filename
    return None

# ================= MAIN HANDLER =================
async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    file = await update.message.document.get_file()
    await file.download_to_drive("links.txt")

    await update.message.reply_text("⚡ Fast Processing Started...")

    with open("links.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    loop = asyncio.get_event_loop()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ":" in line and line.count("http") == 1:
            title, link = line.split(":", 1)
            title = title.strip()
            link = link.strip()
        else:
            title = "File"
            link = line

        try:
            if ".pdf" in link:

                filename = await loop.run_in_executor(
                    executor, download_pdf, title, link
                )

                with open(filename, "rb") as pdf:
                    await context.bot.send_document(
                        chat_id=CHAT_ID,
                        document=pdf,
                        caption=f"📘 {title}"
                    )

                os.remove(filename)

            elif ".m3u8" in link:

                filename = await loop.run_in_executor(
                    executor, download_m3u8, title, link
                )

                if filename:
                    with open(filename, "rb") as video:
                        await context.bot.send_video(
                            chat_id=CHAT_ID,
                            video=video,
                            caption=f"🎬 {title}"
                        )

                    os.remove(filename)

        except Exception as e:
            await update.message.reply_text(f"Error:\n{title}\n{e}")

    await update.message.reply_text("✅ All files processed!")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_txt))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
