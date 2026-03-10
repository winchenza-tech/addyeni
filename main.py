import re
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. AYARLAR ---
TELEGRAM_TOKEN = "8637130007:AAH4hbucW0I5OOgmWeFvXv4rpVRo0LRSJ_k"

ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780]

BANNED_KEYWORDS = [
    "kanalımıza", "kanalına", "kanal", 
    "grubuna", "grubumuza", 
    "davetlisiniz", "katılabilirsiniz"
]

# --- 1.5 JSON VERİTABANI (Kara listenin sıfırlanmaması için) ---
BLACKLIST_FILE = "blacklist.json"
DEFAULT_BLACKLIST = {
    "5177820294": "Octopus Game TR",
    "1858358799": "Bilinmeyen Bot 1",
    "7818025361": "Bilinmeyen Bot 2",
    "7495125802": "Test Hesabı"  
}

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_BLACKLIST.copy()

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(BLACKLIST, f, ensure_ascii=False, indent=4)

# Başlangıçta listeyi yükle
BLACKLIST = load_blacklist()


# --- 2. YARDIMCI FONKSİYONLAR ---
def is_admin(user_id):
    return user_id in ADMIN_IDS


# --- 3. REKLAM ENGELLEME (GRUPLAR İÇİN) ---
async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    if not msg or not user or update.effective_chat.type == 'private':
        return
        
    if is_admin(user.id):
        return

    # ID'ler JSON'da string olarak tutulduğu için string'e çevirerek kontrol ediyoruz
    if str(user.id) not in BLACKLIST:
        return

    text = (msg.text or msg.caption or "")
    if not text:
        return

    link_pattern = r'(?:https?:\/\/)?(?:t\s*\.\s*m\s*e|telegram\s*\.\s*m\s*e)\s*\/'
    has_link = bool(re.search(link_pattern, text, re.IGNORECASE))
    
    text_lower = text.lower().replace('İ', 'i').replace('I', 'ı')
    has_keyword = any(keyword in text_lower for keyword in BANNED_KEYWORDS)

    if has_link or has_keyword:
        try:
            await msg.delete()
            print(f"Reklam Silindi: {user.id} - İçerik: {text[:30]}...")
        except Exception as e:
            print(f"Silme Hatası (Reklam): {e}")


# --- 4. ADMİN YÖNETİM SİSTEMİ (ÖZEL MESAJLAR İÇİN) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu bot üzerinde herhangi bir yetkin bulunmuyor. Erişim reddedildi.")
        return
    await update.message.reply_text("🛡 Hoş geldin admin. Komutlar için `/komutlar` yazabilirsin.")

async def komutlar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    rehber = (
        "🛡 **KOMUT REHBERİ**\n\n"
        "🔹 `/engelle ID` : Botu veya kullanıcıyı kara listeye ekler.\n"
        "🔹 `/liste` : Kara listeyi gösterir.\n"
        "🔹 `/izinver SIRA_NO` : Kara listeden çıkarır.\n"
    )
    await update.message.reply_text(rehber, parse_mode="Markdown")

async def engelle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: 
        await update.message.reply_text("Kullanım: `/engelle ID`", parse_mode="Markdown")
        return
        
    try:
        new_id_str = str(int(context.args[0])) # Rakam kontrolü için önce int, sonra JSON için string
        try:
            bot_chat = await context.bot.get_chat(int(new_id_str))
            bot_name = bot_chat.first_name or bot_chat.title or f"Bilinmeyen ({new_id_str})"
        except:
            bot_name = f"Bilinmeyen ({new_id_str})"
            
        BLACKLIST[new_id_str] = bot_name
        save_blacklist() # RAM'deki değişikliği dosyaya kalıcı olarak kaydet
        await update.message.reply_text(f"✅ {bot_name} şüpheli listesine eklendi. Sadece reklam atarsa silinecek.")
    except ValueError:
        await update.message.reply_text("❌ Geçersiz ID. Lütfen rakamlardan oluşan bir ID girin.")

async def liste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not BLACKLIST:
        await update.message.reply_text("Kara liste boş.")
        return
        
    res = "🚫 **KARA LİSTE**\n\n"
    for i, (b_id, name) in enumerate(BLACKLIST.items(), 1):
        res += f"{i}. {name} - `{b_id}`\n"
    await update.message.reply_text(res, parse_mode="Markdown")

async def izinver_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: 
        await update.message.reply_text("Kullanım: `/izinver SIRA_NO`", parse_mode="Markdown")
        return
        
    try:
        rank = int(context.args[0])
        keys = list(BLACKLIST.keys())
        if 0 < rank <= len(keys):
            target_id = keys[rank - 1]
            name = BLACKLIST.pop(target_id)
            save_blacklist() # RAM'deki değişikliği dosyaya kalıcı olarak kaydet
            await update.message.reply_text(f"🔓 {name} kara listeden çıkarıldı.")
        else:
            await update.message.reply_text("❌ Geçersiz sıra numarası. Lütfen `/liste` komutuyla numaraları kontrol edin.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Hata. Lütfen listedeki sıra numarasını girin (Örn: `/izinver 1`).", parse_mode="Markdown")

async def catch_unauthorized_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Çifte mesaj bug'ı giderildi (~filters.COMMAND ile)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Yetkiniz bulunmuyor.")


# --- 5. ANA ÇALIŞTIRICI ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("komutlar", komutlar_command))
    app.add_handler(CommandHandler("engelle", engelle_command))
    app.add_handler(CommandHandler("liste", liste_command))
    app.add_handler(CommandHandler("izinver", izinver_command))
    
    # ~filters.COMMAND ekleyerek /start gibi komutların iki kez cevap vermesini önledik
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, catch_unauthorized_messages))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, delete_octopus_ads))
    
    print("Bot aktif. Emoji ve boşluklu kelimeleri delen güçlü regex devrede.")
    app.run_polling()

if __name__ == "__main__":
    main()