import telebot
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("MY_SECRET_KEY")
# Gọi localhost vì chạy cùng VPS
API_URL = "http://localhost:3636/search"

if not BOT_TOKEN:
    print("❌ Thiếu TELEGRAM_BOT_TOKEN")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Tao là bot tìm sẽ. Gõ tên diễn viên vào đây.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    actor = message.text.strip()
    bot.reply_to(message, f"🔍 Đang tìm '{actor}', chờ tí...")

    try:
        headers = {"x-api-key": API_KEY}
        resp = requests.get(API_URL, params={"q": actor}, headers=headers, timeout=120)
        
        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", 0)
            
            if count == 0:
                bot.reply_to(message, "❌ Đéo tìm thấy.")
            else:
                msg = f"✅ <b>Tìm thấy {count} video!</b> (Nguồn: {data.get('source')})\n\n"
                for item in data.get("results", [])[:15]:
                    t = item.get("title", "").replace("<","&lt;").replace(">","&gt;")
                    l = item.get("link", "")
                    s = item.get("source", "")
                    msg += f"🎬 <b>[{s}]</b> <a href='{l}'>{t}</a>\n\n"
                
                if count > 15: msg += f"<i>... và {count - 15} cái nữa.</i>"
                bot.reply_to(message, msg, parse_mode="HTML")
        else:
            bot.reply_to(message, f"🔥 Lỗi API: {resp.status_code}")
    except Exception as e:
        bot.reply_to(message, f"☠️ Lỗi Bot: {e}")

print("Bot đang chạy...")
bot.infinity_polling()