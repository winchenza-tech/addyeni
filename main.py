import re
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- AYARLAR ---
TELEGRAM_TOKEN = "8637130007:AAH4hbucW0I5OOgmWeFvXv4rpVRo0LRSJ_k"
ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780]

# --- JSON VERİTABANI ---
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

def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- DETAYLI REGEX TANIMI ---
# Bu regex şunları yakalar:
# 1. t.me/xxxx, telegram.me/xxxx, telegram.dog/xxxx
# 2. https://t.me/xxxx, http://t.me/xxxx
# 3. t . me / xxxx (aradaki boşluklar)
# 4. Mesajın herhangi bir yerinde geçen linkler
TELEGRAM_LINK_REGEX = r'(?:https?:\/\/)?(?:t\s*\.\s*me|telegram\s*\.\s*me|telegram\s*\.\s*dog)\s*\/\s*[a-zA-Z0-9_]{5,}'

# --- REKLAM ENGELLEME FONKSİYONU ---
async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    if not msg or not user:
        return

    # 1. Kontrol: Kullanıcı admin mi? (Adminse dokunma)
    if is_admin(user.id):
        return

    # 2. Kontrol: Kullanıcı Karalistede mi?
    # ID'yi string olarak kontrol ediyoruz (JSON formatı gereği)
    if str(user.id) not in BLACKLIST:
        return

    # Mesaj metnini veya medya açıklamasını (caption) birleştiriyoruz
    content = (msg.text or msg.caption or "")
    
    # 3. Kontrol: Detaylı Regex Taraması
    # re.IGNORECASE: Büyük/küçük harf duyarlılığını kaldırır
    # re.MULTILINE: Birden fazla satırı tarar
    match = re.search(TELEGRAM_LINK_REGEX, content, re.IGNORECASE | re.MULTILINE)

    if match:
        try:
            await msg.delete()
            print(f"✅ REKLAM SİLİNDİ! \nKullanıcı: {user.first_name} ({user.id}) \nYakalanan Link: {match.group()}")
        except Exception as e:
            print(f"❌ Mesaj silinemedi (Yetki sorunu?): {e}")
    else:
        # Link yoksa ama kara listedeki kişi bir şey yazdıysa buraya düşer
        # İstersen link olmasa bile kara listedekilerin her mesajını sildirebilirsin
        print(f"ℹ️ Kara listedeki {user.id} mesaj attı ama link bulunamadı.")

# --- KOMUTLAR ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("🛡 Bot aktif ve Link koruması devrede.")

async def engelle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        target_id = context.args[0]
        BLACKLIST[str(target_id)] = "Engellenen"
        save_blacklist()
        await update.message.reply_text(f"✅ {target_id} karalisteye eklendi.")

async def liste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    res = "🚫 **KARA LİSTE**\n\n"
    for b_id, name in BLACKLIST.items():
        res += f"• `{b_id}`\n"
    await update.message.reply_text(res, parse_mode="Markdown")

# --- ANA ÇALIŞTIRICI ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("engelle", engelle_command))
    app.add_handler(CommandHandler("liste", liste_command))
    
    # Gruplardaki her türlü mesajı (metin, foto, video açıklaması vb.) kontrol eder
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), delete_octopus_ads))
    
    print("🚀 Gelişmiş Regex Botu Başlatıldı...")
    app.run_polling()

if __name__ == "__main__":
    main()
