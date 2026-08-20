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
    raise RuntimeError("DISCORD_TOKEN belum ditemukan.")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY belum ditemukan.")


# ============================================================
# GEMINI
# ============================================================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Kamu adalah Asisten AI Creative Director profesional.

Keahlian utama:
- Strategi konten
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
- Ide pemasaran
- Optimasi konten

GAYA KOMUNIKASI:
- Gunakan bahasa Indonesia yang natural.
- Ramah, santai, profesional, dan kreatif.
- Jangan terlalu kaku.
- Jawaban harus praktis dan bisa langsung digunakan.
- Pahami percakapan sebelumnya dan pertahankan konteks.
- Jangan meminta pengguna menggunakan command tertentu.
- Pengguna cukup berbicara secara natural.

KONTEN AFFILIATE:
Prioritaskan:
1. Hook kuat.
2. Masalah atau kebutuhan penonton.
3. Solusi.
4. Perkenalan produk.
5. Demonstrasi.
6. Manfaat.
7. Bukti jika tersedia.
8. CTA natural.

Jangan mengarang spesifikasi produk.
Jika informasi tidak tersedia atau tidak terlihat dari gambar,
katakan dengan jelas.

GAMBAR:
Jika pengguna mengirim gambar produk:
- Analisis gambar terlebih dahulu.
- Identifikasi hal yang benar-benar terlihat.
- Jangan mengarang detail yang tidak terlihat.
- Berikan ide konten berdasarkan produk tersebut.

VIDEO:
Jika pengguna memberikan durasi:
- Hormati durasi tersebut.
- Jaga kontinuitas antar-scene.
- Jangan mengubah karakter atau produk yang sudah ditentukan.

PROMPT AI:
Jika pengguna meminta prompt:
- Buat prompt yang detail.
- Jaga konsistensi karakter.
- Jaga konsistensi produk.
- Jaga kontinuitas visual.
- Buat prompt siap digunakan.

PERCAKAPAN:
Anggap setiap pesan pengguna sebagai bagian dari percakapan.
Jika pengguna bertanya lanjutan seperti "yang tadi bagaimana?",
gunakan konteks percakapan yang tersedia.

Jika pengguna hanya menyapa,
jawab secara natural dan ramah.
"""


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

# WAJIB untuk membaca isi pesan Discord
intents.message_content = True

client = discord.Client(intents=intents)


# ============================================================
# BATAS PANJANG PESAN DISCORD
# ============================================================

def split_message(text, limit=1900):

    if not text:
        return ["Maaf, Gemini tidak memberikan respons."]

    chunks = []

    while len(text) > limit:

        split_at = text.rfind("\n", 0, limit)

        if split_at == -1:
            split_at = text.rfind(" ", 0, limit)

        if split_at == -1:
            split_at = limit

        chunks.append(
            text[:split_at].strip()
        )

        text = text[split_at:].strip()

    if text:
        chunks.append(text)

    return chunks


# ============================================================
# EVENT BOT ONLINE
# ============================================================

@client.event
async def on_ready():

    print("=" * 60)
    print("       DISCORD GEMINI AI")
    print("=" * 60)
    print(f"Bot    : {client.user}")
    print(f"ID     : {client.user.id}")
    print(f"Model  : {MODEL_NAME}")
    print("Mode   : AUTO CHAT")
    print("Status : ONLINE")
    print("=" * 60)


# ============================================================
# EVENT PESAN
# ============================================================

@client.event
async def on_message(message):

    # Jangan merespons bot lain / bot sendiri
    if message.author.bot:
        return

    # ========================================================
    # SEMUA PESAN MANUSIA AKAN DIPROSES
    # Tidak membutuhkan:
    # !buat
    # @mention
    # reply
    # ========================================================

    async with message.channel.typing():

        try:

            # ------------------------------------------------
            # AMBIL TEKS
            # ------------------------------------------------

            prompt_text = message.content.strip()

            # ------------------------------------------------
            # CONTENT GEMINI
            # ------------------------------------------------

            contents = []

            if prompt_text:
                contents.append(prompt_text)

            # ------------------------------------------------
            # PROSES GAMBAR
            # ------------------------------------------------

            image_count = 0

            for attachment in message.attachments:

                content_type = attachment.content_type or ""

                if content_type.startswith("image/"):

                    # Maksimal 5 gambar per pesan
                    if image_count >= 5:
                        break

                    image_bytes = await attachment.read()

                    image_part = types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=content_type
                    )

                    contents.append(image_part)

                    image_count += 1

            # ------------------------------------------------
            # JIKA PESAN BENAR-BENAR KOSONG
            # ------------------------------------------------

            if not contents:
                return

            # ------------------------------------------------
            # KIRIM KE GEMINI
            # ------------------------------------------------

            response = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                )
            )

            # ------------------------------------------------
            # AMBIL HASIL
            # ------------------------------------------------

            response_text = getattr(
                response,
                "text",
                None
            )

            if not response_text:

                response_text = (
                    "Maaf, saya belum bisa memberikan "
                    "jawaban untuk pesan tersebut."
                )

            # ------------------------------------------------
            # KIRIM KE DISCORD
            # ------------------------------------------------

            chunks = split_message(response_text)

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

            # Error lengkap hanya muncul di Render Logs
            print("=" * 60)
            print("ERROR")
            print(repr(error))
            print("=" * 60)

            await message.reply(
                "⚠️ Maaf, terjadi kendala teknis. "
                "Coba kirim pesan sekali lagi.",
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
