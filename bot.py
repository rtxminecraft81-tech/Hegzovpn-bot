import os
import telebot
from flask import Flask, request
import time

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ======================== دستور start ========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ ربات روشن شد!")

# ======================== Webhook ========================
@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/')
def home():
    return "Bot is running!", 200

# ======================== اجرا ========================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    
    # حذف webhook قبلی
    bot.remove_webhook()
    time.sleep(1)
    
    # تنظیم webhook جدید
    WEBHOOK_URL = f"https://{os.environ.get('RAILWAY_STATIC_URL', 'localhost')}/webhook"
    bot.set_webhook(url=WEBHOOK_URL)
    
    # اجرای Flask
    app.run(host='0.0.0.0', port=PORT)
