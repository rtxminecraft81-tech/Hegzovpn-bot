import os
import telebot
from telebot import types
import json
import time
import re
import hashlib
from datetime import datetime
from flask import Flask, request
from supabase import create_client, Client

app = Flask(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'

bot = telebot.TeleBot(TOKEN)

# ======================== Route های Flask ========================
@app.route('/')
def home():
    return "Hegzo VPN Bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return "OK", 200

# ======================== دستور start ========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ ربات روشن شد!")

# ======================== اجرای اصلی ========================

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    bot.remove_webhook()
    time.sleep(1)
    WEBHOOK_URL = f"https://{os.environ.get('RAILWAY_STATIC_URL', 'localhost')}/webhook"
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=PORT)
