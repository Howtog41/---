from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from fpdf import FPDF
import os

TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"

async def start(update: Update, context):
    await update.message.reply_text("Welcome! Send me a poll, and I'll convert it to a PDF with all details.")

async def handle_poll(update: Update, context):
    poll = update.message.poll
    question = poll.question
    options = [option.text for option in poll.options]
    votes = [option.voter_count for option in poll.options]
    total_votes = sum(votes)
    is_anonymous = "Yes" if poll.is_anonymous else "No"
    allows_multiple_answers = "Yes" if poll.allows_multiple_answers else "No"
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Telegram Poll Report", ln=True, align='C')
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Question: {question}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Anonymous Poll: {is_anonymous}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Allows Multiple Answers: {allows_multiple_answers}")
    pdf.ln(10)
    pdf.cell(200, 10, txt="Options and Votes:", ln=True, align='L')
    pdf.ln(5)
    
    for idx, (option, vote) in enumerate(zip(options, votes), start=1):
        pdf.multi_cell(0, 10, f"{idx}. {option} - Votes: {vote}")
        pdf.ln(2)
    
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Total Votes: {total_votes}")
    
    filename = f"poll_{poll.id}.pdf"
    pdf.output(filename)
    
    await update.message.reply_document(document=open(filename, "rb"))
    os.remove(filename)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.POLL, handle_poll))

app.run_polling()
