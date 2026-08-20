import os
import discord
import google.generativeai as genai
from keep_alive import keep_alive

# Mengambil kunci rahasia dari Render
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Konfigurasi Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

system_prompt = (
    "Kamu adalah Asisten AI Creative Director yang ahli dalam strategi konten, "
    "TikTok Affiliate, dan pembuatan storyboard video UGC yang menjual. "
    "Jawablah dengan bahasa Indonesia yang natural, ramah, dan kreatif. "
    "Jika pengguna mengirimkan gambar produk, bantu analisis dan berikan ide kontennya."
)

# Menggunakan model Gemini 3.6 Flash terbaru
model = genai.GenerativeModel(model_name="gemini-3.6-flash", system_instruction=system_prompt)

# Pengaturan Bot Discord murni
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot {client.user} sudah bangun dan siap bekerja dengan Gemini 3.6!")

@client.event
async def on_message(message):
    # Agar bot tidak merespons pesannya sendiri
    if message.author == client.user:
        return

    # Bot merespons jika:
    # 1. Diawali !buat
    # 2. Bot di-tag (@)
    # 3. Bot di-reply (balas chat)
    if message.content.startswith("!buat") or client.user in message.mentions or (message.reference and message.reference.resolved and message.reference.resolved.author == client.user):
        
        async with message.channel.typing():
            try:
                prompt_text = message.content.replace("!buat", "").strip()
                if not prompt_text and not message.attachments:
                    prompt_text = "Halo! Saya Asisten Creative Director kamu. Ada yang bisa dibantu untuk konten atau produk hari ini?"

                contents = [prompt_text]

                # Cek apakah pengguna mengirimkan foto/gambar
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type and "image" in attachment.content_type:
                            image_bytes = await attachment.read()
                            image_part = {
                                "mime_type": attachment.content_type,
                                "data": image_bytes
                            }
                            contents.append(image_part)

                # Kirim ke Gemini AI
                response = model.generate_content(contents)
                await message.reply(response.text)

            except Exception as e:
                await message.reply(f"Ups, ada kendala teknis: {e}")

# Jalankan server anti-tidur dan bot Discord
keep_alive()
client.run(DISCORD_TOKEN)
