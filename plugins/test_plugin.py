from main import bot  # Bot instance import karna zaroori hai

print("✅ test_plugin.py loaded!") 

@bot.message_handler(commands=['test'])
def test_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "✅ Test plugin is working perfectly!")
