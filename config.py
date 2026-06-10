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

# ── Groq ──────────────────────────────────────────────────
GROQ_KEY     = os.getenv('GROQ_KEY', '')
GROQ_MODEL   = 'llama-3.3-70b-versatile'

# ── Server ────────────────────────────────────────────────
PORT         = int(os.getenv('PORT', 8080))

# ── Bot davri ─────────────────────────────────────────────
INTERVAL     = 30 * 60  # 30 daqiqa
ARTICLE_MAX_AGE_HOURS = 48

# ── Scoring ───────────────────────────────────────────────
MIN_SCORE    = 5

# ── Validate ──────────────────────────────────────────────
if not TOKEN:
    raise RuntimeError('TOKEN .env da topilmadi!')
if not GROQ_KEY:
    raise RuntimeError('GROQ_KEY .env da topilmadi!')
if not ADMIN_IDS:
    raise RuntimeError('ADMIN_IDS .env da topilmadi! (Telegram ID raqamlar, vergul bilan)')
