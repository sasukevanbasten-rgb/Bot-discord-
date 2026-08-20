import os
import asyncio
import discord
from google import genai
from google.genai import types

from keep_alive import keep_alive


# ============================================================
# KONFIGURASI ENVIRONMENT
# ============================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# VALIDASI API KEY
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
Kamu adalah Asisten AI Creative Director profesional milik pengguna.

Keahlian utama:
- Strategi konten digital
- TikTok Affiliate
- TikTok Shop
- UGC
- Storytelling
- Copywriting
- Hook viral
- Script video pendek
- Storyboard
- Prompt image AI
- Prompt video AI
- Ide konten produk
- Analisis foto produk
- Strategi pemasaran
- Optimasi konten agar lebih menarik dan berpotensi menghasilkan penjualan

GAYA KOMUNIKASI:
- Gunakan bahasa Indonesia natural.
- Ramah, profesional, kreatif, dan mudah dipahami.
- Jangan terlalu kaku.
- Berikan jawaban praktis yang bisa langsung digunakan.
- Jika pengguna meminta ide, berikan beberapa opsi terbaik.
- Jika pengguna meminta script, buat script yang siap dipakai.
- Jika pengguna meminta storyboard, susun secara terstruktur.
- Jika pengguna mengirim foto produk, analisis gambar tersebut terlebih dahulu.
- Jangan mengarang spesifikasi produk yang tidak terlihat atau tidak diberikan pengguna.
- Jika informasi produk tidak diketahui, katakan bahwa informasi tersebut belum tersedia.

UNTUK KONTEN AFFILIATE:
Prioritaskan:
1. Hook kuat.
2. Masalah atau kebutuhan penonton.
3. Perkenalan produk secara natural.
4. Demonstrasi atau manfaat.
5. Bukti/hasil jika tersedia.
6. CTA yang natural dan tidak terlalu memaksa.

Jika pengguna memberikan durasi video, hormati durasi tersebut.

Jika pengguna meminta prompt AI:
- Buat prompt yang detail.
- Jaga konsistensi karakter.
- Jaga konsistensi produk.
- Jaga kontinuitas antar-scene.
- Jangan mengubah detail yang sudah dikunci pengguna.

Jika pengguna hanya menyapa:
Jawab secara singkat dan ramah lalu tawarkan bantuan.
"""


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# ============================================================
# FUNGSI MEMECAH PESAN DISCORD
# Discord memiliki batas panjang pesan.
# ============================================================

def split_message(text, limit=1900):
    """
    Memecah teks panjang menjadi beberapa pesan
    agar aman dikirim ke Discord.
    """

    if not text:
        return ["Maaf, Gemini tidak memberikan respons."]

    chunks = []

    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)

        if split_at == -1:
            split_at = text.rfind(" ", 0, limit)

        if split_at == -1:
            split_at = limit

        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()

    if text:
        chunks.append(text)

    return chunks


# ============================================================
# CEK APAKAH PESAN DITUJUKAN KE BOT
# ============================================================

def should_respond(message):
    """
    Bot merespons jika:
    1. Pesan diawali !buat
    2. Bot di-mention
    3. Pesan merupakan reply terhadap bot
    """

    # !buat
    if message.content.lower().startswith("!buat"):
        return True

    # Mention bot
    if client.user and client.user in message.mentions:
        return True

    # Reply terhadap bot
    if (
        message.reference
        and message.reference.resolved
        and isinstance(message.reference.resolved, discord.Message)
        and client.user
        and message.reference.resolved.author == client.user
    ):
        return True

    return False


# ============================================================
# MEMBERSIHKAN PROMPT
# ============================================================

def clean_prompt(message):
    """
    Membersihkan command !buat dan mention bot
    dari prompt yang dikirim ke Gemini.
    """

    prompt = message.content.strip()

    # Hapus command !buat
    if prompt.lower().startswith("!buat"):
        prompt = prompt[5:].strip()

    # Hapus mention bot
    if client.user:
        prompt = prompt.replace(
            f"<@{client.user.id}>",
            ""
        )

        prompt = prompt.replace(
            f"<@!{client.user.id}>",
            ""
        )

    return prompt.strip()


# ============================================================
# EVENT BOT SIAP
# ============================================================

@client.event
async def on_ready():

    print("=" * 60)
    print("DISCORD GEMINI AI BOT")
    print("=" * 60)
    print(f"Bot       : {client.user}")
    print(f"Bot ID    : {client.user.id}")
    print(f"Model     : {MODEL_NAME}")
    print("Status    : ONLINE")
    print("=" * 60)


# ============================================================
# EVENT PESAN
# ============================================================

@client.event
async def on_message(message):

    # Jangan balas pesan bot sendiri
    if message.author == client.user:
        return

    # Abaikan jika bukan command/mention/reply
    if not should_respond(message):
        return

    async with message.channel.typing():

        try:

            # ------------------------------------------------
            # Ambil prompt
            # ------------------------------------------------

            prompt_text = clean_prompt(message)

            # Jika tidak ada teks dan tidak ada gambar
            if not prompt_text and not message.attachments:

                prompt_text = (
                    "Halo! Saya siap membantu sebagai "
                    "Creative Director AI. "
                    "Kamu bisa meminta ide konten, "
                    "script, storyboard, prompt AI, "
                    "atau mengirim foto produk."
                )

            # ------------------------------------------------
            # CONTENTS GEMINI
            # ------------------------------------------------

            contents = []

            # Tambahkan teks
            if prompt_text:
                contents.append(prompt_text)

            # ------------------------------------------------
            # PROSES GAMBAR
            # ------------------------------------------------

            image_count = 0

            for attachment in message.attachments:

                content_type = attachment.content_type or ""

                if content_type.startswith("image/"):

                    # Batasi jumlah gambar agar penggunaan API
                    # tetap terkendali.
                    if image_count >= 5:
                        break

                    image_bytes = await attachment.read()

                    contents.append(
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=content_type
                        )
                    )

                    image_count += 1

            # ------------------------------------------------
            # PANGGIL GEMINI
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
            # AMBIL RESPONSE
            # ------------------------------------------------

            response_text = getattr(response, "text", None)

            if not response_text:

                response_text = (
                    "Maaf, Gemini tidak menghasilkan jawaban "
                    "untuk permintaan tersebut."
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
                    await message.channel.send(chunk)

        except Exception as error:

            # Log error lengkap di Render
            print("=" * 60)
            print("ERROR GEMINI / DISCORD")
            print(repr(error))
            print("=" * 60)

            # Jangan tampilkan detail error mentah
            # kepada pengguna karena bisa membocorkan
            # informasi internal.
            await message.reply(
                "⚠️ Maaf, terjadi kendala saat memproses "
                "permintaan. Coba lagi beberapa saat.",
                mention_author=False
            )


# ============================================================
# KEEP ALIVE
# ============================================================

keep_alive()


# ============================================================
# JALANKAN BOT
# ============================================================

print("Memulai Discord Gemini AI Bot...")

client.run(DISCORD_TOKEN)
