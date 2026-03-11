import re
import os
import json
import unicodedata
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. AYARLAR ---
TELEGRAM_TOKEN = "8637130007:AAH4hbucW0I5OOgmWeFvXv4rpVRo0LRS_k"
ADMIN_IDS = [8416720490, 8382929624, 652932220]

# Hedef ismi bütün olarak buraya yazıyoruz (Küçük harf ve boşluksuz/emojisiz haliyle)
# "Octopus Game TR" normalize edildiğinde "octopusgametr" olur.
TARGET_PHRASE = "octopusgametr"

TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*[a-zA-Z0-9_]{5,}'

# --- 2. JSON VERİTABANI ---
BLACKLIST_FILE = "blacklist.json"
def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"5177820294": "Octopus Game TR"}

BLACKLIST = load_blacklist()

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

# --- 3. YARDIMCI FONKSİYONLAR ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

def normalize_text(text):
    """Emojileri siler, harfleri küçültür ve boşlukları atar."""
    if not text: return ""
    # Sadece harf ve rakamları al (Kategorisi L-Letter veya N-Number olanlar)
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] in 'LN')
    return text.lower().replace('İ', 'i').replace('I', 'ı').strip()

# --- 4. ANA DENETLEME ---
async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    if not msg or not user or update.effective_chat.type == 'private':
        return
        
    if is_admin(user.id):
        return

    # A) ID KONTROLÜ
    is_blacklisted_id = str(user.id) in BLACKLIST
    
    # B) TAM İSİM KONTROLÜ
    user_full_name = (user.first_name or "") + (user.last_name or "")
    normalized_name = normalize_text(user_full_name)
    
    # İsmin içinde "octopusgametr" tam kalıbı geçiyor mu?
    is_blacklisted_name = TARGET_PHRASE in normalized_name

    # Eğer ID veya TAM İSİM eşleşiyorsa link kontrolüne geç
    if is_blacklisted_id or is_blacklisted_name:
        content = (msg.text or msg.caption or "")
        match = re.search(TELEGRAM_LINK_REGEX, content, re.IGNORECASE | re.MULTILINE)

        if match:
            try:
                await msg.delete()
                print(f"✅ REKLAM SİLİNDİ: {user.id} | Sebep: {'ID Listesi' if is_blacklisted_id else 'Tam İsim Eşleşmesi'}")
            except Exception as e:
                print(f"❌ Silme hatası: {e}")
        else:
            # Sadece takip için
            if is_blacklisted_name:
                print(f"ℹ️ Şüpheli isim ({normalized_name}) ama mesajda link yok.")

# --- 5. KOMUTLAR ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("🛡 Bot aktif. Hedef: 'Octopus Game TR' tam isim koruması.")

async def engelle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        new_id = context.args[0]
        BLACKLIST[str(new_id)] = "Manuel Engellenen"
        save_blacklist()
        await update.message.reply_text(f"✅ {new_id} ID listesine eklendi.")

# --- 6. ÇALIŞTIRICI ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("engelle", engelle_command))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), delete_octopus_ads))
    
    print("🚀 Tam İsim Filtreleme Sistemi Devrede...")
    app.run_polling()

if __name__ == "__main__":
    main()
