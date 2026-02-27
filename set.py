import io
import os
import urllib.parse
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from motor.motor_asyncio import AsyncIOMotorClient

# --- KONFIGURASI ---
API_ID = int(os.getenv('API_ID', '36479019'))
API_HASH = os.getenv('API_HASH', '816d1a0589b0cb1f9d147ba4d07ca576')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8532883919:AAH1Khwvzctscyk7ruTsVe8ThJd__r1-uIk')
MONGO_URL = os.getenv('MONGO_URL', 'mongodb+srv://Nadira:Nadira31@cluster0.15j5b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '1423164174').split(',')]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client['warung_lendir_db']
settings_col = db['settings']
app = Client("bot_warung", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def get_db():
    data = await settings_col.find_one({"id": "config"})
    if not data:
        default = {
            "id": "config", "counter": 0, "caption": "Join VIP", 
            "logo_bytes": None, "is_sticker": False, "waiting_for": None, 
            "buttons": [], "target_chat": None
        }
        await settings_col.insert_one(default)
        return default
    return data

# --- MENU ADMIN ---
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if message.from_user.id not in ADMIN_IDS: return
    
    data = await get_db()
    target_name = data.get('target_chat', 'Belum Diatur')
    
    menu = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Watermark", callback_data="sl"), InlineKeyboardButton("📝 Caption", callback_data="sc")],
        [InlineKeyboardButton("🔗 Tambah Tombol", callback_data="sb"), InlineKeyboardButton("🗑️ Reset Tombol", callback_data="reset_btn")],
        [InlineKeyboardButton("📺 Set Channel Tujuan", callback_data="stc")],
        [InlineKeyboardButton("🔢 RESET COUNTER (0)", callback_data="rcn")]
    ])
    
    await message.reply(
        f"**ADMIN PANEL**\n\n"
        f"📍 Channel: `{target_name}`\n"
        f"🔢 Counter: `{data['counter']}`\n"
        f"🔘 Tombol: `{len(data['buttons'])}`", 
        reply_markup=menu
    )

@app.on_callback_query()
async def callbacks(client, callback_query):
    if callback_query.data == "sb":
        await settings_col.update_one({"id": "config"}, {"$set": {"waiting_for": "add_button"}})
        await callback_query.edit_message_text(
            "**KIRIM FORMAT TOMBOL:**\n\n"
            "1. **Chat Admin:** `Nama | @User | Pesan` \n"
            "2. **Bot Sendiri:** `Nama | start | kode` \n"
            "3. **Bot Lain:** `Nama | https://t.me/BotLain?start=kode` \n"
            "4. **Link Bebas:** `Nama | https://t.me/Link`"
        )
    elif callback_query.data == "stc":
        await settings_col.update_one({"id": "config"}, {"$set": {"waiting_for": "set_target"}})
        await callback_query.edit_message_text("Kirim Username Channel (pakai @) atau ID.")
    elif callback_query.data == "rcn":
        await settings_col.update_one({"id": "config"}, {"$set": {"counter": 0}})
        await callback_query.answer("Counter di-reset ke 0!", show_alert=True)
        # Menampilkan kembali menu dengan data terbaru
        data = await get_db()
        target_name = data.get('target_chat', 'Belum Diatur')
        menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ Watermark", callback_data="sl"), InlineKeyboardButton("📝 Caption", callback_data="sc")],
            [InlineKeyboardButton("🔗 Tambah Tombol", callback_data="sb"), InlineKeyboardButton("🗑️ Reset Tombol", callback_data="reset_btn")],
            [InlineKeyboardButton("📺 Set Channel Tujuan", callback_data="stc")],
            [InlineKeyboardButton("🔢 RESET COUNTER (0)", callback_data="rcn")]
        ])
        await callback_query.edit_message_text(
            f"**ADMIN PANEL**\n\n"
            f"📍 Channel: `{target_name}`\n"
            f"🔢 Counter: `0`\n"
            f"🔘 Tombol: `{len(data['buttons'])}`", 
            reply_markup=menu
        )
    elif callback_query.data == "reset_btn":
        await settings_col.update_one({"id": "config"}, {"$set": {"buttons": []}})
        await callback_query.answer("Semua tombol dihapus!")
    elif callback_query.data == "sl":
        await settings_col.update_one({"id": "config"}, {"$set": {"waiting_for": "logo"}})
        await callback_query.answer("Kirim Watermark")
    elif callback_query.data == "sc":
        await settings_col.update_one({"id": "config"}, {"$set": {"waiting_for": "caption"}})
        await callback_query.answer("Ketik Caption")

@app.on_message(filters.private & ~filters.command("start"))
async def handle_settings(client, message):
    if message.from_user.id not in ADMIN_IDS: return
    data = await get_db()
    
    if data['waiting_for'] == 'add_button' and "|" in message.text:
        parts = message.text.split("|")
        name, val_dua = parts[0].strip(), parts[1].strip()
        if val_dua.startswith("http"): final_url = val_dua
        elif val_dua.lower() == "start":
            me = await client.get_me()
            final_url = f"https://t.me/{me.username}?start={parts[2].strip()}"
        elif len(parts) == 3:
            final_url = f"https://t.me/{val_dua.replace('@','') }?text={urllib.parse.quote(parts[2].strip())}"
        else: final_url = val_dua
        await settings_col.update_one({"id": "config"}, {"$push": {"buttons": {"name": name, "url": final_url}}})
        await message.reply(f"✅ Berhasil: {name}")
    
    elif data['waiting_for'] == 'set_target' and message.text:
        await settings_col.update_one({"id": "config"}, {"$set": {"target_chat": message.text, "waiting_for": None}})
        await message.reply(f"✅ Target diatur ke: {message.text}")

    elif data['waiting_for'] == 'logo' and (message.photo or message.sticker or message.document):
        is_stk = bool(message.sticker)
        file_id = message.photo.file_id if message.photo else (message.sticker.file_id if message.sticker else message.document.file_id)
        logo_bytes = await client.download_media(file_id, in_memory=True)
        await settings_col.update_one({"id": "config"}, {"$set": {"logo_bytes": bytes(logo_bytes.getbuffer()), "is_sticker": is_stk, "waiting_for": None}})
        await message.reply("✅ Watermark diperbarui!")
        
    elif data['waiting_for'] == 'caption' and message.text:
        await settings_col.update_one({"id": "config"}, {"$set": {"caption": message.text, "waiting_for": None}})
        await message.reply("✅ Caption diperbarui!")

@app.on_message(filters.photo | filters.document)
async def processor(client, message):
    if message.chat.type.value == "private" and message.from_user.id not in ADMIN_IDS: return
    data = await get_db()
    if not data['logo_bytes']: return
    
    chat_tujuan = data.get('target_chat') if data.get('target_chat') else message.chat.id

    try:
        photo_bytes = await client.download_media(message, in_memory=True)
        main_img = Image.open(io.BytesIO(photo_bytes.getbuffer())).convert("RGBA")
        m_w, m_h = main_img.size
        logo = Image.open(io.BytesIO(data['logo_bytes'])).convert("RGBA")
        
        if data['is_sticker']:
            new_w = int(m_w * 1.5)
            new_h = int(logo.size[1] * (new_w / logo.size[0]))
            logo = logo.resize((new_w, new_h), Image.LANCZOS)
            pos, opac = ((m_w - new_w) // 2, (m_h - new_h) // 2), 0.20
        else:
            new_w = int(m_w * 0.5)
            new_h = int(logo.size[1] * (new_w / logo.size[0]))
            logo = logo.resize((new_w, new_h), Image.LANCZOS)
            pos, opac = ((m_w - new_w) // 2, m_h - new_h - 50), 0.50
            
        alpha = logo.getchannel('A').point(lambda i: i * opac)
        logo.putalpha(alpha)
        main_img.paste(logo, pos, logo)
        
        output = io.BytesIO()
        output.name = "res.jpg"
        main_img.convert("RGB").save(output, format="JPEG", quality=85)
        output.seek(0)
        
        raw_btns = data.get('buttons', [])
        grid = []
        for i in range(0, len(raw_btns), 2):
            row = [InlineKeyboardButton(raw_btns[i]['name'], url=raw_btns[i]['url'])]
            if i + 1 < len(raw_btns):
                row.append(InlineKeyboardButton(raw_btns[i+1]['name'], url=raw_btns[i+1]['url']))
            grid.append(row)
        
        markup = InlineKeyboardMarkup(grid) if grid else None
        
        await settings_col.update_one({"id": "config"}, {"$inc": {"counter": 1}})
        await client.send_photo(chat_tujuan, output, caption=f"● {data['counter']+1}\n{data['caption']}", reply_markup=markup)
        
        if chat_tujuan == message.chat.id:
            await message.delete()
            
    except Exception as e:
        logger.error(e)

app.run()
