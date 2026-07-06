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
TOKEN        = os.getenv('TOKEN', '')
CHANNEL      = os.getenv('CHANNEL', '@Inglizfutbol')
ADMIN_IDS    = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

# ── Gemini ──────────────────────────────────────────────
GEMINI_KEY   = os.getenv('GEMINI_KEY', '')
GEMINI_MODEL = 'gemini-2.5-flash'

# ── Server ────────────────────────────────────────────────
PORT         = int(os.getenv('PORT', 8080))

# ── Bot davri ─────────────────────────────────────────────
INTERVAL     = 30 * 60  # 30 daqiqa
ARTICLE_MAX_AGE_HOURS = 48

# ── Scoring ───────────────────────────────────────────────
MIN_SCORE    = 15   # 2 ta kalit so'z yoki 1 kalit so'z + breaking bonus yetarli

# ── Validate ──────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError('TOKEN .env da topilmadi!')
if not GEMINI_KEY:
    raise RuntimeError('GEMINI_KEY .env da topilmadi!')
if not ADMIN_IDS:
    raise RuntimeError('ADMIN_IDS .env da topilmadi! (Telegram ID raqamlar, vergul bilan)')
