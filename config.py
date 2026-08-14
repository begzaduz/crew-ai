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
TOKEN          = os.getenv('TOKEN', '')
CHANNEL        = os.getenv('CHANNEL', '@Inglizfutbol')
ADMIN_IDS      = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

# ── Gemini ──────────────────────────────────────────────
GEMINI_KEY   = os.getenv('GEMINI_KEY', '')
GEMINI_MODEL = 'gemini-3.6-flash'

# ── Grok (xAI) — Gemini kunlik RPD kvotasi tugaganda ZAXIRA (fallback) ──
# Ixtiyoriy: bo'sh bo'lsa, fallback ishlamaydi (avvalgi xatti-harakat —
# 429 kelsa darhol xato ko'tariladi). GROK_KEY sozlansa, gemini_call()
# Gemini 429/RESOURCE_EXHAUSTED xatosida avtomatik Grok'ga o'tadi.
GROK_KEY   = os.getenv('GROK_KEY', '')
GROK_MODEL = 'grok-4.1-fast'

# ── Serverning o'z ochiq (public) manzili ──────────────────
# Dashboard'dan yuklangan rasmlar o'z DB'imizda saqlanadi va shu manzil
# orqali (masalan https://xxx.up.railway.app/api/image/42) tashqariga
# (jumladan Telegram'ga, rasm yuborilganda) ochiladi. Sozlanmasa,
# yuklangan rasmlar Telegram'ga yuborilganda ishlamaydi (URL nisbiy
# qoladi) — lekin bu ixtiyoriy, boshqa hech narsani buzmaydi.
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')

# ── Studio Lab Dashboard autentifikatsiyasi (Basic Auth) ──
# /studio va /api/studio/* shu login+parol bilan himoyalanadi.
DASHBOARD_USER     = os.getenv('DASHBOARD_USER', 'admin')
DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', '')

# ── Server ────────────────────────────────────────────────
PORT = int(os.getenv('PORT', 8080))

# ── Bot davri ─────────────────────────────────────────────
INTERVAL = 4 * 60 * 60
ARTICLE_MAX_AGE_HOURS = 48
DAILY_POST_BUDGET = 6

# ── Scoring ───────────────────────────────────────────────
MIN_SCORE = 20

# ── Validate ──────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError('TOKEN .env da topilmadi!')
if not GEMINI_KEY:
    raise RuntimeError('GEMINI_KEY .env da topilmadi!')
if not ADMIN_IDS:
    raise RuntimeError('ADMIN_IDS .env da topilmadi! (Telegram ID raqamlar, vergul bilan)')
if not DASHBOARD_PASSWORD:
    raise RuntimeError('DASHBOARD_PASSWORD .env da topilmadi! (Studio Lab Dashboard himoyasi uchun kerak)')
