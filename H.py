import os
import requests
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7105638751:AAEU3vLn1FJcj3QerELdiia9Ald2AqUSDec"
CHAT_ID = -1001911273978   # 🔴 apna channel/group id

# ===============================
# TXT File Receive Handler
# ===============================
async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    file = await update.message.document.get_file()
    await file.download_to_drive("links.txt")

    await update.message.reply_text("Processing started...")

    with open("links.txt", "r") as f:
        links = f.readlines()

    for link in links:
        link = link.strip()
        if not link:
            continue

        try:
            # ================= PDF =================
            if link.endswith(".pdf"):

                await update.message.reply_text(f"Downloading PDF...")

                response = requests.get(link)
                filename = link.split("/")[-1].split("?")[0]

                with open(filename, "wb") as pdf:
                    pdf.write(response.content)

                with open(filename, "rb") as pdf:
                    await context.bot.send_document(
                        chat_id=CHAT_ID,
                        document=pdf,
                        caption=f"📘 {filename}"
                    )

                os.remove(filename)

            # ================= M3U8 =================
            elif link.endswith(".m3u8"):

                await update.message.reply_text("Downloading M3U8 video...")

                filename = link.split("/")[-1].split(".")[0] + ".mp4"

                cmd = [
                    "ffmpeg",
                    "-protocol_whitelist", "file,http,https,tcp,tls",
                    "-i", link,
                    "-c", "copy",
                    filename
                ]

                subprocess.run(cmd)

                with open(filename, "rb") as video:
                    await context.bot.send_video(
                        chat_id=CHAT_ID,
                        video=video,
                        caption=f"🎬 {filename}"
                    )

                os.remove(filename)

        except Exception as e:
            await update.message.reply_text(f"Error with link:\n{link}\n{e}")

    await update.message.reply_text("All files processed ✅")


# ===============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_txt))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
