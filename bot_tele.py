import telebot
import requests
import os
import re
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, select
from telebot.types import BotCommand
from typing import List

load_dotenv()

# --- CẤU HÌNH DB ---
sqlite_file_name = "videos_cache.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

# --- KHỞI TẠO BOT ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("MY_SECRET_KEY")
API_URL = "http://localhost:3636/search"

if not BOT_TOKEN:
    print("❌ Thiếu TELEGRAM_BOT_TOKEN")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# --- LOGIC CẬP NHẬT LỆNH ---
def update_bot_commands():
    commands: List[BotCommand] = []
    try:
        with Session(engine) as session:
            try:
                result = session.exec("SELECT DISTINCT search_query FROM videocache").all()
            except Exception as e: return
            
            if not result: return

            for row in result:
                actress_name = row[0] if isinstance(row, tuple) else row
                if not actress_name: continue
                
                command_name = re.sub(r'[^a-z0-9_]', '_', actress_name.lower())
                command_name = re.sub(r'_+', '_', command_name).strip('_')
                
                if command_name and len(command_name) < 32:
                    commands.append(BotCommand(command=command_name, description=actress_name.title()))

            if commands:
                final_commands = commands[:95] 
                final_commands.insert(0, BotCommand("start", "Khởi động bot"))
                bot.set_my_commands(final_commands)
                print(f"✅ Updated commands.")
            
    except Exception as e:
        print(f"❌ Error updating commands: {e}")

# --- HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(m):
    bot.reply_to(m, "Tao là bot tìm sẽ [Google AI]. Gõ tên diễn viên vào đây.")

@bot.message_handler(func=lambda m: m.text.startswith('/'))
def handle_command_search(m):
    actor_name = m.text[1:].replace('_', ' ')
    m.text = actor_name 
    handle_message(m)

@bot.message_handler(func=lambda m: True)
def handle_message(m):
    actor = m.text.strip()
    
    # FIX TÊN FILE
    actor_for_filename = re.sub(r'[^\w\s-]', '_', actor).replace('/', '').replace('\\', '').strip('_')
    actor_for_filename = re.sub(r'_+', '_', actor_for_filename)
    
    if not actor: return
        
    bot.reply_to(m, f"🔍 Đang tìm '{actor}', chờ tí...")

    try:
        headers = {"x-api-key": API_KEY}
        resp = requests.get(API_URL, params={"q": actor}, headers=headers, timeout=120)
        
        if resp.status_code == 200:
            data = resp.json()
            res = data.get("results", [])
            count = len(res)
            
            if count == 0:
                bot.reply_to(m, "❌ Đéo tìm thấy.")
            else:
                source_type = data.get('source', 'Unknown')
                actor_name_display = data.get('actor_name', actor)
                
                msg = f"✅ <b>Kết quả: {actor_name_display}</b>\n📊 Số lượng: {count} (Nguồn: {source_type})\n\n"
                for i in res[:10]:
                    t = i.get("title", "No Title").replace("<","&lt;").replace(">", "&gt;")
                    l = i.get("link", "#")
                    s = i.get("source", "Unknown")
                    msg += f"🎬 <b>[{s}]</b> <a href='{l}'>{t}</a>\n\n"
                bot.reply_to(m, msg, parse_mode="HTML")

                if "LIVE" in source_type:
                    try: update_bot_commands()
                    except: pass

                if count > 10:
                    content = f"KẾT QUẢ CHO: {actor_name_display}\nTỔNG: {count}\n\n"
                    for i in res: content += f"[{i.get('source')}] {i.get('title')}\nLink: {i.get('link')}\n---\n"
                    
                    filename = f"ket_qua_{actor_for_filename}.txt"
                    with open(filename, "w", encoding="utf-8-sig") as f:
                        f.write(content)
                    with open(filename, "rb") as f:
                        bot.send_document(m.chat.id, f, caption="📁 File full đây.")
                    os.remove(filename)

        else:
            bot.reply_to(m, f"🔥 Lỗi API: {resp.status_code}")
    except Exception as e:
        bot.reply_to(m, f"☠️ Lỗi Bot: {e}")

if __name__ == "__main__":
    update_bot_commands()
    print("Bot đang chạy...")
    bot.infinity_polling()