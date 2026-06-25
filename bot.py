import telebot, os, time, json, threading
from telebot import types
from datetime import datetime
import pymongo
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "Hegzo VPN is running!", 200

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN: raise ValueError("BOT_TOKEN is missing")

MONGO_URI = "mongodb+srv://rtx_user:rtx123456@cluster0.sjyebyr.mongodb.net/?appName=Cluster0"
ADMIN_ID = '6795169616'
CHANNEL_USERNAME = '@hegzo_vpn_channle'
CARD_NUMBER = '5022291525516892'
CARD_NAME = 'احمد خزایی'
REFERRAL_AMOUNT = 5000

client = pymongo.MongoClient(MONGO_URI, maxPoolSize=10, connectTimeoutMS=5000)
db = client['hegzo_bot']
users_col = db['users']
banned_col = db['banned_users']

def get_user(uid): return users_col.find_one({'_id': str(uid)})
def set_user(uid, data): users_col.update_one({'_id': str(uid)}, {'$set': data}, upsert=True)
def get_all(): return list(users_col.find())
def get_banned():
    d = banned_col.find_one({'_id': 'banned'})
    return set(d.get('list', [])) if d else set()
def set_banned(b): banned_col.update_one({'_id': 'banned'}, {'$set': {'list': list(b)}}, upsert=True)
def init_user(uid, name=''):
    if not get_user(uid):
        set_user(uid, {
            'username': name, 'credit': 0, 'active_configs': [],
            'pending_charge': 0, 'invited_by': None, 'referrals': 0,
            'joined_at': str(datetime.now())
        })
def is_banned(uid): return str(uid) in get_banned()

bot = telebot.TeleBot(TOKEN)

def is_member(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("💳 شارژ کیف پول", "🛒 خرید کانفیگ")
    kb.add("📁 کانفیگ‌های من", "👤 حساب کاربری")
    kb.add("👥 دعوت از دوستان", "🆘 پشتیبانی")
    kb.add("🏠 منوی اصلی")
    return kb

def admin_btns(uid, pkg, price):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"ok_{uid}_{pkg}_{price}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"no_{uid}"),
        types.InlineKeyboardButton("✏️ ارسال دستی", callback_data=f"send_{uid}_{pkg}_{price}")
    )
    return kb

def charge_btns(uid, amt):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ تایید شارژ", callback_data=f"ch_ok_{uid}_{amt}"),
        types.InlineKeyboardButton("❌ رد شارژ", callback_data=f"ch_no_{uid}")
    )
    return kb

def buy_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("💰 اقتصادی", callback_data="lev_eco"))
    kb.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 خانواده (غیرفعال)", callback_data="lev_family"))
    kb.add(types.InlineKeyboardButton("🎮 گیمینگ (غیرفعال)", callback_data="lev_gaming"))
    kb.add(types.InlineKeyboardButton("💎 VIP (غیرفعال)", callback_data="lev_vip"))
    kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return kb

def eco_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("25 گیگ - 180,000 تومان", callback_data="b_eco25_180000"))
    kb.add(types.InlineKeyboardButton("50 گیگ - 250,000 تومان", callback_data="b_eco50_250000"))
    kb.add(types.InlineKeyboardButton("100 گیگ - 450,000 تومان", callback_data="b_eco100_450000"))
    kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return kb

def family_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("100 گیگ - 750,000 تومان (غیرفعال)", callback_data="family_inactive"))
    kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return kb

def gaming_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("500 گیگ - 1,200,000 تومان (غیرفعال)", callback_data="gaming_inactive"))
    kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return kb

def vip_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("50 گیگ - 300,000 تومان (غیرفعال)", callback_data="vip_inactive"))
    kb.add(types.InlineKeyboardButton("100 گیگ - 500,000 تومان (غیرفعال)", callback_data="vip_inactive"))
    kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_buy"))
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    if is_banned(uid): return bot.reply_to(m, "⛔ شما بن شدید!")
    name = m.from_user.first_name
    init_user(uid, m.from_user.username or "")
    if len(m.text.split()) > 1:
        try:
            ref = int(m.text.split()[1])
            if ref != uid:
                u = get_user(str(ref))
                if u and not get_user(str(uid)).get('invited_by'):
                    set_user(str(ref), {'referrals': u.get('referrals', 0)+1, 'credit': u.get('credit', 0)+REFERRAL_AMOUNT})
                    set_user(str(uid), {'invited_by': ref})
                    bot.send_message(ref, "🎉 کاربر جدید آوردی!")
        except: pass
    if not is_member(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔗 عضویت", url="https://t.me/hegzo_vpn_channle"))
        return bot.reply_to(m, "❌ عضو کانال شو!", reply_markup=kb)
    bot.reply_to(m, f"🔥 خوش اومدی {name}!", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "🏠 منوی اصلی")
def back_home(m): bot.reply_to(m, "🔥 منوی اصلی:", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "🛒 خرید کانفیگ")
def show_buy(m): bot.reply_to(m, "📊 انتخاب سرویس:", reply_markup=buy_menu())

@bot.message_handler(func=lambda m: m.text == "👤 حساب کاربری")
def profile(m):
    uid = m.from_user.id
    d = get_user(str(uid)) or {}
    bot.reply_to(m, f"👤 **کاربری**\n🆔 {uid}\n💰 اعتبار: {d.get('credit',0):,}\n📁 کانفیگ: {len(d.get('active_configs',[]))}\n👥 دعوت: {d.get('referrals',0)}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "👥 دعوت از دوستان")
def invite(m):
    uid = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    d = get_user(str(uid)) or {}
    bot.reply_to(m, f"🔥 لینک دعوت:\n`{link}`\n👥 {d.get('referrals',0)} دعوت", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support(m): bot.reply_to(m, "🆔 پشتیبانی: @bintc\n۲۴ ساعته")

@bot.message_handler(func=lambda m: m.text == "💳 شارژ کیف پول")
def charge(m):
    bot.reply_to(m, f"💳 شماره کارت: `{CARD_NUMBER}`\n🏦 {CARD_NAME}\nمبلغ رو وارد کن:", parse_mode='Markdown')
    bot.register_next_step_handler(m, get_amount)

def get_amount(m):
    try:
        amt = int(m.text)
        if amt < 200000: return bot.reply_to(m, "❌ حداقل ۲۰۰,۰۰۰ تومان")
        set_user(str(m.from_user.id), {'pending_charge': amt})
        bot.reply_to(m, f"✅ {amt:,} ثبت شد. رسید رو بفرست.")
    except: bot.reply_to(m, "❌ عدد معتبر وارد کن")

@bot.message_handler(content_types=['photo'])
def receipt(m):
    uid = m.from_user.id
    d = get_user(str(uid))
    pending = d.get('pending_charge', 0) if d else 0
    if pending:
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id,
                       caption=f"💰 شارژ\n👤 @{m.from_user.username or 'no'}\n🆔 {uid}\n💸 {pending:,}",
                       reply_markup=charge_btns(uid, pending))
        set_user(str(uid), {'pending_charge': 0})
        bot.reply_to(m, "✅ رسید دریافت شد، منتظر تایید ادمین.")
    else: bot.reply_to(m, "❌ اول شارژ رو شروع کن.")

@bot.message_handler(func=lambda m: m.text == "📁 کانفیگ‌های من")
def my_cfgs(m):
    uid = m.from_user.id
    d = get_user(str(uid)) or {}
    cfgs = d.get('active_configs', [])
    if not cfgs: return bot.reply_to(m, "📭 کانفیگی نداری!")
    kb = types.InlineKeyboardMarkup(row_width=1)
    for i, c in enumerate(cfgs):
        kb.add(types.InlineKeyboardButton(f"{i+1}. {c.get('package','')}", callback_data=f"showcfg_{i}"))
    kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    bot.reply_to(m, "📦 لیست کانفیگ‌ها:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("showcfg_"))
def show_cfg(call):
    uid = call.from_user.id
    idx = int(call.data.split("_")[1])
    d = get_user(str(uid)) or {}
    cfgs = d.get('active_configs', [])
    if idx >= len(cfgs): return bot.answer_callback_query(call.id, "❌ یافت نشد")
    c = cfgs[idx]
    bot.send_message(uid, f"📦 {c.get('package','')}\n🔗 `{c.get('config','')}`\n💰 {c.get('price',0):,}", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def confirm(call):
    if str(call.from_user.id) != ADMIN_ID: return bot.answer_callback_query(call.id, "⛔ ادمین فقط")
    _, uid, pkg, price = call.data.split("_")
    bot.send_message(int(uid), f"✅ کانفیگ {pkg} تایید شد!")
    bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def reject(call):
    if str(call.from_user.id) != ADMIN_ID: return bot.answer_callback_query(call.id, "⛔ ادمین فقط")
    uid = call.data.split("_")[1]
    bot.send_message(int(uid), "❌ درخواست رد شد!")
    bot.answer_callback_query(call.id, "❌ رد شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def manual(call):
    if str(call.from_user.id) != ADMIN_ID: return bot.answer_callback_query(call.id, "⛔ ادمین فقط")
    _, uid, pkg, price = call.data.split("_")
    bot.send_message(call.message.chat.id, f"📝 کانفیگ {pkg} رو بفرست:")
    bot.register_next_step_handler(call.message, lambda m: send_cfg(m, uid, pkg, price))
    bot.answer_callback_query(call.id)

def send_cfg(m, uid, pkg, price):
    cfg = m.text
    d = get_user(str(uid)) or {}
    l = d.get('active_configs', [])
    l.append({'package': pkg, 'config': cfg, 'date': str(datetime.now()), 'price': int(price)})
    set_user(str(uid), {'active_configs': l})
    bot.send_message(int(uid), f"🎁 کانفیگ {pkg}:\n`{cfg}`")
    bot.reply_to(m, "✅ ارسال شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_ok_"))
def ch_ok(call):
    if str(call.from_user.id) != ADMIN_ID: return bot.answer_callback_query(call.id, "⛔ ادمین فقط")
    _, _, uid, amt = call.data.split("_")
    d = get_user(str(uid)) or {}
    set_user(str(uid), {'credit': d.get('credit', 0) + int(amt)})
    bot.send_message(int(uid), f"✅ {int(amt):,} شارژ شد!")
    bot.answer_callback_query(call.id, "✅ تایید شارژ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_no_"))
def ch_no(call):
    if str(call.from_user.id) != ADMIN_ID: return bot.answer_callback_query(call.id, "⛔ ادمین فقط")
    uid = call.data.split("_")[2]
    bot.send_message(int(uid), "❌ شارژ رد شد!")
    bot.answer_callback_query(call.id, "❌ رد شارژ")

@bot.callback_query_handler(func=lambda call: call.data in ["lev_family", "lev_gaming", "lev_vip"])
def inactive(call):
    bot.answer_callback_query(call.id, "⛔ غیرفعال", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "lev_eco")
def lev_eco(call):
    bot.edit_message_text("💰 اقتصادی:", call.message.chat.id, call.message.message_id, reply_markup=eco_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_buy")
def back_buy(call):
    bot.edit_message_text("📊 انتخاب سرویس:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    bot.edit_message_text("🔥 منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=main_kb())

@bot.callback_query_handler(func=lambda call: call.data.startswith("b_"))
def buy(call):
    uid = call.from_user.id
    if is_banned(uid): return bot.answer_callback_query(call.id, "⛔ بن")
    pkg = "_".join(call.data.split("_")[1:-1])
    price = int(call.data.split("_")[-1])
    d = get_user(str(uid)) or {}
    if d.get('credit', 0) >= price:
        set_user(str(uid), {'credit': d.get('credit', 0) - price})
        bot.send_message(ADMIN_ID, f"📸 درخواست {pkg}\n👤 @{call.from_user.username or 'no'}\n🆔 {uid}\n💰 {price:,}", reply_markup=admin_btns(uid, pkg, price))
        bot.send_message(uid, "✅ ثبت شد، منتظر تایید.")
        bot.answer_callback_query(call.id, "✅ ثبت")
    else:
        bot.send_message(uid, f"❌ اعتبار کافی! نیاز: {price - d.get('credit', 0):,}")
        bot.answer_callback_query(call.id, "❌ اعتبار")

@bot.message_handler(commands=['users'])
def list_users(m):
    if str(m.from_user.id) != ADMIN_ID: return
    users = get_all()
    if not users: return bot.reply_to(m, "📭 هیچ کاربری")
    txt = "📊 لیست کاربران:\n"
    for u in users: txt += f"🆔 {u.get('_id')} | اعتبار: {u.get('credit',0):,}\n"
    bot.reply_to(m, txt)

@bot.message_handler(commands=['broadcast'])
def bc(m):
    if str(m.from_user.id) != ADMIN_ID: return
    bot.reply_to(m, "📢 پیام رو بفرست:")
    bot.register_next_step_handler(m, do_bc)

def do_bc(m):
    if str(m.from_user.id) != ADMIN_ID: return
    for u in get_all():
        try:
            bot.send_message(int(u.get('_id')), f"📢 {m.text}")
            time.sleep(0.05)
        except: pass
    bot.reply_to(m, "✅ ارسال شد")

@bot.message_handler(commands=['ban', 'unban'])
def ban_unban(m):
    if str(m.from_user.id) != ADMIN_ID: return
    try:
        uid = int(m.text.split()[1])
        banned = get_banned()
        if m.text.startswith('/ban'):
            banned.add(str(uid)); set_banned(banned); bot.reply_to(m, f"✅ {uid} بن شد")
        else:
            banned.discard(str(uid)); set_banned(banned); bot.reply_to(m, f"✅ {uid} آنبن شد")
    except: bot.reply_to(m, "❌ /ban [id]")

@bot.message_handler(func=lambda m: True)
def unknown(m):
    if is_banned(m.from_user.id): return bot.reply_to(m, "⛔ بن")
    bot.reply_to(m, "❌ از دکمه‌ها استفاده کن", reply_markup=main_kb())

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 10000))
    bot.delete_webhook()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    print("🤖 Hegzo VPN روشن شد!")
    bot.infinity_polling(timeout=15, long_polling_timeout=15)
