import os
import discord
from discord.ext import commands
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

# Menggunakan model Gemini 3.6 Flash
model = genai.GenerativeModel(model_name="gemini-3.6-flash", system_instruction=system_prompt)

# Pengaturan Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} sudah bangun dan siap bekerja dengan Gemini 3.6!")

@bot.event
async def on_message(message):
    # Agar bot tidak merespons pesannya sendiri
    if message.author == bot.user:
        return

    # Bot merespons jika:
    # 1. Diawali !buat
    # 2. Bot di-tag (@)
    # 3. Bot di-reply
    # 4. Dikirim di dalam server (bukan DM pribadi)
    if message.content.startswith("!buat") or bot.user in message.mentions or (message.reference and message.reference.resolved and message.reference.resolved.author == bot.user):
        
        async with message.channel.typing():
            try:
                prompt_text = message.content.replace("!buat", "").strip()
                if not prompt_text and not message.attachments:
                    prompt_text = "Halo! Saya Asisten Creative Director kamu. Ada yang bisa dibantu untuk konten hari ini?"

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

    await bot.process_commands(message)

# Jalankan server anti-tidur dan bot Discord
keep_alive()
bot.run(DISCORD_TOKEN)
