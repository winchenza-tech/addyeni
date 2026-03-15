import re
import os
import json
import unicodedata
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. WEB SUNUCUSU ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot 7/24 Aktif ve Uyanık!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. AYARLAR ---
TELEGRAM_TOKEN = "8637130007:AAEX9jWl5WOs9iQb7oVkyCik6oIkgTpH8tM" 
ADMIN_IDS = [8416720490, 8382929624, 652932220]
TARGET_PHRASE = "octopusgametr"

# Yasaklı Kelimeler Listesi (Sadece blacklisttekiler için aranacak)
BANNED_WORDS = ["aramıza", "sohbetgo", "katılmak için"]

# Özel davet linklerini (+ ve - barındıran) yakalayabilen Regex
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'

# --- 3. JSON VERİTABANI ---
BLACKLIST_FILE = "blacklist.json"

def load_blacklist():
    default_blacklist = {
        "5177820294": "Octopus Game TR",
        "7094870780": "Kara Listedeki Kullanıcı" 
    }
    
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                data.update(default_blacklist)
                return data
            except:
                return default_blacklist
    return default_blacklist

BLACKLIST = load_blacklist()

# --- 4. YARDIMCI FONKSİYONLAR ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

def normalize_text(text):
    if not text: return ""
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] in 'LN')
    return text.lower().replace('İ', 'i').replace('I', 'ı').strip()

# --- 5. ANA DENETLEME ---
async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    if not msg or not user or update.effective_chat.type == 'private':
        return
        
    if is_admin(user.id):
        return

    # 1. Kullanıcı ID veya İsim olarak karalistedeyse tespit et
    is_blacklisted_id = str(user.id) in BLACKLIST
    user_full_name = (user.first_name or "") + (user.last_name or "")
    normalized_name = normalize_text(user_full_name)
    is_blacklisted_name = TARGET_PHRASE in normalized_name

    # KULLANICI KARALİSTEDEYSE İŞLEME DEVAM ET
    if is_blacklisted_id or is_blacklisted_name:
        content = (msg.text or msg.caption or "")
        content_lower = content.lower()

        # Link var mı?
        has_link = bool(re.search(TELEGRAM_LINK_REGEX, content, re.IGNORECASE | re.MULTILINE))
        
        # Yasaklı kelime var mı?
        has_banned_word = any(word in content_lower for word in BANNED_WORDS)

        # İkisinden biri varsa mesajı sil
        if has_link or has_banned_word:
            try:
                await msg.delete()
                
                # Konsola detaylı log yazdır
                kullanici_tipi = "ID Karalistesi" if is_blacklisted_id else "İsim Filtresi"
                yakalanan_sey = []
                if has_link: yakalanan_sey.append("Link")
                if has_banned_word: yakalanan_sey.append("Yasaklı Kelime")
                
                sebep = f"{kullanici_tipi} -> {' + '.join(yakalanan_sey)}"
                print(f"✅ REKLAM SİLİNDİ: {user.id} | Sebep: {sebep}")
                
            except Exception as e:
                print(f"❌ Silme hatası: {e}")

# --- 6. KOMUTLAR ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("🛡️ Koruma sistemi, Yeni Regex ve Kelime Filtresi aktif!")

# --- 7. ÇALIŞTIRICI ---
def main():
    keep_alive()
    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), delete_octopus_ads))
        
        print("🚀 Bot uyanık ve karalistedeki reklamcıları avlamaya hazır.")
        app.run_polling(drop_pending_updates=True) 
    except Exception as e:
        print(f"⚠️ KRİTİK HATA: {e}")

if __name__ == "__main__":
    main()
