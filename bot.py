import os
import asyncio
import discord

from google import genai
from google.genai import types

from keep_alive import keep_alive


# ============================================================
# CONFIG
# ============================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# VALIDASI ENVIRONMENT
# ============================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN tidak ditemukan di Render Environment Variables."
    )

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY tidak ditemukan di Render Environment Variables."
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_PROMPT = """
Kamu adalah Asisten AI Creative Director profesional.

Kamu membantu pengguna dalam:

- TikTok Affiliate
- TikTok Shop
- UGC
- Content marketing
- Copywriting
- Storytelling
- Hook
- Script video
- Storyboard
- Creative direction
- Analisis produk
- Strategi pemasaran
- Prompt image AI
- Prompt video AI
- Ide konten
- Optimasi konten sosial media

Gunakan bahasa Indonesia yang natural, ramah, profesional,
cerdas, kreatif, dan praktis.

Pengguna tidak perlu menggunakan command khusus.
Pengguna cukup berbicara secara natural.

Jika permintaan jelas, langsung kerjakan.

Jika pengguna meminta ide, berikan ide yang praktis.

Jika pengguna meminta script, buat script yang siap digunakan.

Jika pengguna meminta storyboard, buat storyboard yang jelas.

Jika pengguna meminta prompt AI, buat prompt yang detail,
jelas, konsisten, dan siap digunakan.

Jika pengguna mengirim gambar produk:

- Analisis gambar.
- Jelaskan hanya informasi yang benar-benar terlihat.
- Jangan mengarang spesifikasi produk.
- Jangan mengarang harga.
- Jangan mengarang kandungan.
- Jangan mengarang klaim kesehatan.
- Jangan mengarang jumlah penjualan atau rating.

Gunakan informasi yang tersedia untuk membuat ide konten,
script, storyboard, hook, CTA, atau prompt AI.

Untuk konten TikTok Affiliate, prioritaskan:

1. Hook.
2. Masalah.
3. Solusi.
4. Produk.
5. Demonstrasi.
6. Manfaat.
7. Bukti jika tersedia.
8. CTA.

Jika pengguna meminta durasi video tertentu,
ikuti durasi tersebut.

Jaga konsistensi karakter, produk, lokasi, pakaian,
properti, kamera, lighting, dan kontinuitas scene
jika detail tersebut sudah diberikan pengguna.

Jangan membocorkan API key atau informasi rahasia server.

Jika pengguna hanya menyapa, jawab secara natural.
"""


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

intents.message_content = True

discord_bot = discord.Client(
    intents=intents
)


# ============================================================
# MEMECAH PESAN PANJANG
# ============================================================

def split_message(text, limit=1900):

    if not text:
        return [
            "Maaf, Gemini tidak memberikan jawaban."
        ]

    result = []

    while len(text) > limit:

        position = text.rfind(
            "\n",
            0,
            limit
        )

        if position == -1:

            position = text.rfind(
                " ",
                0,
                limit
            )

        if position == -1:

            position = limit

        result.append(
            text[:position].strip()
        )

        text = text[position:].strip()

    if text:
        result.append(text)

    return result


# ============================================================
# SIAPKAN CONTENT GEMINI
# ============================================================

async def prepare_contents(message):

    contents = []

    # --------------------------------------------------------
    # TEKS
    # --------------------------------------------------------

    if message.content.strip():

        contents.append(
            message.content.strip()
        )


    # --------------------------------------------------------
    # GAMBAR
    # --------------------------------------------------------

    image_count = 0

    for attachment in message.attachments:

        content_type = (
            attachment.content_type or ""
        )

        if not content_type.startswith("image/"):
            continue

        if image_count >= 5:
            break

        try:

            image_bytes = await attachment.read()

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=content_type
            )

            contents.append(
                image_part
            )

            image_count += 1

        except Exception as error:

            print(
                f"[IMAGE ERROR] {repr(error)}"
            )


    return contents


# ============================================================
# GEMINI REQUEST
# ============================================================

async def ask_gemini(contents):

    response = await asyncio.to_thread(
        gemini.models.generate_content,
        model=MODEL_NAME,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
    )

    # --------------------------------------------------------
    # RESPONSE TEXT
    # --------------------------------------------------------

    text = getattr(
        response,
        "text",
        None
    )

    if text:

        return text.strip()


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    try:

        for candidate in response.candidates:

            if not candidate.content:
                continue

            for part in candidate.content.parts:

                if part.text:

                    return part.text.strip()

    except Exception:
        pass


    return (
        "Gemini menerima pesan, tetapi "
        "tidak menghasilkan jawaban teks."
    )


# ============================================================
# BOT READY
# ============================================================

@discord_bot.event
async def on_ready():

    print("")
    print("=" * 60)
    print("          DISCORD GEMINI AI BOT")
    print("=" * 60)

    print(
        f"Bot       : {discord_bot.user}"
    )

    print(
        f"Bot ID    : {discord_bot.user.id}"
    )

    print(
        f"Model     : {MODEL_NAME}"
    )

    print(
        "Mode      : AUTO CHAT"
    )

    print(
        "Image     : ENABLED"
    )

    print(
        "Status    : ONLINE"
    )

    print("=" * 60)
    print("")


# ============================================================
# PESAN MASUK
# ============================================================

@discord_bot.event
async def on_message(message):

    # --------------------------------------------------------
    # Jangan balas bot
    # --------------------------------------------------------

    if message.author.bot:
        return


    # --------------------------------------------------------
    # Abaikan pesan kosong
    # --------------------------------------------------------

    if (
        not message.content.strip()
        and not message.attachments
    ):

        return


    # --------------------------------------------------------
    # TYPING
    # --------------------------------------------------------

    async with message.channel.typing():

        try:

            # ------------------------------------------------
            # SIAPKAN INPUT
            # ------------------------------------------------

            contents = await prepare_contents(
                message
            )

            if not contents:

                return


            # ------------------------------------------------
            # GEMINI
            # ------------------------------------------------

            answer = await ask_gemini(
                contents
            )


            # ------------------------------------------------
            # DISCORD
            # ------------------------------------------------

            messages = split_message(
                answer
            )

            for index, text in enumerate(
                messages
            ):

                if index == 0:

                    await message.reply(
                        text,
                        mention_author=False
                    )

                else:

                    await message.channel.send(
                        text
                    )


        except Exception as error:

            # =================================================
            # ERROR DETAIL
            # =================================================

            print("")
            print("=" * 70)
            print("                  GEMINI ERROR")
            print("=" * 70)

            print(
                "TYPE :",
                type(error).__name__
            )

            print(
                "ERROR:",
                str(error)
            )

            print("=" * 70)
            print("")


            # ------------------------------------------------
            # Pesan user
            # ------------------------------------------------

            await message.reply(
                "⚠️ Gemini sedang mengalami kendala. "
                "Coba kirim pesan lagi.",
                mention_author=False
            )


# ============================================================
# KEEP ALIVE
# ============================================================

keep_alive()


# ============================================================
# START BOT
# ============================================================

print(
    "Memulai Discord Gemini AI Bot..."
)

discord_bot.run(
    DISCORD_TOKEN
)
