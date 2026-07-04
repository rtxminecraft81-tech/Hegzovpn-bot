import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from flask import Flask
import threading
import random
from supabase import create_client, Client

app = Flask(__name__)

@app.route('/')
def home():
    return "Hegzo VPN Bot is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ توکن پیدا نشد! BOT_TOKEN رو توی Render تنظیم کن.")

ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'
CARD_NUMBER = '5022291525516892'
CARD_NAME = 'احمد خزایی'
REFERRAL_COMMISSION = 0.1
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
            'username': row.get('username', ''),
            'credit': row.get('credit', 0),
            'active_configs': row.get('active_configs', []),
            'pending_charge': row.get('pending_charge', 0),
            'invited_by': row.get('invited_by'),
            'referrals': row.get('referrals', 0),
            'joined_at': row.get('joined_at', ''),
            'commission': row.get('commission', 0)
        }
    return users

def save_users(users):
    for user_id, data in users.items():
        supabase.table("users").upsert({
            "user_id": user_id,
            "username": data.get('username', ''),
            "credit": data.get('credit', 0),
            "active_configs": data.get('active_configs', []),
            "pending_charge": data.get('pending_charge', 0),
            "invited_by": data.get('invited_by'),
            "referrals": data.get('referrals', 0),
            "commission": data.get('commission', 0)
        }).execute()

def init_user(user_id, username=""):
    if str(user_id) not in users:
        users[str(user_id)] = {
            'username': username,
            'credit': 0,
            'active_configs': [],
            'pending_charge': 0,
            'invited_by': None,
            'referrals': 0,
            'joined_at': str(datetime.now()),
            'commission': 0
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
            bot.reply_to(message, "⛔ شما توسط ادمین مسدود شده اید!")
            return
        if not is_member(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"),
                types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")
            )
            bot.reply_to(message, 
                f"❌ کاربر عزیز!\n\nبرای استفاده از ربات، ابتدا در کانال عضو شوید:\n🔗 @hegzo_vpn_channle\n\nسپس روی دکمه‌ی **✅ تایید عضویت** کلیک کنید.",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            return
        return func(message)
    return wrapper

# ======================== دکمه تایید عضویت ========================
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
        bot.answer_callback_query(call.id, "❌ هنوز عضو کانال نشده‌اید! لطفاً ابتدا عضو شوید.", show_alert=True)

# ======================== استیکرها و ایموجی‌ها ========================
STICKERS = {
    'welcome': 'CAACAgQAAxkBAAE...',
    'success': 'CAACAgQAAxkBAAE...',
    'error': 'CAACAgQAAxkBAAE...',
    'money': 'CAACAgQAAxkBAAE...',
    'fire': 'CAACAgQAAxkBAAE...',
    'cool': 'CAACAgQAAxkBAAE...',
}

EMOJIS = {
    'loading': ['⏳', '🔄', '⚡', '💫'],
    'success': ['✅', '🎉', '🎊', '✨', '💎'],
    'error': ['❌', '⛔', '🚫', '💢'],
    'money': ['💰', '💸', '🤑', '💵'],
    'fire': ['🔥', '❤️‍🔥', '⚡', '🌟'],
}

def get_random_emoji(category):
    return random.choice(EMOJIS.get(category, ['✨']))

def loading_animation(message, text, duration=2):
    msg = bot.reply_to(message, f"{get_random_emoji('loading')} {text}")
    time.sleep(duration)
    return msg

def delete_with_animation(message, delay=0.5):
    try:
        time.sleep(delay)
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

def send_sticker(user_id, sticker_key):
    try:
        if sticker_key in STICKERS:
            bot.send_sticker(user_id, STICKERS[sticker_key])
    except:
        pass

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 شارژ کیف پول", "🛒 خرید کانفیگ")
    markup.add("📁 کانفیگ‌های من", "👤 حساب کاربری")
    markup.add("👥 دعوت از دوستان", "🆘 پشتیبانی")
    markup.add("🏠 منوی اصلی")
    return markup

# ======================== منوهای جدید خرید ========================
def buy_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⭐ اینفلوئنسر و استریمر", callback_data="lev_influencer"))
    markup.add(types.InlineKeyboardButton("🌐 گشت‌وگذار عادی", callback_data="lev_normal"))
    markup.add(types.InlineKeyboardButton("🎮 گیمینگ و حرفه‌ای", callback_data="lev_gaming"))
    markup.add(types.InlineKeyboardButton("👑 VIP و شاهانه", callback_data="lev_vip"))
    markup.add(types.InlineKeyboardButton("🌍 مولتی‌لوکیشن", callback_data="lev_multi"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return markup

def influencer_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - تک کاربره ۵۹۰,۰۰۰", callback_data="b_influencer100_590000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۲ کاربره ۷۹۰,۰۰۰", callback_data="b_influencer100_790000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۳ کاربره ۹۹۰,۰۰۰", callback_data="b_influencer100_990000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۳ ماهه تک کاربره ۱,۴۹۰,۰۰۰", callback_data="b_influencer100_1490000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۳ ماهه ۲ کاربره ۱,۹۹۰,۰۰۰", callback_data="b_influencer100_1990000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۳ ماهه ۳ کاربره ۲,۴۹۰,۰۰۰", callback_data="b_influencer100_2490000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def normal_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🌐 ۲۵ گیگ - ۱۹۰,۰۰۰", callback_data="b_normal25_190000"))
    markup.add(types.InlineKeyboardButton("🌍 ۵۰ گیگ - ۲۹۰,۰۰۰", callback_data="b_normal50_290000"))
    markup.add(types.InlineKeyboardButton("🌎 ۱۰۰ گیگ - ۴۹۰,۰۰۰", callback_data="b_normal100_490000"))
    markup.add(types.InlineKeyboardButton("🌏 ۲۰۰ گیگ - ۷۹۰,۰۰۰", callback_data="b_normal200_790000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def gaming_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💎 ۱۰ گیگ الماس - ۲۰۰,۰۰۰", callback_data="b_gaming_diamond10_200000"))
    markup.add(types.InlineKeyboardButton("💎 ۲۰ گیگ الماس - ۳۹۰,۰۰۰", callback_data="b_gaming_diamond20_390000"))
    markup.add(types.InlineKeyboardButton("💎 ۳۰ گیگ الماس - ۵۵۰,۰۰۰", callback_data="b_gaming_diamond30_550000"))
    markup.add(types.InlineKeyboardButton("💎 ۵۰ گیگ الماس - ۷۵۰,۰۰۰", callback_data="b_gaming_diamond50_750000"))
    markup.add(types.InlineKeyboardButton("💎 ۱۰۰ گیگ الماس - ۱,۲۵۰,۰۰۰", callback_data="b_gaming_diamond100_1250000"))
    markup.add(types.InlineKeyboardButton("💎 ۱۵۰ گیگ الماس - ۱,۹۸۰,۰۰۰", callback_data="b_gaming_diamond150_1980000"))
    markup.add(types.InlineKeyboardButton("💎 ۲۰۰ گیگ الماس - ۲,۴۶۰,۰۰۰", callback_data="b_gaming_diamond200_2460000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def vip_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👑 ۲۰ گیگ شاهانه - ۵۵۰,۰۰۰", callback_data="b_vip20_550000"))
    markup.add(types.InlineKeyboardButton("👑 ۳۰ گیگ شاهانه - ۷۵۰,۰۰۰", callback_data="b_vip30_750000"))
    markup.add(types.InlineKeyboardButton("👑 ۵۰ گیگ شاهانه - ۱,۱۰۰,۰۰۰", callback_data="b_vip50_1100000"))
    markup.add(types.InlineKeyboardButton("👑 ۱۰۰ گیگ شاهانه - ۱,۸۰۰,۰۰۰", callback_data="b_vip100_1800000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def multi_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🌍 ۱۰ گیگ مولتی - ۱۸۰,۰۰۰", callback_data="b_multi10_180000"))
    markup.add(types.InlineKeyboardButton("🌍 ۲۰ گیگ مولتی - ۳۰۰,۰۰۰", callback_data="b_multi20_300000"))
    markup.add(types.InlineKeyboardButton("🌍 ۳۰ گیگ مولتی - ۴۵۰,۰۰۰", callback_data="b_multi30_450000"))
    markup.add(types.InlineKeyboardButton("🌍 ۵۰ گیگ مولتی - ۶۵۰,۰۰۰", callback_data="b_multi50_650000"))
    markup.add(types.InlineKeyboardButton("🌍 ۱۰۰ گیگ مولتی - ۱,۰۰۰,۰۰۰", callback_data="b_multi100_1000000"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return markup

def admin_buttons(user_id, package, price):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{user_id}_{package}_{price}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"no_{user_id}"),
        types.InlineKeyboardButton("✏️ ارسال دستی", callback_data=f"send_{user_id}_{package}_{price}")
    )
    return markup

def admin_charge_buttons(user_id, amount):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تایید شارژ", callback_data=f"ch_ok_{user_id}_{amount}"),
        types.InlineKeyboardButton("❌ رد شارژ", callback_data=f"ch_no_{user_id}")
    )
    return markup

# ======================== منوی جدید شارژ ========================
def charge_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💳 کارت به کارت", callback_data="charge_card"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return markup

# ======================== دستورات و منوها ========================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما توسط ادمین مسدود شده اید!")
        return
    
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔗 عضویت در کانال", url="https://t.me/hegzo_vpn_channle"),
            types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")
        )
        bot.reply_to(message, 
            f"❌ کاربر عزیز!\n\nبرای استفاده از ربات، ابتدا در کانال عضو شوید:\n🔗 @hegzo_vpn_channle\n\nسپس روی دکمه‌ی **✅ تایید عضویت** کلیک کنید.",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        return
    
    loading_msg = loading_animation(message, "🔥 در حال آماده‌سازی...", 1.5)
    delete_with_animation(loading_msg, 0.3)
    
    name = message.from_user.first_name
    init_user(user_id, message.from_user.username or "")
    
    if len(message.text.split()) > 1:
        try:
            ref_param = message.text.split()[1]
            try:
                ref = int(ref_param)
            except:
                ref = ref_param
            
            if str(ref).startswith('start='):
                ref = str(ref).replace('start=', '')
            
            if str(ref) != str(user_id):
                if not users.get(str(user_id), {}).get('invited_by'):
                    inviter = None
                    try:
                        ref_int = int(ref)
                        if str(ref_int) in users:
                            inviter = str(ref_int)
                    except:
                        for uid, data in users.items():
                            if data.get('username', '').lower() == str(ref).lower():
                                inviter = uid
                                break
                    
                    if inviter and inviter != str(user_id):
                        users[str(user_id)]['invited_by'] = inviter
                        users[inviter]['referrals'] += 1
                        save_users(users)
                        
                        bot.send_message(
                            int(inviter), 
                            f"🎉 **یک کاربر جدید با لینک شما عضو شد!**\n\n"
                            f"👤 کاربر: {message.from_user.first_name}\n"
                            f"📊 تعداد دعوت‌ها: {users[inviter].get('referrals', 0)}"
                        )
        except Exception as e:
            print(f"❌ خطا در پردازش لینک دعوت: {e}")
    
    send_sticker(user_id, 'welcome')
    bot.reply_to(message, 
        f"""🔥 **به 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵 خوش اومدی** {name}! 🎉

⚡ **اینترنت آزاد و بدون محدودیت**
🛡️ **امنیت کامل و سرعت بالا**
💎 **کیفیت عالی با قیمت مناسب**

✨ از منوی زیر یکی رو انتخاب کن:
""", 
        reply_markup=main_keyboard(), 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "🏠 منوی اصلی")
@membership_required
def back_home(m):
    loading_msg = loading_animation(m, "🔄 در حال بازگشت به منوی اصلی...", 1)
    delete_with_animation(loading_msg, 0.3)
    bot.reply_to(m, 
        f"🔥 **منوی اصلی 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**\n\n{get_random_emoji('fire')} آماده خدمت‌رسانی هستم!",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "🛒 خرید کانفیگ")
@membership_required
def show_buy(m):
    loading_msg = loading_animation(m, "📦 در حال بارگذاری سرویس‌ها...", 1)
    delete_with_animation(loading_msg, 0.3)
    bot.reply_to(m, 
        f"📊 **انتخاب نوع سرویس**\n\n{get_random_emoji('fire')} بهترین سرویس رو انتخاب کن:",
        reply_markup=buy_menu(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "👤 حساب کاربری")
@membership_required
def profile(m):
    user_id = m.from_user.id
    data = users.get(str(user_id), {})
    active_count = len(data.get('active_configs', []))
    
    loading_msg = loading_animation(m, "📊 در حال دریافت اطلاعات...", 1)
    delete_with_animation(loading_msg, 0.3)
    
    username = m.from_user.username or "بدون نام"
    text = f"""👤 **حساب کاربری 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**

━━━━━━━━━━━━━━━━━━━━━
🆔 شناسه: `{user_id}`
👤 نام کاربری: @{username}
👤 نام: {m.from_user.first_name}
📊 کانفیگ فعال: {active_count}
👥 زیرمجموعه: {data.get('referrals', 0)}
💰 اعتبار کیف پول: {data.get('credit', 0):,} تومان
💰 کمیسیون累积: {data.get('commission', 0):,} تومان
━━━━━━━━━━━━━━━━━━━━━

💡 با دعوت از دوستانت، از هر خرید آنها ۱۰٪ کمیسیون دریافت کن!

{get_random_emoji('success')} کاربر عزیز، همیشه در کنارتیم!"""
    
    send_sticker(user_id, 'cool')
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "👥 دعوت از دوستان")
@membership_required
def invite(m):
    user_id = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    data = users.get(str(user_id), {})
    
    text = f"""🔥 **لینک دعوت اختصاصی شما**

`{link}`

👥 دعوت‌ها: {data.get('referrals', 0)}
💰 کمیسیون累计: {data.get('commission', 0):,} تومان

💎 **با هر خرید دوستانت، ۱۰٪ کمیسیون دریافت کن!**

هر چه دوستان بیشتری دعوت کنی، درآمد بیشتری خواهی داشت!"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url={link}&text=🔥 به ربات Hegzo VPN بپیوند! اینترنت آزاد و بدون محدودیت!"))
    
    bot.reply_to(m, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
@membership_required
def support(m):
    send_sticker(m.from_user.id, 'fire')
    bot.reply_to(m, 
        f"""🆔 **پشتیبانی 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**

{get_random_emoji('success')} ۲۴ ساعته پاسخگوی شما هستیم!

📱 @hegzosupport

⚠️ لطفاً قبل از تماس، سوال خود را دقیق مطرح کنید تا سریع‌تر پاسخ بگیرید.""",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
@membership_required
def charge(m):
    user_id = m.from_user.id
    send_sticker(user_id, 'money')
    bot.reply_to(m, 
        f"💳 **شارژ کیف پول 𝑯𝑬𝑮𝒁𝑶 𝑽𝑷𝑵**\n\n"
        f"{get_random_emoji('money')} لطفاً روش شارژ مورد نظر خود را انتخاب کنید:",
        reply_markup=charge_menu(),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == "charge_card")
def charge_card(call):
    user_id = call.from_user.id
    text = f"""💳 **اطلاعات کارت به کارت**

━━━━━━━━━━━━━━━━━━━━━
🏦 **شماره کارت:** `{CARD_NUMBER}`
👤 **به نام:** {CARD_NAME}
━━━━━━━━━━━━━━━━━━━━━

💰 **حداقل شارژ:** {MIN_CHARGE:,} تومان

📌 **مراحل شارژ:**
1️⃣ مبلغ مورد نظر را به کارت بالا واریز کنید.
2️⃣ مبلغ را در ربات وارد کنید.
3️⃣ عکس رسید را بفرستید.

⚠️ پس از تایید ادمین، مبلغ به کیف پول شما اضافه خواهد شد.

🆔 پشتیبانی: @hegzosupport"""
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    # درخواست وارد کردن مبلغ
    msg = bot.send_message(user_id, f"💰 **لطفاً مبلغ واریز شده را به تومان وارد کنید:**")
    bot.register_next_step_handler(msg, get_charge_amount)

def get_charge_amount(m):
    user_id = m.from_user.id
    try:
        amount = int(m.text)
        if amount < MIN_CHARGE:
            bot.reply_to(m, f"❌ **حداقل شارژ {MIN_CHARGE:,} تومان است!**\n\nلطفاً مبلغ بیشتری واریز کنید.")
            return
        users[str(user_id)]['pending_charge'] = amount
        save_users(users)
        bot.reply_to(m, f"✅ **مبلغ {amount:,} تومان ثبت شد!**\n\n📸 لطفاً عکس رسید واریز را بفرستید.")
    except:
        bot.reply_to(m, f"❌ **لطفاً یک عدد معتبر وارد کنید!**\n\nمثال: 200000")

@bot.message_handler(content_types=['photo'])
@membership_required
def receipt(m):
    user_id = m.from_user.id
    username = m.from_user.username or "بدون نام"
    file_id = m.photo[-1].file_id
    pending = users.get(str(user_id), {}).get('pending_charge', 0)
    
    if pending > 0:
        admin_text = f"💰 **درخواست شارژ!**\n👤 @{username}\n🆔 {user_id}\n💸 مبلغ: {pending:,} تومان"
        bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=admin_charge_buttons(user_id, pending), parse_mode='Markdown')
        
        loading_msg = loading_animation(m, "📤 در حال ارسال رسید...", 1)
        delete_with_animation(loading_msg, 0.3)
        
        bot.reply_to(m, f"✅ **رسید شما دریافت شد!**\n\n{get_random_emoji('loading')} در حال بررسی توسط ادمین...\n\n⏳ لطفاً چند دقیقه صبر کنید.")
        users[str(user_id)]['pending_charge'] = 0
        save_users(users)
        send_sticker(user_id, 'success')
    else:
        bot.reply_to(m, f"❌ **ابتدا از منوی اصلی روی 💳 شارژ کیف پول کلیک کن و مبلغ را وارد کن.**\n\n{get_random_emoji('error')}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📁 کانفیگ‌های من")
@membership_required
def my_configs_list(m):
    user_id = m.from_user.id
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    loading_msg = loading_animation(m, "📁 در حال دریافت کانفیگ‌ها...", 1)
    delete_with_animation(loading_msg, 0.3)
    
    if not cfg_list:
        bot.reply_to(m, 
            f"📭 **کانفیگ فعالی ندارید!**\n\n{get_random_emoji('error')} برای خرید کانفیگ از بخش 🛒 خرید کانفیگ اقدام کنید.",
            parse_mode='Markdown'
        )
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(cfg_list):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    
    bot.reply_to(m, 
        f"📦 **لیست کانفیگ‌های فعال شما**\n\n{get_random_emoji('fire')} {len(cfg_list)} کانفیگ فعال داری!\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ======================== Callback های جدید ========================
@bot.callback_query_handler(func=lambda call: call.data == "lev_influencer")
def lev_influencer(call):
    try:
        bot.edit_message_text("⭐ **اینفلوئنسر و استریمر**\n\nسرویس‌های اختصاصی برای تولیدکنندگان محتوا:", call.message.chat.id, call.message.message_id, reply_markup=influencer_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "⭐ **اینفلوئنسر و استریمر**\n\nسرویس‌های اختصاصی برای تولیدکنندگان محتوا:", reply_markup=influencer_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_normal")
def lev_normal(call):
    try:
        bot.edit_message_text("🌐 **گشت‌وگذار عادی**\n\nمناسب برای استفاده‌ی روزمره:", call.message.chat.id, call.message.message_id, reply_markup=normal_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "🌐 **گشت‌وگذار عادی**\n\nمناسب برای استفاده‌ی روزمره:", reply_markup=normal_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_gaming")
def lev_gaming(call):
    try:
        bot.edit_message_text("🎮 **گیمینگ و حرفه‌ای**\n\nسرویس‌های ویژه برای گیمرها و کاربران حرفه‌ای:", call.message.chat.id, call.message.message_id, reply_markup=gaming_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "🎮 **گیمینگ و حرفه‌ای**\n\nسرویس‌های ویژه برای گیمرها و کاربران حرفه‌ای:", reply_markup=gaming_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_vip")
def lev_vip(call):
    try:
        bot.edit_message_text("👑 **VIP و شاهانه**\n\nسرویس‌های لوکس برای کاربران ویژه:", call.message.chat.id, call.message.message_id, reply_markup=vip_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "👑 **VIP و شاهانه**\n\nسرویس‌های لوکس برای کاربران ویژه:", reply_markup=vip_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "lev_multi")
def lev_multi(call):
    try:
        bot.edit_message_text("🌍 **مولتی‌لوکیشن**\n\nسرویس‌های با چندین موقعیت مکانی:", call.message.chat.id, call.message.message_id, reply_markup=multi_menu(), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "🌍 **مولتی‌لوکیشن**\n\nسرویس‌های با چندین موقعیت مکانی:", reply_markup=multi_menu(), parse_mode='Markdown')

# ======================== بقیه‌ی Callback ها ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("showcfg_"))
def show_config_detail(call):
    user_id = call.from_user.id
    if not is_member(user_id):
        bot.answer_callback_query(call.id, "❌ ابتدا در کانال عضو شوید!", show_alert=True)
        return
    idx = int(call.data.split("_")[1])
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    if idx >= len(cfg_list):
        bot.answer_callback_query(call.id, "❌ کانفیگ مورد نظر یافت نشد!", show_alert=True)
        return
    
    cfg = cfg_list[idx]
    package = cfg.get('package', 'نامشخص')
    config = cfg.get('config', 'نامشخص')
    date = cfg.get('date', 'نامشخص')
    price = cfg.get('price', 'نامشخص')
    
    text = f"""📦 **جزئیات کانفیگ {idx+1}**

━━━━━━━━━━━━━━━━━━━━━
📌 **بسته:** {package}
💰 **مبلغ:** {price:,} تومان
📅 **تاریخ دریافت:** {date}
━━━━━━━━━━━━━━━━━━━━━
🔗 **لینک کانفیگ:**
`{config}`
━━━━━━━━━━━━━━━━━━━━━
💡 **نحوه استفاده:**
روی لینک بالا فشار طولانی بدید و Copy رو بزنید، سپس در برنامه V2rayNG یا NPV Tunnel وارد کنید.
━━━━━━━━━━━━━━━━━━━━━
🆔 پشتیبانی: @hegzosupport"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست کانفیگ‌ها", callback_data="back_to_configs"))
    markup.add(types.InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_configs")
def back_to_configs(call):
    user_id = call.from_user.id
    if not is_member(user_id):
        bot.answer_callback_query(call.id, "❌ ابتدا در کانال عضو شوید!", show_alert=True)
        return
    cfg_list = users.get(str(user_id), {}).get('active_configs', [])
    
    if not cfg_list:
        try:
            bot.edit_message_text("📭 کانفیگ فعالی ندارید!", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, "📭 کانفیگ فعالی ندارید!", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(cfg_list):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text("📦 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "📦 **لیست کانفیگ‌های فعال شما**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "back_buy")
def back_buy(call):
    try:
        bot.edit_message_text("📊 انتخاب نوع سرویس:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())
    except:
        bot.send_message(call.message.chat.id, "📊 انتخاب نوع سرویس:", reply_markup=buy_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    try:
        bot.edit_message_text("🔥 منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    except:
        bot.send_message(call.message.chat.id, "🔥 منوی اصلی:", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("b_"))
def buy_cmd(call):
    user_id = call.from_user.id
    if is_banned(user_id):
        bot.answer_callback_query(call.id, "❌ شما مسدود شده اید!", show_alert=True)
        return
    if not is_member(user_id):
        bot.answer_callback_query(call.id, "❌ ابتدا در کانال عضو شوید!", show_alert=True)
        return
    
    parts = call.data.split("_")
    price = int(parts[-1])
    package = "_".join(parts[1:-1])
    
    credit = users.get(str(user_id), {}).get('credit', 0)
    if credit >= price:
        users[str(user_id)]['credit'] -= price
        save_users(users)
        username = call.from_user.username or "بدون نام"
        
        inviter_id = users.get(str(user_id), {}).get('invited_by')
        if inviter_id:
            commission_amount = int(price * REFERRAL_COMMISSION)
            users[inviter_id]['commission'] = users[inviter_id].get('commission', 0) + commission_amount
            save_users(users)
            bot.send_message(
                int(inviter_id),
                f"💎 **کمیسیون جدید!**\n\n"
                f"👤 کاربر: @{username}\n"
                f"📦 بسته: {package}\n"
                f"💰 مبلغ خرید: {price:,} تومان\n"
                f"💸 کمیسیون شما (۱۰%): {commission_amount:,} تومان\n\n"
                f"📊 کمیسیون کل: {users[inviter_id].get('commission', 0):,} تومان"
            )
        
        admin_text = f"📸 **درخواست کانفیگ جدید!**\n\n👤 کاربر: @{username}\n🆔 آیدی: {user_id}\n📦 بسته: {package}\n💰 مبلغ: {price:,} تومان"
        bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_buttons(user_id, package, price), parse_mode='Markdown')
        
        bot.send_message(user_id, f"✅ **درخواست شما ثبت شد!**\n\n{get_random_emoji('loading')} منتظر تایید ادمین باشید.\n\n⏳ معمولاً کمتر از ۵ دقیقه طول می‌کشد.")
        bot.answer_callback_query(call.id, "✅ ثبت شد")
        send_sticker(user_id, 'fire')
        try:
            bot.edit_message_text("✅ درخواست ثبت شد. منتظر تایید ادمین.", call.message.chat.id, call.message.message_id)
        except:
            pass
    else:
        need = price - credit
        bot.send_message(user_id, 
            f"""❌ **اعتبار کافی نیست!**

💰 اعتبار شما: {credit:,} تومان
💸 نیاز به {need:,} تومان دیگر

💳 برای افزایش اعتبار، از منوی اصلی روی «💳 شارژ کیف پول» کلیک کن.

💡 راهنمایی: با دعوت از دوستانت، از هر خرید آنها ۱۰٪ کمیسیون دریافت کن!""",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "❌ اعتبار کافی نیست")

# ======================== دکمه‌های ادمین برای شارژ ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_ok_"))
def ch_ok(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = int(parts[2])
    amount = int(parts[3])
    
    if str(user_id) in users:
        users[str(user_id)]['credit'] += amount
        save_users(users)
        
        send_sticker(user_id, 'money')
        bot.send_message(user_id, 
            f"""✅ **شارژ {amount:,} تومانی تایید شد!**

💰 اعتبار جدید: {users[str(user_id)]['credit']:,} تومان

{get_random_emoji('success')} حالا می‌تونی کانفیگ مورد نظرت رو بخری!

🛒 از منوی اصلی روی خرید کانفیگ کلیک کن.""",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "✅ تایید شد")
        try:
            bot.edit_message_caption("✅ تایید شد", call.message.chat.id, call.message.message_id)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_no_"))
def ch_no(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    user_id = int(call.data.split("_")[2])
    
    if str(user_id) in users:
        bot.send_message(user_id, 
            f"""❌ **درخواست شارژ رد شد!**

{get_random_emoji('error')} لطفاً با پشتیبانی تماس بگیرید:

📱 @hegzosupport

💡 نکته: حتماً رسید را به درستی ارسال کنید.""",
            parse_mode='Markdown'
        )
    bot.answer_callback_query(call.id, "❌ رد شد")
    try:
        bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)
    except:
        pass

# ======================== بقیه‌ی دکمه‌های ادمین ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def confirm(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = int(parts[1])
    package = parts[2]
    price = int(parts[3])
    
    bot.send_message(user_id, f"✅ **کانفیگ {package} تایید شد!**\n\n{get_random_emoji('success')} منتظر دریافت کانفیگ از ادمین باش.\n\n🆔 پشتیبانی: @hegzosupport", parse_mode='Markdown')
    bot.answer_callback_query(call.id, "✅ تایید شد")
    send_sticker(user_id, 'success')
    try:
        bot.edit_message_caption(f"✅ تایید شد - {package}", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def reject(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    user_id = int(call.data.split("_")[1])
    
    bot.send_message(user_id, 
        f"""❌ **درخواست شما رد شد!**

{get_random_emoji('error')} لطفاً با پشتیبانی تماس بگیرید:

📱 @hegzosupport

💡 دلیل احتمالی:
• اطلاعات ناقص
• مشکل در پرداخت
• بسته ناموجود""",
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id, "❌ رد شد")
    try:
        bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def manual(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = int(parts[1])
    package = parts[2]
    price = int(parts[3])
    
    bot.send_message(call.message.chat.id, f"📝 لطفا کانفیگ مورد نظر برای کاربر {user_id} (بسته: {package}) را بفرستید:")
    bot.register_next_step_handler(call.message, lambda m: send_config(m, user_id, package, price))
    bot.answer_callback_query(call.id)

def send_config(m, user_id, package, price):
    config = m.text
    if str(user_id) in users:
        users[str(user_id)].setdefault('active_configs', []).append({'package': package, 'config': config, 'date': str(datetime.now()), 'price': price})
        save_users(users)
    
    send_sticker(user_id, 'success')
    bot.send_message(user_id, 
        f"""🎁 **کانفیگ اختصاصی شما ({package})**

`{config}`

{get_random_emoji('success')} کانفیگ با موفقیت ثبت شد!

📅 تاریخ فعال‌سازی: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🆔 پشتیبانی: @hegzosupport""",
        parse_mode='Markdown'
    )
    bot.reply_to(m, "✅ کانفیگ با موفقیت ارسال شد")

# ======================== دستورات ادمین ========================
@bot.message_handler(commands=['users'])
def list_users(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not users:
        bot.reply_to(m, "📭 هیچ کاربری وجود ندارد.")
        return
    text = "📊 **لیست کاربران Hegzo VPN**\n\n"
    for uid, data in users.items():
        username = data.get('username', 'بدون نام')
        text += f"🆔 `{uid}` | @{username} | اعتبار: {data.get('credit',0):,} | دعوت: {data.get('referrals',0)} | کمیسیون: {data.get('commission',0):,}\n"
    bot.reply_to(m, text, parse_mode='Markdown')

# ======================== دستور broadcast ========================
@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    bot.reply_to(m, "📢 **لطفاً پیام، عکس، ویدیو، گیف، استیکر یا هر محتوایی که می‌خواهید برای همه ارسال شود را بفرستید.**\n\n📌 اگر پیام متنی است، آن را تایپ کنید.\n📌 اگر فایل است، آن را آپلود کنید.\n\n⏳ پس از ارسال، پیام برای همه کاربران ارسال خواهد شد.")
    bot.register_next_step_handler(m, do_broadcast)

def do_broadcast(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    
    success = 0
    fail = 0
    user_ids = list(users.keys())
    
    for uid in user_ids:
        try:
            if m.text:
                bot.send_message(int(uid), f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.text}", parse_mode='Markdown')
            elif m.photo:
                bot.send_photo(int(uid), m.photo[-1].file_id, caption=f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.caption or ''}", parse_mode='Markdown')
            elif m.video:
                bot.send_video(int(uid), m.video.file_id, caption=f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.caption or ''}", parse_mode='Markdown')
            elif m.animation:
                bot.send_animation(int(uid), m.animation.file_id, caption=f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.caption or ''}", parse_mode='Markdown')
            elif m.sticker:
                bot.send_sticker(int(uid), m.sticker.file_id)
            elif m.document:
                bot.send_document(int(uid), m.document.file_id, caption=f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.caption or ''}", parse_mode='Markdown')
            elif m.voice:
                bot.send_voice(int(uid), m.voice.file_id, caption=f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.caption or ''}", parse_mode='Markdown')
            elif m.audio:
                bot.send_audio(int(uid), m.audio.file_id, caption=f"📢 **پیام از ادمین Hegzo VPN**\n\n{m.caption or ''}", parse_mode='Markdown')
            else:
                bot.send_message(int(uid), f"📢 **پیام از ادمین Hegzo VPN**\n\n{get_random_emoji('fire')} پیام جدید از ادمین!", parse_mode='Markdown')
            success += 1
            time.sleep(0.05)
        except Exception as e:
            fail += 1
            print(f"❌ ارسال به {uid} ناموفق: {e}")
    
    bot.reply_to(m, f"✅ **ارسال پیام پایان یافت!**\n\n✅ موفق: {success}\n❌ ناموفق: {fail}")

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
        try:
            bot.send_message(user_id, "⛔ شما توسط ادمین مسدود شده اید!\n🆔 @hegzosupport")
        except:
            pass
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

@bot.message_handler(commands=['banned'])
def list_banned(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not banned_users:
        bot.reply_to(m, "📭 هیچ کاربر مسدود شده‌ای وجود ندارد.")
        return
    text = "🚫 **لیست کاربران مسدود شده:**\n\n"
    for uid in banned_users:
        text += f"🆔 `{uid}`\n"
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
@membership_required
def unknown(m):
    user_id = m.from_user.id
    if is_banned(user_id):
        bot.reply_to(m, "⛔ شما مسدود شده اید!")
        return
    bot.reply_to(m, 
        f"😅 **اوه! این دکمه رو ندارم!**\n\n{get_random_emoji('error')} لطفا از دکمه‌های منوی اصلی استفاده کنید.\n\n{get_random_emoji('fire')} منو در دسترس است:",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

# ======================== اجرای ربات ========================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 Hegzo VPN روی پورت {PORT} روشن شد!")
    print("✅ اتصال به Supabase برای ذخیره‌سازی دائمی فعال شد!")
    print("✅ سیستم کمیسیون ۱۰% برای دعوت‌کنندگان فعال شد!")
    print("✅ منوی جدید شارژ (کارت به کارت) با حداقل ۲۰۰,۰۰۰ تومان فعال شد!")
    print("✅ سیستم وارد کردن مبلغ و ارسال رسید برای ادمین فعال شد!")
    print("✅ عضویت در کانال برای همه عملیات‌ها الزامی شد!")
    print("✅ دکمه تایید عضویت اضافه شد!")
    print("✅ سیستم دعوت (Deep Link) با پشتیبانی از آیدی عددی و یوزرنیم فعال شد!")
    print("✅ نام کاربری (با @) در پیام‌های ادمین نمایش داده می‌شود!")
    print("✅ دستور broadcast با قابلیت ارسال عکس، ویدیو، گیف، استیکر، فایل و متن فعال شد!")
    print("✅ سرویس‌های جدید (اینفلوئنسر، گشت‌وگذار، گیمینگ، VIP، مولتی‌لوکیشن) اضافه شدند!")

    bot.delete_webhook()
    time.sleep(2)

    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()

    bot.infinity_polling()
