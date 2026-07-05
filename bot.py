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
REFERRAL_COMMISSION = 0.1  # 10% کمیسیون

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
            'commission': row.get('commission', 0),
            'joined_at': row.get('joined_at', '')
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
            "commission": data.get('commission', 0),
            "joined_at": data.get('joined_at', '')
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
            'commission': 0,
            'joined_at': str(datetime.now())
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

# ======================== منوهای خرید ========================
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
    
    # سیستم دعوت اینفلوئنسری
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
                        bot.send_message(int(inviter), 
                            f"🎉 یک کاربر جدید با لینک شما عضو شد!\n\n👤 {message.from_user.first_name}\n📊 تعداد دعوت‌ها: {users[inviter].get('referrals', 0)}"
                        )
        except:
            pass
    
    bot.reply_to(message, 
        f"""🔥 **به هگزو وی‌پی‌ان خوش اومدی** {name}! 🎉

⚡ اینترنت آزاد و بدون محدودیت
🛡️ امنیت کامل و سرعت بالا
💎 کیفیت عالی با قیمت مناسب

✨ از منوی زیر یکی رو انتخاب کن:
""", 
        reply_markup=main_keyboard(), 
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "🏠 منوی اصلی")
@membership_required
def back_home(m):
    bot.reply_to(m, "🔥 منوی اصلی:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🛒 خرید کانفیگ")
@membership_required
def show_buy(m):
    bot.reply_to(m, "📊 انتخاب نوع سرویس:", reply_markup=buy_menu())

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
👥 دعوت‌ها: {data.get('referrals', 0)}
💰 کمیسیون累计: {data.get('commission', 0):,} تومان
━━━━━━━━━━━━━━━━━━━━━

💡 با دعوت از دوستانت، ۱۰٪ کمیسیون دریافت کن!"""
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

💎 با هر خرید دوستانت، ۱۰٪ کمیسیون دریافت کن!"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url={link}&text=🔥 به هگزو وی‌پی‌ان بپیوند!"))
    bot.reply_to(m, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
@membership_required
def support(m):
    bot.reply_to(m, "🆔 **پشتیبانی هگزو وی‌پی‌ان**\n\n@hegzosupport\n\n۲۴ ساعته پاسخگوی شما هستیم.", parse_mode='Markdown')

# ======================== خرید کانفیگ ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("lev_"))
def handle_lev(call):
    menus = {
        "lev_influencer": influencer_menu,
        "lev_normal": normal_menu,
        "lev_gaming": gaming_menu,
        "lev_vip": vip_menu,
        "lev_multi": multi_menu
    }
    titles = {
        "lev_influencer": "⭐ اینفلوئنسر",
        "lev_normal": "🌐 گشت‌وگذار",
        "lev_gaming": "🎮 گیمینگ",
        "lev_vip": "👑 VIP",
        "lev_multi": "🌍 مولتی‌لوکیشن"
    }
    try:
        bot.edit_message_text(f"{titles[call.data]}\n\nلطفاً بسته مورد نظر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=menus[call.data](), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, f"{titles[call.data]}\n\nلطفاً بسته مورد نظر را انتخاب کنید:", reply_markup=menus[call.data](), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("b_"))
def buy_cmd(call):
    user_id = str(call.from_user.id)
    if is_banned(int(user_id)):
        bot.answer_callback_query(call.id, "❌ شما مسدود شده اید!", show_alert=True)
        return
    
    parts = call.data.split("_")
    price = int(parts[-1])
    package = "_".join(parts[1:-1])
    
    if user_id not in users:
        init_user(user_id)
    
    credit = users[user_id].get('credit', 0)
    if credit >= price:
        users[user_id]['credit'] = credit - price
        save_users(users)
        username = call.from_user.username or "بدون نام"
        
        # کمیسیون برای دعوت‌کننده
        inviter_id = users.get(user_id, {}).get('invited_by')
        if inviter_id:
            commission_amount = int(price * REFERRAL_COMMISSION)
            users[inviter_id]['commission'] = users[inviter_id].get('commission', 0) + commission_amount
            save_users(users)
            bot.send_message(
                int(inviter_id),
                f"💎 **کمیسیون جدید!**\n\n"
                f"👤 کاربر: @{username}\n"
                f"📦 بسته: {package}\n"
                f"💰 مبلغ: {price:,} تومان\n"
                f"💸 کمیسیون (۱۰%): {commission_amount:,} تومان\n"
                f"📊 کل: {users[inviter_id].get('commission', 0):,} تومان"
            )
        
        admin_text = f"📸 **درخواست کانفیگ!**\n👤 @{username}\n🆔 {user_id}\n📦 {package}\n💰 {price:,}"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{user_id}_{package}_{price}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"no_{user_id}"),
            types.InlineKeyboardButton("✏️ ارسال دستی", callback_data=f"send_{user_id}_{package}_{price}")
        )
        bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
        bot.send_message(int(user_id), f"✅ درخواست خرید {package} ثبت شد. منتظر تایید ادمین باشید.")
        bot.answer_callback_query(call.id, "✅ ثبت شد")
    else:
        need = price - credit
        bot.send_message(int(user_id), f"❌ اعتبار کافی نیست!\n💰 اعتبار: {credit:,} تومان\n💸 نیاز: {need:,} تومان\n\n💳 از منوی اصلی روی شارژ کیف پول کلیک کن.")
        bot.answer_callback_query(call.id, "❌ اعتبار")

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

# ======================== دکمه‌های ادمین برای کانفیگ ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def confirm_config(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    _, user_id, package, price = call.data.split("_")
    bot.send_message(int(user_id), f"✅ کانفیگ {package} تایید شد!\n🆔 پشتیبانی: @hegzosupport")
    bot.answer_callback_query(call.id, "✅ تایید شد")
    try:
        bot.edit_message_caption(f"✅ تایید شد - {package}", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def reject_config(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    user_id = call.data.split("_")[1]
    bot.send_message(int(user_id), "❌ درخواست شما رد شد! با پشتیبانی تماس بگیرید: @hegzosupport")
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
    _, user_id, package, price = call.data.split("_")
    bot.send_message(call.message.chat.id, f"📝 لطفاً کانفیگ {package} رو برای کاربر {user_id} بفرستید:")
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
    bot.send_message(int(user_id), f"🎁 کانفیگ {package} شما:\n\n`{config}`\n\n🆔 پشتیبانی: @hegzosupport", parse_mode='Markdown')
    bot.reply_to(m, "✅ کانفیگ ارسال شد")

# ======================== کانفیگ‌های من ========================
@bot.message_handler(func=lambda m: m.text == "📁 کانفیگ‌های من")
@membership_required
def my_configs(m):
    user_id = str(m.from_user.id)
    data = users.get(user_id, {})
    configs = data.get('active_configs', [])
    if not configs:
        bot.reply_to(m, "📭 شما هیچ کانفیگ فعالی ندارید!\n\nبرای خرید کانفیگ از بخش 🛒 خرید کانفیگ اقدام کنید.", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(configs):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    
    bot.reply_to(m, "📦 **لیست کانفیگ‌های فعال شما**\n\nلطفاً یکی را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("showcfg_"))
def show_config_detail(call):
    user_id = str(call.from_user.id)
    idx = int(call.data.split("_")[1])
    data = users.get(user_id, {})
    configs = data.get('active_configs', [])
    
    if idx >= len(configs):
        bot.answer_callback_query(call.id, "❌ کانفیگ مورد نظر یافت نشد!", show_alert=True)
        return
    
    cfg = configs[idx]
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
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="back_to_configs"))
    markup.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_configs")
def back_to_configs(call):
    user_id = str(call.from_user.id)
    data = users.get(user_id, {})
    configs = data.get('active_configs', [])
    
    if not configs:
        try:
            bot.edit_message_text("📭 کانفیگ فعالی ندارید!", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, "📭 کانفیگ فعالی ندارید!", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cfg in enumerate(configs):
        package = cfg.get('package', 'نامشخص')
        date = cfg.get('date', 'نامشخص')[:10]
        markup.add(types.InlineKeyboardButton(f"{i+1}. {package} ({date})", callback_data=f"showcfg_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    
    try:
        bot.edit_message_text("📦 **لیست کانفیگ‌های فعال شما**\n\nلطفاً یکی را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "📦 **لیست کانفیگ‌های فعال شما**\n\nلطفاً یکی را انتخاب کنید:", reply_markup=markup, parse_mode='Markdown')

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
        types.InlineKeyboardButton("✅ تایید شارژ", callback_data=f"ch_ok_{user_id}_{pending}"),
        types.InlineKeyboardButton("❌ رد شارژ", callback_data=f"ch_no_{user_id}")
    )
    
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=caption, reply_markup=markup)
    bot.reply_to(m, "✅ رسید شما دریافت شد. در حال بررسی توسط ادمین...")
    
    users[user_id]['pending_charge'] = 0
    save_users(users)

# ======================== دکمه‌های ادمین برای شارژ ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_ok_"))
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_no_"))
def reject_charge(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    user_id = call.data.split("_")[2]
    
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
        text += f"🆔 `{uid}` | @{username} | اعتبار: {data.get('credit',0):,} | دعوت: {data.get('referrals',0)} | کمیسیون: {data.get('commission',0):,}\n"
    bot.reply_to(m, text, parse_mode='Markdown')

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
            bot.send_message(int(uid), f"📢 **پیام از ادمین هگزو وی‌پی‌ان**\n\n{m.text}", parse_mode='Markdown')
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
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
    bot.reply_to(m, "❌ لطفاً از دکمه‌های منوی اصلی استفاده کنید.", reply_markup=main_keyboard())

# ======================== اجرا ========================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"🤖 Hegzo VPN روی پورت {PORT} روشن شد!")
    print("✅ همه‌ی بخش‌های کانفیگ (اینفلوئنسر، عادی، گیمینگ، VIP، مولتی) فعال شد!")
    print("✅ سیستم دعوت اینفلوئنسری با کمیسیون ۱۰% فعال شد!")
    print("✅ دکمه‌های ادمین برای تایید/رد کانفیگ و شارژ فعال شد!")
    print("✅ دستورات ادمین (users, broadcast, ban, unban, banned) فعال شد!")

    bot.delete_webhook()
    time.sleep(2)

    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()

    bot.infinity_polling()
