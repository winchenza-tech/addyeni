import re
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. AYARLAR ---
TELEGRAM_TOKEN = "8637130007:AAH4hbucW0I5OOgmWeFvXv4rpVRo0LRSJ_k"

# Test için 7094870780 ID'sini buradan çıkardım (Admin olunca silme çalışmaz)
ADMIN_IDS = [8416720490, 8382929624, 652932220] 

# --- 2. JSON VERİTABANI ---
BLACKLIST_FILE = "blacklist.json"
DEFAULT_BLACKLIST = {
    "5177820294": "Octopus Game TR",
    "7094870780": "Deneme Hesabı"  # <--- Test için buraya ekledik
}

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_BLACKLIST.copy()

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

BLACKLIST = load_blacklist()

# --- 3. YARDIMCI FONKSİYONLAR ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- 4. GELİŞMİŞ REGEX VE SİLME MANTIĞI ---
# Bu regex t.me/xxx, t . me / xxx, telegram.me gibi her türlü varyasyonu yakalar
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*[a-zA-Z0-9_]{5,}'

async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    if not msg or not user or update.effective_chat.type == 'private':
        return
        
    # Admin ise kontrol etme (Adminler reklam yapabilir mantığı)
    if is_admin(user.id):
        return

    # Sadece kara listedeki hesapları denetle
    if str(user.id) not in BLACKLIST:
        return

    # Mesaj metni veya medya açıklamasını al
    content = (msg.text or msg.caption or "")
    
    # Regex taraması (Büyük/Küçük harf duyarsız)
    match = re.search(TELEGRAM_LINK_REGEX, content, re.IGNORECASE | re.MULTILINE)

    if match:
        try:
            await msg.delete()
            print(f"✅ REKLAM SİLİNDİ: {user.id} - Link: {match.group()}")
        except Exception as e:
            print(f"❌ Silme hatası (Bot admin mi?): {e}")
    else:
        # Debug: Link bulunamazsa terminale yaz (Neden silmediğini anlamak için)
        print(f"ℹ️ {user.id} mesaj attı ama içinde Telegram linki bulunamadı.")

# --- 5. ADMİN KOMUTLARI ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("🛡 Deneme hesabı engelli listesine eklendi. Test yapabilirsiniz.")

async def liste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    res = "🚫 **GÜNCEL KARA LİSTE**\n\n"
    for b_id, name in BLACKLIST.items():
        res += f"• `{b_id}` ({name})\n"
    await update.message.reply_text(res, parse_mode="Markdown")

async def engelle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        new_id = context.args[0]
        BLACKLIST[str(new_id)] = "Manuel Engellenen"
        save_blacklist()
        await update.message.reply_text(f"✅ {new_id} listeye eklendi.")

# --- 6. ÇALIŞTIRICI ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("liste", liste_command))
    app.add_handler(CommandHandler("engelle", engelle_command))
    
    # Gruplardaki mesajları dinle
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), delete_octopus_ads))
    
    print("🚀 Bot çalışıyor... Test hesabı kara listede.")
    app.run_polling()

if __name__ == "__main__":
    main()
