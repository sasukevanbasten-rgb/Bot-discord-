import os
import asyncio
import logging
import traceback
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
# LOGGING
# ============================================================

# konfigurasi logging: tampilkan di console dan simpan ke file bot.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


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

            logger.exception("Error reading attachment: %s", error)


    return contents


# ============================================================
# GEMINI REQUEST
# ============================================================

async def ask_gemini(contents):

    try:
        response = await asyncio.to_thread(
            gemini.models.generate_content,
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )
    except Exception as e:
        logger.exception("[GEMINI CALL ERROR] %s", e)
        # Log full traceback to file (already handled by logger.exception)
        return "⚠️ Gemini gagal memproses permintaan (error koneksi / API)."

    # --------------------------------------------------------
    # RESPONSE TEXT
    # --------------------------------------------------------

    try:
        text = getattr(response, "text", None)

        if text:
            return text.strip()

        # --------------------------------------------------------
        # FALLBACK
        # --------------------------------------------------------

        for candidate in getattr(response, "candidates", []) or []:

            if not getattr(candidate, "content", None):
                continue

            for part in getattr(candidate.content, "parts", []) or []:

                if getattr(part, "text", None):

                    return part.text.strip()

    except Exception as e:
        logger.exception("[GEMINI RESPONSE PARSE ERROR] %s", e)
        return "⚠️ Gemini merespons tapi tidak bisa diproses (format tak terduga)."

    return (
        "Gemini menerima pesan, tetapi "
        "tidak menghasilkan jawaban teks."
    )


# ============================================================
# BOT READY
# ============================================================

@discord_bot.event
async def on_ready():

    logger.info("%s", """

============================================================
          DISCORD GEMINI AI BOT
============================================================

""")

    logger.info("Bot       : %s", discord_bot.user)
    logger.info("Bot ID    : %s", discord_bot.user.id)
    logger.info("Model     : %s", MODEL_NAME)
    logger.info("Mode      : AUTO CHAT")
    logger.info("Image     : ENABLED")
    logger.info("Status    : ONLINE")


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

            try:
                contents = await prepare_contents(message)
                logger.info("prepare_contents succeeded, %d parts", len(contents))
            except Exception as e:
                logger.exception("prepare_contents failed: %s", e)
                await message.reply(
                    "⚠️ Terjadi kesalahan saat memproses lampiran/pesan.",
                    mention_author=False
                )
                return

            if not contents:
                logger.info("No contents to process (empty after prepare_contents)")
                return

            # ------------------------------------------------
            # GEMINI
            # ------------------------------------------------

            try:
                answer = await ask_gemini(contents)
                if isinstance(answer, str):
                    logger.info("ask_gemini returned %d chars", len(answer))
                else:
                    logger.info("ask_gemini returned non-str response: %s", type(answer))
            except Exception as e:
                logger.exception("ask_gemini call failed: %s", e)
                await message.reply(
                    "⚠️ Gemini gagal memproses permintaan (error API/koneksi).",
                    mention_author=False
                )
                return


            # ------------------------------------------------
            # DISCORD
            # ------------------------------------------------

            try:
                messages = split_message(answer)

                for index, text in enumerate(messages):

                    if index == 0:

                        await message.reply(
                            text,
                            mention_author=False
                        )

                    else:

                        await message.channel.send(
                            text
                        )

                logger.info("Sent reply messages (%d parts)", len(messages))

            except Exception as e:
                logger.exception("Failed to send reply messages: %s", e)
                try:
                    await message.channel.send("⚠️ Gagal mengirim balasan ke channel.")
                except Exception:
                    logger.exception("Also failed to send fallback message to channel")

        except Exception:

            logger.exception("Unexpected error in on_message")

            try:
                await message.reply(
                    "⚠️ Gemini sedang mengalami kendala. Coba kirim pesan lagi.",
                    mention_author=False
                )
            except Exception:
                logger.exception("Failed to send final fallback reply")


# ============================================================
# KEEP ALIVE
# ============================================================

keep_alive()


# ============================================================
# START BOT
# ============================================================

logger.info("Memulai Discord Gemini AI Bot...")

discord_bot.run(
    DISCORD_TOKEN
)
