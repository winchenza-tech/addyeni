import re
import os
import json
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

# Yasaklı Kelimeler Listesi
BANNED_WORDS = ["aramıza", "grubumuza", "grubuna", "sohbet", "ortam"]

# Özel davet linklerini (+ ve - barındıran) yakalayabilen Regex
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*(?:\+)?[\w\-]+'

# --- 3. JSON VERİTABANI (HEM ID HEM USERNAME) ---
BLACKLIST_FILE = "blacklist.json"

def load_blacklist():
    default_blacklist = {
        "octopusgame_bot": "Octopus Game TR Reklam Botu",
        "eskidenyesil": "Deneme Test Hesabı"
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

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

BLACKLIST = load_blacklist()

# --- 4. YARDIMCI FONKSİYONLAR ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- 5. ANA DENETLEME ---
async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    if not msg or not user or update.effective_chat.type == 'private':
        return
        
    if is_admin(user.id):
        return

    # 1. Kullanıcının Username'ini ve ID'sini al (ID'yi stringe çeviriyoruz çünkü JSON key'leri string olur)
    username = user.username.lower() if user.username else ""
    user_id_str = str(user.id)
    
    # KULLANICI ADI VEYA ID KARALİSTEDEYSE İŞLEME DEVAM ET
    is_blacklisted = (username in BLACKLIST) or (user_id_str in BLACKLIST)

    if is_blacklisted:
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
                yakalanan_sey = []
                if has_link: yakalanan_sey.append("Link")
                if has_banned_word: yakalanan_sey.append("Yasaklı Kelime")
                
                sebep = f"Karaliste ({user_id_str}/{username}) -> {' + '.join(yakalanan_sey)}"
                print(f"✅ REKLAM SİLİNDİ: @{username} | Sebep: {sebep}")
                
            except Exception as e:
                print(f"❌ Silme hatası: {e}")

# --- 6. KOMUTLAR ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("🛡️ Koruma sistemi aktif! Hem ID hem Username bazlı karaliste devrede.")

async def add_blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return

    # Eğer bir mesaja yanıt verilmişse o kişiyi ekle
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_id = str(target_user.id)
        
        BLACKLIST[target_id] = f"ID Ban (Ekleyen: {update.effective_user.first_name})"
        if target_user.username:
            BLACKLIST[target_user.username.lower()] = f"Username Ban (Ekleyen: {update.effective_user.first_name})"
        
        save_blacklist()
        await update.message.reply_text(f" karalisteye eklendi (ID: {target_id}).")
        return

    # Yanıt verilmemişse, komutun yanına yazılan metni al (Örn: /ekle 123456789 veya /ekle @kullanici)
    if not context.args:
        await update.message.reply_text("Kullanım: Bir mesaja yanıt verin veya `/ekle <id_veya_username>` yazın.")
        return

    target = context.args[0].replace("@", "").lower()
    BLACKLIST[target] = f"Manuel Eklendi (Ekleyen: {update.effective_user.first_name})"
    save_blacklist()
    await update.message.reply_text(f"✅ `{target}` karalisteye eklendi.")

async def remove_blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return

    # Eğer bir mesaja yanıt verilmişse o kişiyi çıkar
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_id = str(target_user.id)
        target_username = target_user.username.lower() if target_user.username else None
        
        removed = False
        if target_id in BLACKLIST:
            del BLACKLIST[target_id]
            removed = True
        if target_username and target_username in BLACKLIST:
            del BLACKLIST[target_username]
            removed = True
            
        if removed:
            save_blacklist()
            await update.message.reply_text("✅ Kullanıcı karalisteden çıkarıldı.")
        else:
            await update.message.reply_text("⚠️ Bu kullanıcı zaten karalistede bulunmuyor.")
        return

    if not context.args:
        await update.message.reply_text("Kullanım: Bir mesaja yanıt verin veya `/cikar <id_veya_username>` yazın.")
        return

    target = context.args[0].replace("@", "").lower()
    if target in BLACKLIST:
        del BLACKLIST[target]
        save_blacklist()
        await update.message.reply_text(f"✅ `{target}` karalisteden çıkarıldı.")
    else:
        await update.message.reply_text(f"⚠️ `{target}` karalistede bulunamadı.")

async def list_blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    if not BLACKLIST:
        await update.message.reply_text("📋 Karaliste şu an boş.")
        return

    text = "📋 **Güncel Karaliste:**\n"
    for key, value in BLACKLIST.items():
        text += f"• `{key}` - _{value}_\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# --- 7. ÇALIŞTIRICI ---
def main():
    keep_alive()
    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Komutları ekle
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("ekle", add_blacklist_command))
        app.add_handler(CommandHandler("cikar", remove_blacklist_command))
        app.add_handler(CommandHandler("liste", list_blacklist_command))
        
        # Normal mesaj denetleyici
        app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), delete_octopus_ads))
        
        print("🚀 Bot uyanık ve karalistedeki reklamcıları avlamaya hazır.")
        app.run_polling(drop_pending_updates=True) 
    except Exception as e:
        print(f"⚠️ KRİTİK HATA: {e}")

if __name__ == "__main__":
    main()
