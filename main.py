import re
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. AYARLAR ---
# Token ve Admin ID'lerinizi buraya ekleyin
TELEGRAM_TOKEN = "8637130007:AAH4hbucW0I5OOgmWeFvXv4rpVRo0LRSJ_k"
ADMIN_IDS = [8416720490, 8382929624, 652932220, 7094870780]

# Kelimeleri kök hallerine indirdik (Böylece 'grubumuz', 'grubuna' hepsini yakalar)
BANNED_KEYWORDS = [
    "kanal", "grubumuz", "grup", "davet", "katıl", "bekleriz", "katılabilirsiniz"
]

# --- 2. JSON VERİTABANI ---
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

BLACKLIST = load_blacklist()

# --- 3. YARDIMCI FONKSİYONLAR ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- 4. REKLAM ENGELLEME MANTIĞI ---
async def delete_octopus_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    
    # Özel mesajları veya adminleri atla
    if not msg or not user or update.effective_chat.type == 'private':
        return
    if is_admin(user.id):
        return

    # ÖNEMLİ: Sadece BLACKLIST içindeki kişileri denetle
    # Eğer listede olmayanların da reklamını silmek istiyorsan bu 'if'i kaldırabilirsin.
    if str(user.id) not in BLACKLIST:
        return

    # Mesaj içeriğini normalize et (Küçük harf, Türkçe karakter düzeltme)
    text = (msg.text or msg.caption or "").lower().replace('İ', 'i').replace('I', 'ı')
    
    # --- LİNK KONTROLÜ (Entity & Regex) ---
    has_link = False
    
    # A) Telegram'ın kendi sisteminden link kontrolü (En garantisi)
    if msg.entities or msg.caption_entities:
        entities = msg.entities or msg.caption_entities
        for ent in entities:
            if ent.type in ['url', 'text_link']:
                has_link = True
                break
    
    # B) Regex ile manuel kontrol (Garantilemek için)
    if not has_link:
        # t.me, telegram.me veya http içeren her şeyi yakalar
        link_pattern = r'(t\s*\.\s*me|telegram\s*\.\s*me|http)'
        if re.search(link_pattern, text):
            has_link = True

    # --- KELİME KONTROLÜ ---
    has_keyword = any(keyword in text for keyword in BANNED_KEYWORDS)

    # EĞER LİNK VEYA YASAKLI KELİME VARSA SİL
    if has_link or has_keyword:
        try:
            await msg.delete()
            print(f"🚨 REKLAM SİLİNDİ: {user.first_name} ({user.id})")
        except Exception as e:
            print(f"❌ SİLME HATASI (Yetki Eksik Olabilir): {e}")

# --- 5. ADMİN KOMUTLARI ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Erişim reddedildi.")
        return
    await update.message.reply_text("🛡 Bot aktif. Komutlar için `/komutlar` yazın.")

async def komutlar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    rehber = (
        "🛡 **KOMUT REHBERİ**\n\n"
        "🔹 `/engelle ID` : Kullanıcıyı kara listeye ekler.\n"
        "🔹 `/liste` : Kara listeyi gösterir.\n"
        "🔹 `/izinver SIRA_NO` : Listeden çıkarır."
    )
    await update.message.reply_text(rehber, parse_mode="Markdown")

async def engelle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Kullanım: `/engelle 12345678`")
        return
    
    target_id = context.args[0]
    try:
        # ID geçerli mi kontrol et
        chat = await context.bot.get_chat(int(target_id))
        name = chat.first_name or chat.title
        BLACKLIST[str(target_id)] = name
        save_blacklist()
        await update.message.reply_text(f"✅ {name} ({target_id}) listeye eklendi.")
    except Exception:
        # ID bulunamazsa yine de ekle (Önlem olarak)
        BLACKLIST[str(target_id)] = "Bilinmeyen Kullanıcı"
        save_blacklist()
        await update.message.reply_text(f"✅ {target_id} listeye eklendi (Kullanıcı adı alınamadı).")

async def liste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not BLACKLIST:
        await update.message.reply_text("Liste boş.")
        return
    res = "🚫 **KARA LİSTE**\n\n"
    for i, (b_id, name) in enumerate(BLACKLIST.items(), 1):
        res += f"{i}. {name} - `{b_id}`\n"
    await update.message.reply_text(res, parse_mode="Markdown")

async def izinver_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        rank = int(context.args[0])
        keys = list(BLACKLIST.keys())
        target_id = keys[rank - 1]
        name = BLACKLIST.pop(target_id)
        save_blacklist()
        await update.message.reply_text(f"🔓 {name} listeden çıkarıldı.")
    except:
        await update.message.reply_text("❌ Geçersiz sıra numarası.")

# --- 6. ÇALIŞTIRICI ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Komutlar
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("komutlar", komutlar_command))
    app.add_handler(CommandHandler("engelle", engelle_command))
    app.add_handler(CommandHandler("liste", liste_command))
    app.add_handler(CommandHandler("izinver", izinver_command))
    
    # Mesaj Dinleyiciler
    # Gruplardaki tüm mesajları kontrol et
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (~filters.COMMAND), delete_octopus_ads))
    
    print("🚀 Bot başarıyla başlatıldı!")
    app.run_polling()

if __name__ == "__main__":
    main()
