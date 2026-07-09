import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)

# ── Telegram ──────────────────────────────────────────────
TOKEN           = os.getenv('TOKEN', '')
CHANNEL         = os.getenv('CHANNEL', '@Inglizfutbol')
ADMIN_IDS       = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
WEBHOOK_SECRET  = os.getenv('WEBHOOK_SECRET', '')

# ── Gemini ──────────────────────────────────────────────
GEMINI_KEY   = os.getenv('GEMINI_KEY', '')
# ESLATMA: sifat testlarida 'gemini-2.5-flash' 'flash-lite'dan yaxshiroq
# natija bergan (tildagi nozik xatolar kamroq). Agar sifatni ustuvor
# qilsangiz, buni 'gemini-2.5-flash' ga qaytaring.
GEMINI_MODEL = 'gemini-2.5-flash-lite'

# ── Football-data.org (Mini App: O'yinlar + Jadval bo'limlari) ─
# Bepul API key: https://www.football-data.org/client/register
# Kalit bo'lmasa, mini app "O'yinlar" va "Jadval" bo'limlari bo'sh xabar ko'rsatadi,
# lekin bot ishlashda davom etadi (bu majburiy emas).
FOOTBALL_DATA_KEY = os.getenv('FOOTBALL_DATA_KEY', '')

# ── Server ────────────────────────────────────────────────
PORT = int(os.getenv('PORT', 8080))

# ── Bot davri va API kvotasi ──────────────────────────────
# Gemini free tier loyihada kunlik ~20 so'rov (RPD) bilan cheklangan.
# Pipeline 1 post uchun 3 ta chaqiruv sarflaydi (Researcher+Writer+Editor).
# 20 RPD / 3 = ~6 ta post/kun xavfsiz limit.
# INTERVAL = 4 soat => kuniga 6 marta avtomatik urinish = 18 ta chaqiruv,
# qolgan 2 chaqiruv (ya'ni ~0.6 post) qo'lda /yangilik testlash uchun bufer.
INTERVAL = 4 * 60 * 60          # 4 soat (sekundda)
ARTICLE_MAX_AGE_HOURS = 48      # 48 soatdan eski maqolalar e'tiborga olinmaydi

# Kunlik xavfsiz post byudjeti — kelajakda main.py/database.py'da
# sanoqchi (counter) qo'shib, shu songa yetganda avtomatik jarayonni
# to'xtatish mumkin, behuda 429 urinishlarining oldini olish uchun.
DAILY_POST_BUDGET = 6

# ── Scoring ───────────────────────────────────────────────
# MIN_SCORE past bo'lsa — ko'proq maqola o'tadi, lekin sifat pasayishi
# mumkin. MIN_SCORE yuqori bo'lsa — kamroq, lekin dolzarbroq maqolalar.
# 20 RPD cheklovi bilan MIN_SCORE'ni biroz oshirish tavsiya etiladi,
# toki har bir chaqiruv eng muhim yangilikka sarflansin.
MIN_SCORE = 20   # oldingi 15 dan oshirildi — faqat kuchli signalli maqolalar o'tadi

# ── Validate ──────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError('TOKEN .env da topilmadi!')
if not GEMINI_KEY:
    raise RuntimeError('GEMINI_KEY .env da topilmadi!')
if not ADMIN_IDS:
    raise RuntimeError('ADMIN_IDS .env da topilmadi! (Telegram ID raqamlar, vergul bilan)')
if not WEBHOOK_SECRET:
    raise RuntimeError('WEBHOOK_SECRET .env da topilmadi! (o\'zingiz tasodifiy uzun matn o\'ylab toping)')
