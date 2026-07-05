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
CARD_NAME = ' خزایی'
MIN_CHARGE = 200000
REFERRAL_AMOUNT = 5000

# ======================== وضعیت شارژ ========================
wallet_enabled = True

# ======================== اتصال به Supabase ========================
SUPABASE_URL = "https://fyflqsxodxpwhrfvnmex.supabase.co"
SUPABASE_KEY = "sb_publishable_uKV9HhKzCSuVvR_q7Ei95g_LR8q9Icx"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================== توابع دیتابیس (اصلاح شده) ========================
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
                'referral_code': row.get('referral_code', str(row['user_id']))
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
                "referral_code": data.get('referral_code', str(user_id))
            }).execute()
    except Exception as e:
        print(f"❌ خطا در سیو کاربران: {e}")

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
            'referral_code': str(user_id)
        }
        save_users(users)

def generate_referral_code(user_id):
    return str(user_id)

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
    markup.add("👥 دعوت از دوستان", "🆘 پشتیبانی")
    markup.add("🏠 منوی اصلی")
    return markup

def buy_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⭐ اینفلوئنسر", callback_data="lev_influencer"))
    markup.add(types.InlineKeyboardButton("🌐 گشت‌وگذار", callback_data="lev_normal"))
    markup.add(types.InlineKeyboardButton("🎮 گیمینگ", callback_data="lev_gaming"))
    markup.add(types.InlineKeyboardButton("👑 VIP", callback_data="lev_vip"))
    markup.add(types.InlineKeyboardButton("🌍 مولتی", callback_data="lev_multi"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return markup

def influencer_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - تک ۵۹۰,۰۰۰", callback_data="b_influencer100_590000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۲ کاربره ۷۹۰,۰۰۰", callback_data="b_influencer100_790000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۳ کاربره ۹۹۰,۰۰۰", callback_data="b_influencer100_990000"))
    markup.add(types.InlineKeyboardButton("🎬 ۱۰۰ گیگ - ۳ ماهه تک ۱,۴۹۰,۰۰۰", callback_data="b_influencer100_1490000"))
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

# ======================== دستورات ادمین ========================
@bot.message_handler(commands=['walletoff'])
def wallet_off(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    global wallet_enabled
    wallet_enabled = False
    bot.reply_to(m, "✅ شارژ کیف پول **غیرفعال** شد.")

@bot.message_handler(commands=['walleton'])
def wallet_on(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    global wallet_enabled
    wallet_enabled = True
    bot.reply_to(m, "✅ شارژ کیف پول **فعال** شد.")

# ======================== دستورات اصلی ========================
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
    
    # ======================== سیستم رفرال ========================
    if len(message.text.split()) > 1:
        try:
            ref_param = message.text.split()[1]
            
            if users.get(str(user_id), {}).get('invited_by') is None:
                inviter_id = None
                
                # بررسی با آیدی
                try:
                    ref_int = int(ref_param)
                    if str(ref_int) in users and str(ref_int) != str(user_id):
                        inviter_id = str(ref_int)
                except:
                    pass
                
                # بررسی با کد دعوت
                if inviter_id is None:
                    for uid, data in users.items():
                        if data.get('referral_code', '').lower() == ref_param.lower():
                            if uid != str(user_id):
                                inviter_id = uid
                                break
                
                if inviter_id:
                    users[str(user_id)]['invited_by'] = inviter_id
                    users[inviter_id]['referrals'] = users[inviter_id].get('referrals', 0) + 1
                    users[inviter_id]['credit'] = users[inviter_id].get('credit', 0) + REFERRAL_AMOUNT
                    save_users(users)
                    
                    try:
                        bot.send_message(
                            int(inviter_id),
                            f"🎉 یک کاربر جدید با کد شما عضو شد!\n\n"
                            f"👤 {message.from_user.first_name}\n"
                            f"💰 {REFERRAL_AMOUNT:,} تومان به حسابت اضافه شد!"
                        )
                    except:
                        pass
                    
                    bot.reply_to(
                        message,
                        f"✅ شما با کد دعوت عضو شدید!\n"
                        f"🎁 دعوت‌کننده شما {REFERRAL_AMOUNT:,} تومان پاداش گرفت."
                    )
        except Exception as e:
            print(f"❌ خطا در رفرال: {e}")
    
    bot.reply_to(
        message,
        f"🔥 **به هگزو وی‌پی‌ان خوش اومدی** {name}! 🎉\n\n"
        f"⚡ اینترنت آزاد و بدون محدودیت\n"
        f"🛡️ امنیت کامل و سرعت بالا\n"
        f"✨ از منوی زیر یکی رو انتخاب کن:", 
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

@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
@membership_required
def charge_menu(m):
    global wallet_enabled
    if not wallet_enabled:
        bot.reply_to(m, "⛔ **این بخش در حال حاضر غیرفعال است.**\n\nلطفاً بعداً مراجعه کنید.", parse_mode='Markdown')
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
    bot.send_message(
        call.message.chat.id,
        f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n📸 لطفاً عکس رسید را بفرستید:"
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def process_custom_charge(m):
    user_id = str(m.from_user.id)
    
    raw_text = m.text.strip()
    
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
    }
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
        bot.reply_to(m, "❌ عدد معتبر نیست. دوباره تلاش کن (مثال: 200000):")
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
        bot.reply_to(m, "❌ شما هیچ درخواست شارژ فعالی ندارید. ابتدا از منو مبلغ را وارد کنید.", reply_markup=main_keyboard())
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
    
    try:
        bot.edit_message_caption("✅ تایید شد", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_no_"))
def reject_charge(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    parts = call.data.split("_")
    user_id = parts[2]
    
    bot.send_message(int(user_id), "❌ درخواست شارژ شما رد شد. لطفاً با پشتیبانی تماس بگیرید: @hegzosupport")
    bot.answer_callback_query(call.id, "❌ رد شد")
    
    try:
        bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)
    except:
        pass

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
        "lev_multi": "🌍 مولتی"
    }
    try:
        bot.edit_message_text(f"{titles[call.data]}\n\nلطفاً بسته مورد نظر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=menus[call.data](), parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, f"{titles[call.data]}\n\nلطفاً بسته مورد نظر را انتخاب کنید:", reply_markup=menus[call.data](), parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("b_"))
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
    
    credit = users[user_id].get('credit', 0)
    if credit >= price:
        users[user_id]['credit'] = credit - price
        save_users(users)
        username = call.from_user.username or "بدون نام"
        
        admin_text = f"📸 درخواست کانفیگ!\n👤 @{username}\n🆔 {user_id}\n📦 {package}\n💰 {price:,} تومان"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{user_id}_{package}_{price}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"no_{user_id}"),
            types.InlineKeyboardButton("✏️ ارسال دستی", callback_data=f"send_{user_id}_{package}_{price}")
        )
        bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
        bot.send_message(int(user_id), f"✅ درخواست خرید {package} ثبت شد.")
        bot.answer_callback_query(call.id, "✅ ثبت شد")
    else:
        bot.send_message(int(user_id), f"❌ اعتبار کافی نیست!\n💰 اعتبار: {credit:,} تومان")
        bot.answer_callback_query(call.id, "❌ اعتبار")

@bot.callback_query_handler(func=lambda call: call.data == "back_buy")
def back_buy(call):
    try:
        bot.edit_message_text("📊 انتخاب نوع سرویس:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())
    except:
        bot.send_message(call.message.chat.id, "📊 انتخاب نوع سرویس:", reply_markup=buy_menu())
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
    bot.reply_to(m, f"👤 حساب کاربری\n💰 اعتبار: {data.get('credit', 0):,}\n📁 کانفیگ: {len(data.get('active_configs', []))}\n👥 دعوت: {data.get('referrals', 0)}")

@bot.message_handler(func=lambda m: m.text == "👥 دعوت از دوستان")
@membership_required
def invite(m):
    user_id = str(m.from_user.id)
    data = users.get(user_id, {})
    referral_code = data.get('referral_code', user_id)
    bot_username = bot.get_me().username
    
    invite_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    text = f"""🔥 **سیستم دعوت از دوستان**

👤 کد دعوت شما: `{referral_code}`
🔗 لینک دعوت: `{invite_link}`

📌 **طرز استفاده:**
۱. لینک بالا رو برای دوستانت بفرست
۲. هر کسی با لینک شما وارد ربات بشه
۳. شما {REFERRAL_AMOUNT:,} تومان پاداش میگیری

👥 تعداد دعوت‌های شما: {data.get('referrals', 0)} نفر
💰 پاداش دریافتی: {data.get('referrals', 0) * REFERRAL_AMOUNT:,} تومان

⚡ هرچه دوستان بیشتری دعوت کنی، پاداش بیشتری میگیری!"""
    
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
@membership_requireddef support(m):
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
        text += f"🆔 {uid} | @{data.get('username', '')} | اعتبار: {data.get('credit',0):,} | دعوت: {data.get('referrals',0)}\n"
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
    print(f"🤖 Hegzo VPN روشن شد!")
    print("✅ همه چیز آماده است!")

    bot.delete_webhook()
    time.sleep(2)

    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()

    bot.infinity_polling()
