import os
import requests
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"
CHAT_ID = -1001911273978   

async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    file = await update.message.document.get_file()
    await file.download_to_drive("links.txt")

    await update.message.reply_text("Processing started...")

    with open("links.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            # Title + URL split
            if ":" in line and line.count("http") == 1:
                title, link = line.split(":", 1)
                title = title.strip()
                link = link.strip()
            else:
                title = "File"
                link = line

            # ================= PDF =================
            if ".pdf" in link:

                filename = title.replace(" ", "_") + ".pdf"

                response = requests.get(link)
                with open(filename, "wb") as f:
                    f.write(response.content)

                with open(filename, "rb") as pdf:
                    await context.bot.send_document(
                        chat_id=CHAT_ID,
                        document=pdf,
                        caption=f"📘 {title}"
                    )

                os.remove(filename)

            # ================= M3U8 =================
            elif ".m3u8" in link:

                filename = title.replace(" ", "_") + ".mp4"

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-protocol_whitelist", "file,http,https,tcp,tls",
                    "-i", link,
                    "-c", "copy",
                    filename
                ]

                process = subprocess.run(cmd)

                if os.path.exists(filename):
                    with open(filename, "rb") as video:
                        await context.bot.send_video(
                            chat_id=CHAT_ID,
                            video=video,
                            caption=f"🎬 {title}"
                        )

                    os.remove(filename)
                else:
                    await update.message.reply_text(f"FFmpeg failed:\n{title}")

        except Exception as e:
            await update.message.reply_text(f"Error:\n{line}\n{e}")

    await update.message.reply_text("All files processed ✅")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_txt))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
