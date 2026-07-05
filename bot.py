import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
from supabase import create_client, Client

app = Flask(__name__)

@app.route('/')
def home():
    return "Hegzo VPN Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن پیدا نشد!")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'
CARD_NUMBER = '5022291525516892'
CARD_NAME = 'احمد خزایی'
MIN_CHARGE = 200000

# ======================== اتصال به Supabase ========================
SUPABASE_URL = "https://fyflqsxodxpwhrfvnmex.supabase.co"
SUPABASE_KEY = "sb_publishable_uKV9HhKzCSuVvR_q7Ei95g_LR8q9Icx"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================== توابع ذخیره‌سازی ========================
def load_users():
    response = supabase.table("users").select("*").execute()
    users = {}
    for row in response.data:
        users[row['user_id']] = {
            'credit': row.get('credit', 0),
            'pending_charge': row.get('pending_charge', 0),
            'active_configs': row.get('active_configs', []),
            'username': row.get('username', '')
        }
    return users

def save_users(users):
    for user_id, data in users.items():
        supabase.table("users").upsert({
            "user_id": user_id,
            "credit": data.get('credit', 0),
            "pending_charge": data.get('pending_charge', 0),
            "active_configs": data.get('active_configs', []),
            "username": data.get('username', '')
        }).execute()

def init_user(user_id, username=""):
    if str(user_id) not in users:
        users[str(user_id)] = {
            'credit': 0,
            'pending_charge': 0,
            'active_configs': [],
            'username': username
        }
        save_users(users)

# ======================== بوت ========================
bot = telebot.TeleBot(TOKEN)
users = load_users()
banned_users = set()

def load_banned_users():
    global banned_users
    if os.path.exists('banned_users.json'):
        with open('banned_users.json', 'r') as f:
            banned_users = set(json.load(f))

def save_banned_users():
    with open('banned_users.json', 'w') as f:
        json.dump(list(banned_users), f)

def is_banned(user_id):
    return str(user_id) in banned_users

load_banned_users()

def is_member(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ======================== دکوراتور بررسی عضویت ========================
def membership_required(func):
    def wrapper(message):
        user_id = message.from_user.id
        if is_banned(user_id):
            bot.reply_to(message, "⛔ شما مسدود شده اید!")
            return
        if not is_member(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"),
                types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")
            )
            bot.reply_to(message, 
                f"❌ کاربر عزیز!\n\nبرای استفاده از ربات، ابتدا در کانال عضو شوید:\n🔗 @hegzo_vpn_channle\n\nسپس روی دکمه‌ی ✅ تایید عضویت کلیک کنید.",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            return
        return func(message)
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership_callback(call):
    user_id = call.from_user.id
    if is_member(user_id):
        bot.edit_message_text(
            "✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.send_message(user_id, "🔥 منوی اصلی:", reply_markup=main_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو کانال نشده‌اید!", show_alert=True)

# ======================== کیبورد اصلی ========================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 شارژ کیف پول", "🛒 خرید کانفیگ")
    markup.add("📁 کانفیگ‌های من", "👤 حساب کاربری")
    markup.add("👥 دعوت از دوستان", "🆘 پشتیبانی")
    markup.add("🏠 منوی اصلی")
    return markup

# ======================== دستورات ========================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما مسدود شده اید!")
        return
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"),
            types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")
        )
        bot.reply_to(message, 
            f"❌ کاربر عزیز!\n\nبرای استفاده از ربات، ابتدا در کانال عضو شوید:\n🔗 @hegzo_vpn_channle\n\nسپس روی دکمه‌ی ✅ تایید عضویت کلیک کنید.",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        return
    
    name = message.from_user.first_name
    init_user(user_id, message.from_user.username or "")
    
    bot.reply_to(message, 
        f"""🔥 **به هگزو وی‌پی‌ان خوش اومدی** {name}! 🎉

⚡ اینترنت آزاد و بدون محدودیت
🛡️ امنیت کامل و سرعت بالا

✨ از منوی زیر یکی رو انتخاب کن:
""", 
        reply_markup=main_keyboard(), 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "🏠 منوی اصلی")
@membership_required
def back_home(m):
    bot.reply_to(m, "🔥 منوی اصلی:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "👤 حساب کاربری")
@membership_required
def profile(m):
    user_id = str(m.from_user.id)
    data = users.get(user_id, {})
    text = f"""👤 **حساب کاربری هگزو وی‌پی‌ان**

━━━━━━━━━━━━━━━━━━━━━
🆔 شناسه: `{user_id}`
👤 نام: {m.from_user.first_name}
💰 اعتبار: {data.get('credit', 0):,} تومان
📁 کانفیگ فعال: {len(data.get('active_configs', []))}
━━━━━━━━━━━━━━━━━━━━━"""
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
@membership_required
def support(m):
    bot.reply_to(m, "🆔 **پشتیبانی هگزو وی‌پی‌ان**\n\n@hegzosupport\n\n۲۴ ساعته پاسخگوی شما هستیم.", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "👥 دعوت از دوستان")
@membership_required
def invite(m):
    user_id = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.reply_to(m, f"🔥 **لینک دعوت شما**\n\n`{link}`\n\nهر کاربری با این لینک وارد بشه، برای شما ثبت میشه.", parse_mode='Markdown')

# ======================== خرید کانفیگ ========================
@bot.message_handler(func=lambda m: m.text == "🛒 خرید کانفیگ")
@membership_required
def buy_menu(m):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("25 گیگ - 190,000 تومان", callback_data="buy_25"))
    markup.add(types.InlineKeyboardButton("50 گیگ - 290,000 تومان", callback_data="buy_50"))
    markup.add(types.InlineKeyboardButton("100 گیگ - 490,000 تومان", callback_data="buy_100"))
    markup.add(types.InlineKeyboardButton("200 گیگ - 790,000 تومان", callback_data="buy_200"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    bot.reply_to(m, "📦 انتخاب بسته:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_config(call):
    user_id = str(call.from_user.id)
    if user_id not in users:
        init_user(user_id)
    
    price = int(call.data.split("_")[1]) * 1000
    if call.data == "buy_25":
        price = 190000
        package = "25 گیگ"
    elif call.data == "buy_50":
        price = 290000
        package = "50 گیگ"
    elif call.data == "buy_100":
        price = 490000
        package = "100 گیگ"
    elif call.data == "buy_200":
        price = 790000
        package = "200 گیگ"
    
    credit = users[user_id].get('credit', 0)
    if credit >= price:
        users[user_id]['credit'] = credit - price
        save_users(users)
        
        admin_text = f"📸 درخواست کانفیگ\n👤 @{call.from_user.username or 'بدون نام'}\n🆔 {user_id}\n📦 {package}\n💰 {price:,} تومان"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{user_id}_{package}_{price}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"no_{user_id}")
        )
        bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
        bot.send_message(int(user_id), f"✅ درخواست خرید {package} ثبت شد. منتظر تایید ادمین باشید.")
        bot.answer_callback_query(call.id, "✅ ثبت شد")
    else:
        need = price - credit
        bot.send_message(int(user_id), f"❌ اعتبار کافی نیست!\n💰 اعتبار: {credit:,} تومان\n💸 نیاز: {need:,} تومان\n\n💳 از منوی اصلی روی شارژ کیف پول کلیک کن.")
        bot.answer_callback_query(call.id, "❌ اعتبار")

# ======================== دکمه‌های ادمین برای کانفیگ ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def confirm_config(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    _, user_id, package, price = call.data.split("_")
    bot.send_message(int(user_id), f"✅ کانفیگ {package} تایید شد!\n🆔 پشتیبانی: @hegzosupport")
    bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def reject_config(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    user_id = call.data.split("_")[1]
    bot.send_message(int(user_id), "❌ درخواست شما رد شد! با پشتیبانی تماس بگیرید: @hegzosupport")
    bot.answer_callback_query(call.id, "❌ رد شد")

# ======================== کانفیگ‌های من ========================
@bot.message_handler(func=lambda m: m.text == "📁 کانفیگ‌های من")
@membership_required
def my_configs(m):
    user_id = str(m.from_user.id)
    data = users.get(user_id, {})
    configs = data.get('active_configs', [])
    if not configs:
        bot.reply_to(m, "📭 شما هیچ کانفیگ فعالی ندارید!")
        return
    text = "📁 **کانفیگ‌های فعال شما:**\n\n"
    for i, cfg in enumerate(configs, 1):
        text += f"{i}. {cfg.get('package', 'نامشخص')} - {cfg.get('date', '')}\n"
    bot.reply_to(m, text, parse_mode='Markdown')

# ======================== شارژ کیف پول ========================
@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
@membership_required
def charge_menu(m):
    user_id = str(m.from_user.id)
    if user_id not in users:
        init_user(user_id)
    
    text = f"""💳 **شارژ کیف پول**

🏦 شماره کارت: `{CARD_NUMBER}`
👤 به نام: {CARD_NAME}

💰 حداقل شارژ: {MIN_CHARGE:,} تومان

📌 لطفاً مبلغ مورد نظر را به تومان وارد کنید:"""
    
    bot.reply_to(m, text, parse_mode='Markdown')
    bot.register_next_step_handler(m, get_amount)

def get_amount(m):
    user_id = str(m.from_user.id)
    try:
        amount = int(m.text.replace(',', '').replace(' ', ''))
        if amount < MIN_CHARGE:
            bot.reply_to(m, f"❌ حداقل شارژ {MIN_CHARGE:,} تومان است. لطفاً مجدداً مبلغ را وارد کنید:")
            bot.register_next_step_handler(m, get_amount)
            return
        users[user_id]['pending_charge'] = amount
        save_users(users)
        bot.reply_to(m, f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n📸 لطفاً عکس رسید را بفرستید:")
    except:
        bot.reply_to(m, "❌ لطفاً یک عدد معتبر وارد کنید:")
        bot.register_next_step_handler(m, get_amount)

@bot.message_handler(content_types=['photo'])
@membership_required
def receipt(m):
    user_id = str(m.from_user.id)
    pending = users.get(user_id, {}).get('pending_charge', 0)
    if pending == 0:
        bot.reply_to(m, "❌ شما هیچ درخواست شارژ فعالی ندارید. لطفاً ابتدا از منو مبلغ را وارد کنید.", reply_markup=main_keyboard())
        return
    
    caption = f"💰 درخواست شارژ\n👤 @{m.from_user.username or 'بدون نام'}\n🆔 {user_id}\n💸 مبلغ: {pending:,} تومان"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید شارژ", callback_data=f"accept_{user_id}_{pending}"),
        types.InlineKeyboardButton("❌ رد شارژ", callback_data=f"reject_{user_id}")
    )
    
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=caption, reply_markup=markup)
    bot.reply_to(m, "✅ رسید شما دریافت شد. در حال بررسی توسط ادمین...")
    
    users[user_id]['pending_charge'] = 0
    save_users(users)

@bot.message_handler(func=lambda m: True)
@membership_required
def unknown(m):
    bot.reply_to(m, "❌ لطفاً از دکمه‌های منوی اصلی استفاده کنید.", reply_markup=main_keyboard())

# ======================== دکمه‌های ادمین برای شارژ ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
def accept_charge(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    _, user_id, amount = call.data.split("_")
    amount = int(amount)
    
    if user_id not in users:
        users[user_id] = {'credit': 0, 'pending_charge': 0, 'active_configs': []}
    
    users[user_id]['credit'] = users[user_id].get('credit', 0) + amount
    save_users(users)
    
    bot.send_message(int(user_id), f"✅ شارژ {amount:,} تومانی شما تایید شد!\n💰 اعتبار جدید: {users[user_id]['credit']:,} تومان")
    bot.answer_callback_query(call.id, "✅ تایید شد")
    try:
        bot.edit_message_caption("✅ تایید شد", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject_charge(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    user_id = call.data.split("_")[1]
    
    bot.send_message(int(user_id), "❌ درخواست شارژ شما رد شد. لطفاً با پشتیبانی تماس بگیرید: @hegzosupport")
    bot.answer_callback_query(call.id, "❌ رد شد")
    try:
        bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)
    except:
        pass

# ======================== دستورات ادمین ========================
@bot.message_handler(commands=['users'])
def list_users(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not users:
        bot.reply_to(m, "📭 هیچ کاربری وجود ندارد.")
        return
    text = "📊 **لیست کاربران هگزو وی‌پی‌ان**\n\n"
    for uid, data in users.items():
        username = data.get('username', 'بدون نام')
        text += f"🆔 `{uid}` | @{username} | اعتبار: {data.get('credit',0):,}\n"
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(commands=['ban'])
def ban_user(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if str(user_id) == ADMIN_ID:
            bot.reply_to(m, "❌ نمی‌توانید ادمین را بن کنید!")
            return
        banned_users.add(str(user_id))
        save_banned_users()
        bot.send_message(user_id, "⛔ شما مسدود شدید!")
        bot.reply_to(m, f"✅ کاربر {user_id} مسدود شد.")
    except:
        bot.reply_to(m, "❌ دستور: /ban [user_id]")

@bot.message_handler(commands=['unban'])
def unban_user(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if str(user_id) in banned_users:
            banned_users.discard(str(user_id))
            save_banned_users()
            bot.reply_to(m, f"✅ کاربر {user_id} از حالت مسدودیت خارج شد.")
        else:
            bot.reply_to(m, f"❌ کاربر {user_id} در لیست مسدود شده‌ها نیست.")
    except:
        bot.reply_to(m, "❌ دستور: /unban [user_id]")

# ======================== اجرا ========================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 Hegzo VPN روی پورت {PORT} روشن شد!")
    print("✅ سیستم شارژ با حداقل ۲۰۰,۰۰۰ تومان فعال شد!")
    print("✅ ارسال رسید به ادمین فعال شد!")
    print("✅ دکمه‌های ادمین برای تایید/رد شارژ و کانفیگ فعال شد!")

    bot.delete_webhook()
    time.sleep(2)

    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()

    bot.infinity_polling()
