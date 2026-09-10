import os
import json
import time
import random
import hashlib
import logging
import threading
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from flask import Flask, request
import telebot
from telebot import types

# ==================== CẤU HÌNH ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8385677064:AAHS5ZqmV9QPka3I1t84lyysLzLsLTp3N6g")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "7564889663").split(",")]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://betok.onrender.com/webhook")
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ==================== QUẢN LÝ KEY ====================
KEYS_FILE = "xworld_keys.json"
user_keys = {}

def load_keys():
    global user_keys
    try:
        with open(KEYS_FILE, 'r') as f:
            user_keys = json.load(f)
    except:
        user_keys = {}

def save_keys():
    try:
        with open(KEYS_FILE, 'w') as f:
            json.dump(user_keys, f, indent=2)
    except:
        pass

load_keys()

def generate_key(days: int) -> str:
    raw = f"{datetime.now().isoformat()}:{random.randint(1000000, 9999999)}"
    key = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    user_keys[key] = {
        "created": datetime.now().isoformat(),
        "expiry": expiry,
        "days": days,
        "used_by": []
    }
    save_keys()
    return key

def verify_key(key: str, user_id: int) -> bool:
    if key not in user_keys:
        return False
    data = user_keys[key]
    expiry = datetime.fromisoformat(data["expiry"])
    if datetime.now() > expiry:
        return False
    if str(user_id) not in data["used_by"]:
        data["used_by"].append(str(user_id))
        save_keys()
    return True

def get_key_info(key: str):
    if key not in user_keys:
        return None
    data = user_keys[key]
    expiry = datetime.fromisoformat(data["expiry"])
    remaining = (expiry - datetime.now()).days
    return {
        "key": key,
        "expiry": data["expiry"],
        "days": data["days"],
        "remaining": remaining,
        "used_by": data["used_by"]
    }

# ==================== TOOL XWORLD ====================
def parse_escape_link(url):
    if not isinstance(url, str):
        return None, "URL phải là chuỗi"
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        user_ids = query.get("userId") or query.get("userid") or query.get("user_id")
        secret_keys = query.get("secretKey") or query.get("secretkey") or query.get("secret_key")
        if not user_ids:
            return None, "Không tìm thấy userId trong link"
        if not secret_keys:
            return None, "Không tìm thấy secretKey trong link"
        user_id = user_ids[0]
        secret_key = secret_keys[0]
        if not user_id.isdigit():
            return None, f"userId không hợp lệ: {user_id}"
        if len(secret_key) < 10:
            return None, f"secretKey không hợp lệ"
        return {"user_id": user_id, "secret_key": secret_key}, None
    except Exception as e:
        return None, str(e)

def send_xworld_payload(user_id, secret_key):
    data = {
        "user_id": user_id,
        "data": {
            "user_id": user_id,
            "slots": [{"level": 37, "pos": i} for i in range(13)],
            "items": [{"level": i, "coin_cnt": c} for i, c in [
                (1, 2), (2, 1000), (3, 1393), (4, 939), (5, 339),
                (6, 8393), (7, 58383), (8, 94932), (9, 13838),
                (10, 6), (11, 8), (12, 7), (13, 10), (14, 12),
                (15, 10), (16, 21), (17, 16), (18, 13), (19, 15),
                (20, 19), (21, 17), (22, 21), (23, 23), (24, 20),
                (25, 26), (26, 24), (27, 29), (28, 27), (29, 31),
                (30, 3), (31, 0), (32, 0), (33, 37), (34, 0),
                (35, 0), (36, 0), (37, 0)
            ]],
            "coin": "3773876377738282998892124540909988",
            "history_coin": "88737383283773763777382829988921245406709988",
            "max_level": 37,
            "backup_utc": time.time()
        },
        "ts": time.time()
    }

    headers = {
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Content-Type": "application/json",
        "user-secret-key": str(secret_key),
        "user-id": str(user_id),
        "country-code": "vn",
        "platform": "h5",
        "origin": "https://xworld.info",
        "referer": "https://xworld.info/",
        "accept-language": "vi-VN,vi;q=0.9",
        "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"
    }

    try:
        resp = requests.post(
            'https://mpet3.3games.io/api/mpet/store_mpet_data',
            headers=headers, json=data, timeout=15
        )
        return resp.status_code, resp.text
    except Exception as e:
        return 0, str(e)

# ==================== MENU ====================
def main_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🚀 Hack Pet", callback_data='hack'),
        types.InlineKeyboardButton("📊 Thông tin", callback_data='info'),
    )
    keyboard.add(
        types.InlineKeyboardButton("👑 Admin Panel", callback_data='admin'),
    )
    return keyboard

def admin_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🔑 Key 1 ngày", callback_data='key_1'),
        types.InlineKeyboardButton("🔑 Key 7 ngày", callback_data='key_7'),
        types.InlineKeyboardButton("🔑 Key 30 ngày", callback_data='key_30'),
    )
    keyboard.add(
        types.InlineKeyboardButton("📋 DS Key", callback_data='list_keys'),
        types.InlineKeyboardButton("🔍 Check Key", callback_data='check_key'),
    )
    keyboard.add(
        types.InlineKeyboardButton("⬅️ Menu", callback_data='menu'),
    )
    return keyboard

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.chat.id
    
    if user_id in ADMIN_IDS:
        bot.send_message(user_id, f"""
👑 *XWORLD HACK BOT - ADMIN*
━━━━━━━━━━━━━━━━━━━
👤 Admin: `{user_id}`
📊 Tổng key: `{len(user_keys)}`
━━━━━━━━━━━━━━━━━━━
📌 Chọn chức năng:
""", reply_markup=main_menu(), parse_mode='Markdown')
        return

    bot.send_message(user_id, f"""
🔒 *XWORLD HACK BOT*
━━━━━━━━━━━━━━━━━━━
📌 *Nhập Key để kích hoạt:*
`/key <MÃ_KEY>`

🔑 Mua Key: liên hệ admin
━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')

@bot.message_handler(commands=['key'])
def cmd_key(message):
    user_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Nhập: `/key <MÃ_KEY>`", parse_mode='Markdown')
        return

    key = parts[1].strip().upper()
    if verify_key(key, user_id):
        info = get_key_info(key)
        bot.reply_to(message, f"""
✅ *KÍCH HOẠT THÀNH CÔNG!*
━━━━━━━━━━━━━━━━━━━
🔑 Key: `{key}`
⏳ Hạn: {info['remaining']} ngày
📅 Hết hạn: {info['expiry'][:10]}
━━━━━━━━━━━━━━━━━━━
📌 Bấm /start để bắt đầu!
""", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Key không hợp lệ hoặc đã hết hạn!")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == 'menu':
        bot.send_message(user_id, "🏠 *MENU CHÍNH*", reply_markup=main_menu(), parse_mode='Markdown')

    elif data == 'hack':
        msg = bot.send_message(user_id, """
🚀 *HACK PET XWORLD*
━━━━━━━━━━━━━━━━━━━
📌 Dán link game có dạng:
`https://xworld.info/?userId=xxx&secretKey=yyy`
━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_hack)

    elif data == 'info':
        bot.send_message(user_id, f"""
📊 *THÔNG TIN*
━━━━━━━━━━━━━━━━━━━
🤖 Bot: XWorld Hack
👤 User ID: `{user_id}`
📌 Chức năng: Hack pet level 37
━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown', reply_markup=main_menu())

    elif data == 'admin':
        if user_id not in ADMIN_IDS:
            bot.send_message(user_id, "❌ Không có quyền!")
            return
        bot.send_message(user_id, "👑 *ADMIN PANEL*", reply_markup=admin_menu(), parse_mode='Markdown')

    elif data.startswith('key_'):
        if user_id not in ADMIN_IDS:
            return
        days = int(data.replace('key_', ''))
        key = generate_key(days)
        info = get_key_info(key)
        bot.send_message(user_id, f"""
✅ *KEY ĐÃ TẠO*
━━━━━━━━━━━━━━━━━━━
🔑 Key: `{key}`
📅 Hạn: {days} ngày
⏳ Hết hạn: {info['expiry'][:10]}
━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown', reply_markup=admin_menu())

    elif data == 'list_keys':
        if user_id not in ADMIN_IDS:
            return
        if not user_keys:
            bot.send_message(user_id, "📭 Chưa có key nào!", reply_markup=admin_menu())
            return
        text = "📋 *DANH SÁCH KEY*\n━━━━━━━━━━━━━━━━━━━\n"
        for k, v in user_keys.items():
            expiry = datetime.fromisoformat(v["expiry"])
            remaining = (expiry - datetime.now()).days
            status = "🟢" if remaining > 0 else "🔴"
            text += f"{status} `{k}` | {v['days']}d | còn {remaining}d | {len(v['used_by'])} user\n"
        bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=admin_menu())

    elif data == 'check_key':
        if user_id not in ADMIN_IDS:
            return
        msg = bot.send_message(user_id, "📌 Nhập Key cần kiểm tra:")
        bot.register_next_step_handler(msg, process_check_key)

def process_hack(message):
    user_id = message.chat.id
    link = message.text.strip()

    parsed, err = parse_escape_link(link)
    if err:
        bot.reply_to(message, f"❌ Lỗi: {err}", reply_markup=main_menu())
        return

    msg = bot.reply_to(message, "⏳ Đang gửi payload lên server...")

    status, resp = send_xworld_payload(parsed['user_id'], parsed['secret_key'])

    try:
        data = json.loads(resp)
        code = data.get('code', 'N/A')
        msg_text = data.get('msg', data.get('message', 'N/A'))
    except:
        code = status
        msg_text = resp[:200]

    if code == 0:
        result = f"""
✅ *HACK THÀNH CÔNG!*
━━━━━━━━━━━━━━━━━━━
🆔 User ID: `{parsed['user_id']}`
📊 Code: `{code}`
💬 Msg: `{msg_text}`
━━━━━━━━━━━━━━━━━━━
📌 Vào game check pet!
"""
    else:
        result = f"""
❌ *HACK THẤT BẠI*
━━━━━━━━━━━━━━━━━━━
🆔 User ID: `{parsed['user_id']}`
📊 Code: `{code}`
💬 Msg: `{msg_text}`
━━━━━━━━━━━━━━━━━━━
"""

    bot.edit_message_text(result, chat_id=msg.chat.id, message_id=msg.message_id,
                          parse_mode='Markdown', reply_markup=main_menu())

def process_check_key(message):
    key = message.text.strip().upper()
    info = get_key_info(key)
    if info:
        status = "🟢 Còn hiệu lực" if info['remaining'] > 0 else "🔴 Hết hạn"
        bot.reply_to(message, f"""
🔍 *THÔNG TIN KEY*
━━━━━━━━━━━━━━━━━━━
🔑 Key: `{key}`
📅 Hạn: {info['days']} ngày
⏳ Còn: {info['remaining']} ngày
👥 Đã dùng: {len(info['used_by'])} user
📊 Trạng thái: {status}
━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown', reply_markup=admin_menu())
    else:
        bot.reply_to(message, "❌ Key không tồn tại!", reply_markup=admin_menu())

# ==================== WEBHOOK ====================
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "✅ Webhook working!", 200
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        try:
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return f"❌ Error: {e}", 500
    return '❌ Invalid', 403

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        return f"✅ Webhook set to {WEBHOOK_URL}", 200
    except Exception as e:
        return f"❌ Error: {e}", 500

@app.route('/', methods=['GET'])
def index():
    return "🤖 XWorld Hack Bot is running!", 200

# ==================== MAIN ====================
if __name__ == '__main__':
    print(f"🚀 XWorld Hack Bot đang chạy trên port {PORT}")
    print(f"👑 Admin IDs: {ADMIN_IDS}")
    print(f"🔗 Webhook: {WEBHOOK_URL}")
    app.run(host='0.0.0.0', port=PORT)
