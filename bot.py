import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
import random
import string
import re
import hashlib
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

# ======================== اطلاعات کارت ========================
CARD_NUMBER = os.environ.get('CARD_NUMBER', '6037701210877582')
CARD_NAME = os.environ.get('CARD_NAME', 'خزایی')

MIN_CHARGE = 200000
REFERRAL_AMOUNT = 0
COMMISSION_PERCENT = 10

# ======================== وضعیت‌ها ========================
wallet_enabled = True
discount_enabled = True
discounts = {}

# ======================== بخش کانفیگ تست (با توضیحات) ========================
free_config_data = {
    'config': None,      # لینک کانفیگ یا هر لینک دیگه
    'description': None, # توضیحات
    'date': None,        # تاریخ تنظیم
    'set_by': None       # کسی که تنظیم کرده
}

# ======================== اتصال به Supabase ========================
SUPABASE_URL = "https://fyflqsxodxpwhrfvnmex.supabase.co"
SUPABASE_KEY = "sb_publishable_uKV9HhKzCSuVvR_q7Ei95g_LR8q9Icx"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================== توابع دیتابیس ========================
def load_users():
    try:
        response = supabase.table("users").select("*").execute()
        users = {}
        for row in response.data:
            users[row['user_id']] = {
                'username': row.get('username', ''),
                'credit': row.get('credit', 0),
                'active_configs': row.get('active_configs', []),
                'pending_charge': row.get('pending_charge', 0),
                'invited_by': row.get('invited_by'),
                'referrals': row.get('referrals', 0),
                'joined_at': row.get('joined_at', ''),
                'referral_code': row.get('referral_code', ''),
                'total_commission': row.get('total_commission', 0)
            }
        return users
    except Exception as e:
        print(f"❌ خطا در لود کاربران: {e}")
        return {}

def save_users(users):
    try:
        for user_id, data in users.items():
            supabase.table("users").upsert({
                "user_id": user_id,
                "username": data.get('username', ''),
                "credit": data.get('credit', 0),
                "active_configs": data.get('active_configs', []),
                "pending_charge": data.get('pending_charge', 0),
                "invited_by": data.get('invited_by'),
                "referrals": data.get('referrals', 0),
                "joined_at": data.get('joined_at', ''),
                "referral_code": data.get('referral_code', ''),
                "total_commission": data.get('total_commission', 0)
            }).execute()
    except Exception as e:
        print(f"❌ خطا در سیو کاربران: {e}")

def generate_referral_code(user_id):
    hash_object = hashlib.md5(str(user_id).encode())
    return hash_object.hexdigest()[:6].upper()

def init_user(user_id, username=""):
    if str(user_id) not in users:
        referral_code = generate_referral_code(user_id)
        users[str(user_id)] = {
            'username': username,
            'credit': 0,
            'active_configs': [],
            'pending_charge': 0,
            'invited_by': None,
            'referrals': 0,
            'joined_at': str(datetime.now()),
            'referral_code': referral_code,
            'total_commission': 0
        }
        save_users(users)

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
        try:
            bot.edit_message_text("✅ عضویت شما تأیید شد!", call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(user_id, "🔥 منوی اصلی:", reply_markup=main_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو کانال نشده‌اید!", show_alert=True)

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 شارژ کیف پول", "🛒 خرید کانفیگ")
    markup.add("📁 کانفیگ‌های من", "👤 حساب کاربری")
    markup.add("🎁 کانفیگ تست", "👥 دعوت از دوستان")
    markup.add("🆘 پشتیبانی", "🏠 منوی اصلی")
    return markup

# ======================== منوهای خرید ========================
def buy_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🚀 اقتصادی", callback_data="cat_economic"))
    markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 خانواده", callback_data="cat_family"))
    markup.add(types.InlineKeyboardButton("⚡ پرسرعت", callback_data="cat_speed"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return markup

def economic_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🚀 ۱۰۰ گیگ - یک ماهه ۱۹۹,۰۰۰", callback_data="buy_economic100_199000"))
    markup.add(types.InlineKeyboardButton("🚀 ۱۰۰ گیگ مولتی‌لوکیشن - سرعت موشکی ۲۴۹,۰۰۰", callback_data="buy_economic100_249000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def family_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 ۲ کاربر - نامحدود ۲۳۵,۰۰۰", callback_data="buy_family2_235000"))
    markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 ۴ کاربر - نامحدود ۳۴۶,۰۰۰", callback_data="buy_family4_346000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def speed_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⚡ ۲۰ گیگ - ۱۴۰,۰۰۰", callback_data="buy_speed20_140000"))
    markup.add(types.InlineKeyboardButton("⚡ ۳۰ گیگ - ۲۰۰,۰۰۰", callback_data="buy_speed30_200000"))
    markup.add(types.InlineKeyboardButton("⚡ ۵۰ گیگ - ۳۱۵,۰۰۰", callback_data="buy_speed50_315000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

# ======================== دستورات ادمین (تخفیف) ========================
@bot.message_handler(commands=['discount'])
def add_discount(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        parts = m.text.split()
        code = parts[1].upper()
        value = int(parts[2])
        uses = int(parts[3]) if len(parts) > 3 else 999
        discount_type = 'percent' if value <= 100 else 'amount'
        discounts[code] = {
            'value': value,
            'type': discount_type,
            'uses': uses,
            'used': 0
        }
        bot.reply_to(m, f"✅ کد تخفیف {code} با {value}{'%' if discount_type == 'percent' else ' تومان'} و {uses} بار استفاده ایجاد شد.")
    except:
        bot.reply_to(m, "❌ /discount [کد] [مقدار] [تعداد]\nمثال: /discount OFF15 15 999")

@bot.message_handler(commands=['discounts'])
def list_discounts(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not discounts:
        bot.reply_to(m, "📭 هیچ کد تخفیفی وجود ندارد.")
        return
    text = "📊 لیست تخفیف‌ها:\n"
    for code, data in discounts.items():
        text += f"🔹 {code}: {data['value']}{'%' if data['type'] == 'percent' else ' تومان'} - {data['used']}/{data['uses']}\n"
    bot.reply_to(m, text)

@bot.message_handler(commands=['deldiscount'])
def del_discount(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        code = m.text.split()[1].upper()
        if code in discounts:
            del discounts[code]
            bot.reply_to(m, f"✅ کد تخفیف {code} حذف شد!")
        else:
            bot.reply_to(m, f"❌ کد {code} وجود ندارد!")
    except:
        bot.reply_to(m, "❌ /deldiscount [کد]")

@bot.message_handler(commands=['discountoff'])
def discount_off(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    global discount_enabled
    discount_enabled = False
    bot.reply_to(m, "✅ همه تخفیف‌ها غیرفعال شدند!")

@bot.message_handler(commands=['discounton'])
def discount_on(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    global discount_enabled
    discount_enabled = True
    bot.reply_to(m, "✅ سیستم تخفیف فعال شد!")

# ======================== دستورات ادمین (شارژ) ========================
@bot.message_handler(commands=['walletoff'])
def wallet_off(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    global wallet_enabled
    wallet_enabled = False
    bot.reply_to(m, "✅ شارژ کیف پول غیرفعال شد.")

@bot.message_handler(commands=['walleton'])
def wallet_on(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    global wallet_enabled
    wallet_enabled = True
    bot.reply_to(m, "✅ شارژ کیف پول فعال شد.")

# ======================== دستورات ادمین (کانفیگ تست) ========================
@bot.message_handler(commands=['setfree'])
def set_free_config(m):
    """تنظیم کانفیگ تست با توضیحات - روی پیام ریپلی کن"""
    if str(m.from_user.id) != ADMIN_ID:
        bot.reply_to(m, "⛔ فقط ادمین!")
        return
    
    global free_config_data
    
    if m.reply_to_message:
        full_text = m.reply_to_message.text or m.reply_to_message.caption or ''
        
        if not full_text:
            bot.reply_to(m, "❌ پیام انتخابی متنی نیست!")
            return
        
        lines = full_text.strip().split('\n')
        
        # پیدا کردن لینک (هر لینکی رو قبول کن)
        config_link = None
        description_lines = []
        
        for line in lines:
            line = line.strip()
            # هر لینکی رو قبول کن (http, https, vless, vmess, trojan, ss, و حتی لینک‌های معمولی)
            if any(x in line.lower() for x in ['http://', 'https://', 'vless://', 'vmess://', 'trojan://', 'ss://', '.com', '.net', '.org', 't.me/']):
                config_link = line
            else:
                if line and not line.startswith('#'):
                    description_lines.append(line)
        
        if not config_link:
            bot.reply_to(m, "❌ **لینک پیدا نشد!**\n\n"
                           "لطفاً پیامت باید شامل یک لینک باشه:\n"
                           "مثلاً: `https://example.com` یا `vless://...`")
            return
        
        free_config_data['config'] = config_link
        free_config_data['description'] = '\n'.join(description_lines) if description_lines else 'لینک تست'
        free_config_data['date'] = str(datetime.now())
        free_config_data['set_by'] = m.from_user.username or m.from_user.first_name
        
        bot.reply_to(
            m,
            f"✅ **لینک تست با موفقیت ذخیره شد!**\n\n"
            f"📝 توضیحات: {free_config_data['description'][:100]}...\n"
            f"🔗 لینک: `{config_link[:50]}...`\n"
            f"📅 تاریخ: {free_config_data['date']}",
            parse_mode='Markdown'
        )
        
        try:
            bot.send_message(
                ADMIN_ID,
                f"✅ لینک تست جدید:\n\n"
                f"📝 توضیحات: {free_config_data['description']}\n\n"
                f"🔗 لینک: {config_link}\n\n"
                f"📅 تنظیم شده توسط: @{free_config_data['set_by']}"
            )
        except:
            pass
    else:
        bot.reply_to(
            m,
            "❌ **روی یک پیام حاوی لینک ریپلی کن!**\n\n"
            "📝 **فرمت پیام:**\n"
            "توضیحات لینک تست\n"
            "https://example.com\n\n"
            "🔄 پیام رو فوروارد کن و روی اون `/setfree` رو بفرست."
        )

@bot.message_handler(commands=['showfree'])
def show_free_config(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    
    if free_config_data['config']:
        text = f"""📡 **لینک تست فعلی:**

📝 توضیحات:
{free_config_data['description']}

🔗 لینک:
`{free_config_data['config']}`

📅 تاریخ تنظیم: {free_config_data['date']}
👤 تنظیم شده توسط: @{free_config_data['set_by']}"""
        bot.reply_to(m, text, parse_mode='Markdown')
    else:
        bot.reply_to(m, "❌ هیچ لینک تستی تنظیم نشده!")

@bot.message_handler(commands=['delfree'])
def del_free_config(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    
    global free_config_data
    free_config_data = {
        'config': None,
        'description': None,
        'date': None,
        'set_by': None
    }
    bot.reply_to(m, "✅ لینک تست حذف شد!")

# ======================== دکمه کانفیگ تست ========================
@bot.message_handler(func=lambda m: m.text == "🎁 کانفیگ تست")
@membership_required
def send_free_config(m):
    if free_config_data['config']:
        try:
            date_obj = datetime.strptime(free_config_data['date'], '%Y-%m-%d %H:%M:%S.%f')
            date_str = date_obj.strftime('%Y/%m/%d - %H:%M')
        except:
            date_str = free_config_data['date'] or 'نامشخص'
        
        text = f"""🎁 **لینک تست رایگان**

📝 **توضیحات:**
{free_config_data['description']}

🔗 **لینک:**
{free_config_data['config']}

📅 تاریخ بروزرسانی: {date_str}

⚠️ **توجه:**
• این لینک تستی است و ممکن است هر لحظه تغییر کند.
• برای دریافت کانفیگ پایدار از بخش 🛒 خرید کانفیگ استفاده کن.

🆔 پشتیبانی: @hegzosupport"""
        
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
        
        try:
            bot.send_message(
                ADMIN_ID,
                f"📡 درخواست لینک تست\n"
                f"👤 @{m.from_user.username or 'بدون نام'}\n"
                f"🆔 {m.from_user.id}"
            )
        except:
            pass
    else:
        bot.reply_to(
            m,
            "❌ **هیچ لینک تستی تنظیم نشده!**\n\n"
            "📢 با ادمین تماس بگیرید: @hegzosupport",
            parse_mode='Markdown'
        )

@bot.message_handler(func=lambda m: m.text == "🏠 منوی اصلی")
@membership_required
def back_home(m):
    bot.reply_to(m, "🔥 منوی اصلی:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🛒 خرید کانفیگ")
@membership_required
def show_buy(m):
    bot.reply_to(m, "📊 انتخاب دسته‌بندی:", reply_markup=buy_menu())

@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
@membership_required
def charge_menu(m):
    global wallet_enabled
    if not wallet_enabled:
        bot.reply_to(m, "⛔ این بخش در حال حاضر غیرفعال است.", parse_mode='Markdown')
        return
    
    user_id = str(m.from_user.id)
    if user_id not in users:
        init_user(user_id)
    
    text = f"""💳 شارژ کیف پول
🏦 شماره کارت: {CARD_NUMBER}
👤 به نام: {CARD_NAME}
💰 حداقل شارژ: {MIN_CHARGE:,} تومان
لطفاً مبلغ مورد نظر را انتخاب کنید:"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("۲۰۰,۰۰۰ تومان", callback_data="charge_200000"),
        types.InlineKeyboardButton("۳۰۰,۰۰۰ تومان", callback_data="charge_300000"),
        types.InlineKeyboardButton("۵۰۰,۰۰۰ تومان", callback_data="charge_500000"),
        types.InlineKeyboardButton("۱,۰۰۰,۰۰۰ تومان", callback_data="charge_1000000"),
        types.InlineKeyboardButton("✏️ مبلغ دلخواه", callback_data="charge_custom"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    )
    bot.send_message(m.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("charge_"))
def charge_callback(call):
    user_id = str(call.from_user.id)
    if call.data == "charge_custom":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "💰 لطفاً مبلغ مورد نظر را به تومان وارد کنید:")
        bot.register_next_step_handler(msg, process_custom_charge)
        return
    amount = int(call.data.split("_")[1])
    if amount < MIN_CHARGE:
        bot.answer_callback_query(call.id, f"❌ حداقل شارژ {MIN_CHARGE:,} تومان است!", show_alert=True)
        return
    users[user_id]['pending_charge'] = amount
    save_users(users)
    bot.answer_callback_query(call.id, "✅ ثبت شد")
    bot.send_message(call.message.chat.id, f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n📸 لطفاً عکس رسید را بفرستید:")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def process_custom_charge(m):
    user_id = str(m.from_user.id)
    raw_text = m.text.strip()
    persian_to_english = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
    for p, e in persian_to_english.items():
        raw_text = raw_text.replace(p, e)
    raw_text = re.sub(r'[^0-9]', '', raw_text)
    if not raw_text:
        bot.reply_to(m, "❌ لطفاً یک عدد معتبر وارد کن (مثال: 200000):")
        bot.register_next_step_handler(m, process_custom_charge)
        return
    try:
        amount = int(raw_text)
    except:
        bot.reply_to(m, "❌ عدد معتبر نیست. دوباره تلاش کن:")
        bot.register_next_step_handler(m, process_custom_charge)
        return
    if amount < MIN_CHARGE:
        bot.reply_to(m, f"❌ حداقل شارژ {MIN_CHARGE:,} تومان است. دوباره وارد کن:")
        bot.register_next_step_handler(m, process_custom_charge)
        return
    users[user_id]['pending_charge'] = amount
    save_users(users)
    bot.reply_to(m, f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n📸 لطفاً عکس رسید را بفرستید:")

@bot.message_handler(content_types=['photo'])
@membership_required
def handle_receipt(m):
    user_id = str(m.from_user.id)
    pending = users.get(user_id, {}).get('pending_charge', 0)
    if pending == 0:
        bot.reply_to(m, "❌ شما هیچ درخواست شارژ فعالی ندارید.", reply_markup=main_keyboard())
        return
    caption = f"💰 درخواست شارژ\n👤 @{m.from_user.username or 'بدون نام'}\n🆔 {user_id}\n💸 مبلغ: {pending:,} تومان"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید شارژ", callback_data=f"ch_ok_{user_id}_{pending}"),
        types.InlineKeyboardButton("❌ رد شارژ", callback_data=f"ch_no_{user_id}")
    )
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=caption, reply_markup=markup)
    bot.reply_to(m, "✅ رسید شما دریافت شد. در حال بررسی توسط ادمین...")
    users[user_id]['pending_charge'] = 0
    save_users(users)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_ok_"))
def accept_charge(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    parts = call.data.split("_")
    user_id = parts[2]
    amount = int(parts[3])
    if user_id not in users:
        users[user_id] = {'credit': 0, 'pending_charge': 0, 'active_configs': []}
    users[user_id]['credit'] = users[user_id].get('credit', 0) + amount
    save_users(users)
    bot.send_message(int(user_id), f"✅ شارژ {amount:,} تومانی شما تایید شد!\n💰 اعتبار جدید: {users[user_id]['credit']:,} تومان")
    bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_no_"))
def reject_charge(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    parts = call.data.split("_")
    user_id = parts[2]
    bot.send_message(int(user_id), "❌ درخواست شارژ شما رد شد. لطفاً با پشتیبانی تماس بگیرید: @hegzosupport")
    bot.answer_callback_query(call.id, "❌ رد شد")

# ======================== منوهای دسته‌بندی ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def handle_category(call):
    category = call.data.replace("cat_", "")
    menus = {
        "economic": economic_menu,
        "family": family_menu,
        "speed": speed_menu
    }
    titles = {
        "economic": "🚀 اقتصادی",
        "family": "👨‍👩‍👧‍👦 خانواده (نامحدود)",
        "speed": "⚡ پرسرعت"
    }
    try:
        bot.edit_message_text(f"{titles[category]}\n\nلطفاً بسته مورد نظر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=menus[category](), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, f"{titles[category]}\n\nلطفاً بسته مورد نظر را انتخاب کنید:", reply_markup=menus[category](), parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_cmd(call):
    user_id = str(call.from_user.id)
    if is_banned(int(user_id)):
        bot.answer_callback_query(call.id, "❌ شما مسدود شده اید!", show_alert=True)
        return
    
    data_parts = call.data.split("_")
    price = int(data_parts[-1])
    package = "_".join(data_parts[1:-1])
    
    if user_id not in users:
        init_user(user_id)
    
    if discount_enabled and discounts:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎯 وارد کردن کد تخفیف", callback_data=f"discount_{user_id}_{price}_{package}"))
        markup.add(types.InlineKeyboardButton("⏭️ ادامه بدون تخفیف", callback_data=f"nodiscount_{user_id}_{price}_{package}"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
        
        bot.send_message(
            int(user_id),
            f"📦 بسته: {package}\n💰 قیمت: {price:,} تومان\n\n🎯 اگر کد تخفیف داری، روی دکمه زیر بزن:",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        return
    
    process_purchase(user_id, package, price, call)

# ======================== توابع خرید ========================
def process_purchase(user_id, package, price, call=None, discount_code=None):
    credit = users[user_id].get('credit', 0)
    original_price = price
    discount_text = ""
    
    if discount_code and discount_code in discounts and discount_enabled:
        disc = discounts[discount_code]
        if disc['used'] < disc['uses']:
            if disc['type'] == 'percent':
                discount_amount = int(price * disc['value'] / 100)
            else:
                discount_amount = disc['value']
            price = price - discount_amount
            if price < 0:
                price = 0
            discounts[discount_code]['used'] += 1
            discount_text = f"\n🎁 تخفیف: {discount_amount:,} تومان"
    
    if credit >= price:
        users[user_id]['credit'] = credit - price
        
        inviter_id = users[user_id].get('invited_by')
        if inviter_id and inviter_id in users:
            commission = int(original_price * COMMISSION_PERCENT / 100)
            if commission > 0:
                users[inviter_id]['credit'] = users[inviter_id].get('credit', 0) + commission
                users[inviter_id]['total_commission'] = users[inviter_id].get('total_commission', 0) + commission
                try:
                    bot.send_message(
                        int(inviter_id),
                        f"💰 **کمیسیون خرید**\n\n"
                        f"👤 کاربر زیرمجموعه‌ی شما یک کانفیگ خرید.\n"
                        f"📦 بسته: {package}\n"
                        f"💵 مبلغ اصلی: {original_price:,} تومان\n"
                        f"🎁 کمیسیون شما ({COMMISSION_PERCENT}%): {commission:,} تومان\n\n"
                        f"💰 اعتبار جدید: {users[inviter_id]['credit']:,} تومان"
                    )
                except:
                    pass
        
        save_users(users)
        username = users[user_id].get('username', 'بدون نام')
        
        admin_text = f"📸 درخواست کانفیگ!\n👤 @{username}\n🆔 {user_id}\n📦 {package}\n💰 اصلی: {original_price:,}\n💸 پرداخت: {price:,}{discount_text}"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{user_id}_{package}_{price}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"no_{user_id}"),
            types.InlineKeyboardButton("✏️ ارسال دستی", callback_data=f"send_{user_id}_{package}_{price}")
        )
        bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
        bot.send_message(int(user_id), f"✅ درخواست خرید {package} ثبت شد.{discount_text}")
        if call:
            bot.answer_callback_query(call.id, "✅ ثبت شد")
    else:
        bot.send_message(int(user_id), f"❌ اعتبار کافی نیست!\n💰 اعتبار: {credit:,} تومان\n💰 قیمت: {price:,} تومان")
        if call:
            bot.answer_callback_query(call.id, "❌ اعتبار")

@bot.callback_query_handler(func=lambda call: call.data.startswith("discount_"))
def discount_handler(call):
    parts = call.data.split("_")
    user_id = parts[1]
    price = parts[2]
    package = "_".join(parts[3:])
    
    msg = bot.send_message(call.message.chat.id, "🎯 کد تخفیف خود را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: apply_discount(m, user_id, int(price), package))
    bot.answer_callback_query(call.id)

def apply_discount(m, user_id, price, package):
    code = m.text.strip().upper()
    if code in discounts and discounts[code]['used'] < discounts[code]['uses'] and discount_enabled:
        process_purchase(user_id, package, price, discount_code=code)
    else:
        bot.reply_to(m, "❌ کد تخفیف نامعتبر یا منقضی شده است!")
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎯 وارد کردن مجدد", callback_data=f"discount_{user_id}_{price}_{package}"))
        markup.add(types.InlineKeyboardButton("⏭️ ادامه بدون تخفیف", callback_data=f"nodiscount_{user_id}_{price}_{package}"))
        bot.send_message(m.chat.id, "🔄 لطفاً انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("nodiscount_"))
def no_discount(call):
    parts = call.data.split("_")
    user_id = parts[1]
    price = int(parts[2])
    package = "_".join(parts[3:])
    
    process_purchase(user_id, package, price, call)
    bot.answer_callback_query(call.id)

# ======================== دکمه‌های برگشت ========================
@bot.callback_query_handler(func=lambda call: call.data == "back_buy")
def back_buy(call):
    try:
        bot.edit_message_text("📊 انتخاب دسته‌بندی:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())
    except:
        bot.send_message(call.message.chat.id, "📊 انتخاب دسته‌بندی:", reply_markup=buy_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    try:
        bot.edit_message_text("🔥 منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    except:
        bot.send_message(call.message.chat.id, "🔥 منوی اصلی:", reply_markup=main_keyboard())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def confirm_config(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    parts = call.data.split("_")
    user_id = parts[1]
    package = "_".join(parts[2:-1])
    price = int(parts[-1])
    bot.send_message(int(user_id), f"✅ کانفیگ {package} تایید شد!")
    bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def reject_config(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    user_id = call.data.split("_")[1]
    bot.send_message(int(user_id), "❌ رد شد! با پشتیبانی تماس بگیرید.")
    bot.answer_callback_query(call.id, "❌ رد شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def manual(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    parts = call.data.split("_")
    user_id = parts[1]
    package = "_".join(parts[2:-1])
    price = int(parts[-1])
    bot.send_message(call.message.chat.id, f"📝 کانفیگ {package} رو بفرست:")
    bot.register_next_step_handler(call.message, lambda m: send_config(m, user_id, package, price))
    bot.answer_callback_query(call.id)

def send_config(m, user_id, package, price):
    config = m.text
    if str(user_id) in users:
        users[str(user_id)].setdefault('active_configs', []).append({
            'package': package,
            'config': config,
            'date': str(datetime.now()),
            'price': price
        })
        save_users(users)
    bot.send_message(int(user_id), f"🎁 کانفیگ {package}:\n{config}")
    bot.reply_to(m, "✅ ارسال شد")

@bot.message_handler(func=lambda m: m.text == "📁 کانفیگ‌های من")
@membership_required
def my_configs(m):
    user_id = str(m.from_user.id)
    configs = users.get(user_id, {}).get('active_configs', [])
    if not configs:
        bot.reply_to(m, "📭 کانفیگ فعالی ندارید!")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(configs):
        markup.add(types.InlineKeyboardButton(f"{i+1}. {cfg.get('package', 'نامشخص')}", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    bot.reply_to(m, "📦 لیست کانفیگ‌ها:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("showcfg_"))
def show_config_detail(call):
    user_id = str(call.from_user.id)
    idx = int(call.data.split("_")[1])
    configs = users.get(user_id, {}).get('active_configs', [])
    if idx >= len(configs):
        bot.answer_callback_query(call.id, "❌ کانفیگ مورد نظر یافت نشد!", show_alert=True)
        return
    cfg = configs[idx]
    package = cfg.get('package', 'نامشخص')
    price = cfg.get('price', 0)
    date = cfg.get('date', 'نامشخص')
    config = cfg.get('config', 'ندارد')
    text = f"""📦 جزئیات کانفیگ
━━━━━━━━━━━━━━━━━━━━━
📌 بسته: {package}
💰 قیمت: {price:,} تومان
📅 تاریخ: {date}
━━━━━━━━━━━━━━━━━━━━━
🔗 لینک:
{config}
━━━━━━━━━━━━━━━━━━━━━
🆔 پشتیبانی: @hegzosupport"""
    bot.send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "👤 حساب کاربری")
@membership_required
def profile(m):
    user_id = str(m.from_user.id)
    data = users.get(user_id, {})
    text = f"""👤 **حساب کاربری**
━━━━━━━━━━━━━━━━━━━━━
💰 اعتبار: {data.get('credit', 0):,} تومان
📁 کانفیگ: {len(data.get('active_configs', []))} عدد
👥 دعوت‌ها: {data.get('referrals', 0)} نفر
🎁 کمیسیون: {data.get('total_commission', 0):,} تومان
━━━━━━━━━━━━━━━━━━━━━
🆔 آیدی: {user_id}"""
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "👥 دعوت از دوستان")
@membership_required
def invite(m):
    user_id = str(m.from_user.id)
    data = users.get(user_id, {})
    if not data.get('referral_code'):
        data['referral_code'] = generate_referral_code(user_id)
        users[user_id] = data
        save_users(users)
    referral_code = data.get('referral_code')
    bot_username = bot.get_me().username
    invite_link = f"https://t.me/{bot_username}?start={referral_code}"
    text = f"""🔥 **سیستم دعوت از دوستان**

👤 کد دعوت شما: `{referral_code}`
🔗 لینک دعوت: `{invite_link}`

━━━━━━━━━━━━━━━━━━━━━
🎁 **پاداش‌ها:**
• پاداش دعوت: {REFERRAL_AMOUNT:,} تومان (غیرفعال)
• کمیسیون خرید: {COMMISSION_PERCENT}% از هر خرید زیرمجموعه

👥 تعداد دعوت‌ها: {data.get('referrals', 0)} نفر
🎁 کل کمیسیون: {data.get('total_commission', 0):,} تومان

⚡ هرچه دوستان بیشتری دعوت کنی، کمیسیون بیشتری میگیری!"""
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
@membership_required
def support(m):
    bot.reply_to(m, "🆔 @hegzosupport\n۲۴ ساعته")

@bot.message_handler(commands=['users'])
def list_users(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not users:
        bot.reply_to(m, "📭 هیچ کاربری وجود ندارد.")
        return
    text = "📊 لیست کاربران:\n"
    for uid, data in users.items():
        text += f"🆔 {uid} | @{data.get('username', '')} | اعتبار: {data.get('credit',0):,} | دعوت: {data.get('referrals',0)} | کمیسیون: {data.get('total_commission',0):,}\n"
    bot.reply_to(m, text)

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    bot.reply_to(m, "📢 لطفاً پیام خود را بفرستید:")
    bot.register_next_step_handler(m, do_broadcast)

def do_broadcast(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    success = 0
    fail = 0
    for uid in users.keys():
        try:
            bot.send_message(int(uid), f"📢 پیام از ادمین:\n{m.text}")
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
    bot.reply_to(m, f"✅ ارسال شد!\n✅ موفق: {success}\n❌ ناموفق: {fail}")

@bot.message_handler(commands=['ban', 'unban'])
def ban_unban(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        uid = int(m.text.split()[1])
        if m.text.startswith('/ban'):
            banned_users.add(str(uid))
            bot.send_message(uid, "⛔ مسدود شدید!")
        else:
            banned_users.discard(str(uid))
            bot.send_message(uid, "✅ از مسدودیت خارج شدید!")
        save_banned_users()
        bot.reply_to(m, f"✅ {uid} {'بن' if m.text.startswith('/ban') else 'آنبن'} شد")
    except:
        bot.reply_to(m, "❌ /ban [user_id] یا /unban [user_id]")

@bot.message_handler(func=lambda m: True)
@membership_required
def unknown(m):
    bot.reply_to(m, "❌ از دکمه‌های منو استفاده کن.", reply_markup=main_keyboard())

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print("🤖 Hegzo VPN روشن شد!")
    print("✅ پاداش دعوت حذف شد - فقط کمیسیون ۱۰٪ فعال است!")
    print("✅ منوهای جدید: اقتصادی | خانواده | پرسرعت")
    print("✅ بخش لینک تست با توضیحات فعال شد!")
    print("✅ هر نوع لینکی قابل قبول است!")
    print("✅ دستور /start درست شد!")
    bot.delete_webhook()
    time.sleep(2)
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    bot.infinity_polling()
