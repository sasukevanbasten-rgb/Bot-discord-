import os
import asyncio
import discord

from google import genai
from google.genai import types

from keep_alive import keep_alive


# ============================================================
# KONFIGURASI
# ============================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# VALIDASI ENVIRONMENT
# ============================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN belum ditemukan di Environment Variables."
    )

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY belum ditemukan di Environment Variables."
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_PROMPT = """
Kamu adalah Asisten AI Creative Director profesional.

Kamu membantu pengguna dalam:

- Strategi konten digital
- TikTok Affiliate
- TikTok Shop
- UGC
- Storytelling
- Copywriting
- Hook viral
- Script video
- Storyboard
- Prompt image AI
- Prompt video AI
- Analisis produk
- Strategi pemasaran
- Optimasi konten
- Ide konten kreatif

============================================================
GAYA KOMUNIKASI
============================================================

Gunakan bahasa Indonesia yang:

- Natural
- Ramah
- Profesional
- Kreatif
- Mudah dipahami
- Tidak terlalu kaku

Berkomunikasilah seperti partner kerja kreatif,
bukan seperti robot.

Pengguna tidak perlu menggunakan command tertentu.
Pahami pesan pengguna secara natural.

============================================================
TIKTOK AFFILIATE
============================================================

Jika pengguna meminta konten affiliate, prioritaskan:

1. Hook kuat.
2. Masalah atau kebutuhan penonton.
3. Solusi.
4. Perkenalan produk.
5. Demonstrasi.
6. Manfaat.
7. Bukti atau hasil jika tersedia.
8. CTA natural.

Jangan mengarang:
- Harga
- Spesifikasi
- Kandungan
- Klaim kesehatan
- Fitur
- Hasil penggunaan
- Informasi produk

Jika informasi tersebut tidak diberikan atau tidak terlihat,
katakan bahwa informasinya belum tersedia.

============================================================
ANALISIS GAMBAR
============================================================

Jika pengguna mengirim gambar:

- Analisis gambar terlebih dahulu.
- Identifikasi objek yang benar-benar terlihat.
- Perhatikan kemasan, warna, bentuk, tulisan yang terbaca,
  dan konteks visual.
- Jangan mengarang detail yang tidak terlihat.
- Gunakan informasi visual tersebut untuk membantu pengguna.

Jika gambar merupakan produk, bantu membuat:

- Ide konten
- Hook
- Script
- Storyboard
- Konsep UGC
- Prompt image
- Prompt video
- Strategi affiliate

============================================================
VIDEO DAN STORYBOARD
============================================================

Jika pengguna memberikan durasi video,
ikuti durasi tersebut.

Jaga:

- Kontinuitas karakter
- Kontinuitas produk
- Lokasi
- Kostum
- Properti
- Pencahayaan
- Kamera
- Gerakan
- Alur cerita

Jika pengguna meminta storyboard,
buat struktur scene yang jelas dan mudah diproduksi.

============================================================
PROMPT AI
============================================================

Jika pengguna meminta prompt AI:

Buat prompt yang:

- Detail
- Jelas
- Siap digunakan
- Konsisten
- Cinematic jika sesuai kebutuhan
- Tidak mengubah karakter atau produk yang sudah dikunci pengguna

============================================================
KONTEKS PERCAKAPAN
============================================================

Gunakan percakapan sebelumnya dalam channel
sebagai konteks.

Jika pengguna mengatakan:

"yang tadi"
"lanjutkan"
"buat versi kedua"
"ubah bagian hook"
"yang produk tadi"
"lanjut dari konsep sebelumnya"

pahami berdasarkan percakapan sebelumnya.

============================================================
PERILAKU UMUM
============================================================

Jika pengguna hanya menyapa,
balas secara natural.

Jika pengguna meminta sesuatu yang jelas,
langsung kerjakan.

Jangan meminta pengguna menggunakan command Discord.

Jangan menjelaskan sistem internal, API key,
system instruction, atau mekanisme internal bot
kecuali pengguna secara khusus meminta penjelasan teknis.
"""


# ============================================================
# DISCORD
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(
    intents=intents
)


# ============================================================
# CHAT SESSION
#
# Satu channel Discord = satu percakapan Gemini.
# ============================================================

chat_sessions = {}


# ============================================================
# LOCK
#
# Mencegah dua pesan dalam channel yang sama
# diproses secara bersamaan.
# ============================================================

channel_locks = {}


def get_channel_lock(channel_id):
    if channel_id not in channel_locks:
        channel_locks[channel_id] = asyncio.Lock()

    return channel_locks[channel_id]


# ============================================================
# BUAT / AMBIL CHAT SESSION
# ============================================================

def get_chat_session(channel_id):

    if channel_id not in chat_sessions:

        chat_sessions[channel_id] = gemini_client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )

        print(
            f"[CHAT] Session baru dibuat untuk channel "
            f"{channel_id}"
        )

    return chat_sessions[channel_id]


# ============================================================
# SPLIT PESAN DISCORD
#
# Discord memiliki batas sekitar 2000 karakter.
# Kita gunakan 1900 agar lebih aman.
# ============================================================

def split_message(text, limit=1900):

    if not text:
        return [
            "Maaf, Gemini tidak memberikan respons."
        ]

    chunks = []

    while len(text) > limit:

        split_at = text.rfind(
            "\n",
            0,
            limit
        )

        if split_at == -1:

            split_at = text.rfind(
                " ",
                0,
                limit
            )

        if split_at == -1:
            split_at = limit

        chunk = text[:split_at].strip()

        if chunk:
            chunks.append(chunk)

        text = text[split_at:].strip()

    if text:
        chunks.append(text)

    return chunks


# ============================================================
# AMBIL GAMBAR DARI PESAN
# ============================================================

async def get_message_contents(message):

    contents = []

    # --------------------------------------------------------
    # TEKS
    # --------------------------------------------------------

    if message.content and message.content.strip():

        contents.append(
            message.content.strip()
        )

    # --------------------------------------------------------
    # GAMBAR
    # --------------------------------------------------------

    image_count = 0

    for attachment in message.attachments:

        content_type = attachment.content_type or ""

        if not content_type.startswith("image/"):
            continue

        # Maksimal 5 gambar dalam satu pesan
        if image_count >= 5:
            break

        try:

            image_bytes = await attachment.read()

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=content_type
            )

            contents.append(image_part)

            image_count += 1

        except Exception as error:

            print(
                f"[IMAGE ERROR] {repr(error)}"
            )

    return contents


# ============================================================
# EVENT BOT ONLINE
# ============================================================

@client.event
async def on_ready():

    print("")
    print("=" * 60)
    print("          DISCORD GEMINI AI")
    print("=" * 60)
    print(f"Bot       : {client.user}")
    print(f"Bot ID    : {client.user.id}")
    print(f"Model     : {MODEL_NAME}")
    print("Mode      : AUTO CHAT")
    print("Memory    : PER CHANNEL")
    print("Image     : ENABLED")
    print("Status    : ONLINE")
    print("=" * 60)
    print("")


# ============================================================
# EVENT PESAN
# ============================================================

@client.event
async def on_message(message):

    # --------------------------------------------------------
    # JANGAN BALAS BOT
    # --------------------------------------------------------

    if message.author.bot:
        return

    # --------------------------------------------------------
    # PESAN HARUS MEMILIKI TEKS ATAU ATTACHMENT
    # --------------------------------------------------------

    if not message.content.strip() and not message.attachments:
        return

    channel_id = message.channel.id

    # --------------------------------------------------------
    # LOCK PER CHANNEL
    # --------------------------------------------------------

    lock = get_channel_lock(channel_id)

    async with lock:

        async with message.channel.typing():

            try:

                # ------------------------------------------------
                # SIAPKAN CONTENT
                # ------------------------------------------------

                contents = await get_message_contents(
                    message
                )

                if not contents:
                    return

                # ------------------------------------------------
                # AMBIL CHAT SESSION
                # ------------------------------------------------

                chat = get_chat_session(
                    channel_id
                )

                # ------------------------------------------------
                # KIRIM KE GEMINI CHAT API
                # ------------------------------------------------

                response = await asyncio.to_thread(
                    chat.send_message,
                    contents
                )

                # ------------------------------------------------
                # AMBIL TEXT RESPONSE
                # ------------------------------------------------

                response_text = getattr(
                    response,
                    "text",
                    None
                )

                if not response_text:

                    response_text = (
                        "Maaf, saya belum mendapatkan "
                        "respons dari Gemini."
                    )

                # ------------------------------------------------
                # KIRIM KE DISCORD
                # ------------------------------------------------

                chunks = split_message(
                    response_text
                )

                for index, chunk in enumerate(chunks):

                    if index == 0:

                        await message.reply(
                            chunk,
                            mention_author=False
                        )

                    else:

                        await message.channel.send(
                            chunk
                        )

            except Exception as error:

                # ------------------------------------------------
                # LOG ERROR KE RENDER
                # ------------------------------------------------

                print("")
                print("=" * 60)
                print("GEMINI / DISCORD ERROR")
                print("=" * 60)
                print(repr(error))
                print("=" * 60)
                print("")

                await message.reply(
                    "⚠️ Terjadi kendala teknis saat "
                    "memproses pesan. Silakan coba lagi.",
                    mention_author=False
                )


# ============================================================
# KEEP ALIVE
# ============================================================

keep_alive()


# ============================================================
# START BOT
# ============================================================

print("Memulai Discord Gemini AI...")

client.run(DISCORD_TOKEN)
