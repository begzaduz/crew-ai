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
GEMINI_MODEL = 'gemini-2.5-flash-lite'

# ── Football-data.org (Mini App: O'yinlar + Jadval bo'limlari) ─
# Bepul API key: https://www.football-data.org/client/register
# Kalit bo'lmasa, mini app "O'yinlar" va "Jadval" bo'limlari bo'sh xabar ko'rsatadi,
# lekin bot ishlashda davom etadi (bu majburiy emas).
FOOTBALL_DATA_KEY = os.getenv('FOOTBALL_DATA_KEY', '')

# ── Server ────────────────────────────────────────────────
PORT         = int(os.getenv('PORT', 8080))

# ── Bot davri ─────────────────────────────────────────────
INTERVAL     = 4 * 60 * 60  # 4 soat
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
if not WEBHOOK_SECRET:
    raise RuntimeError('WEBHOOK_SECRET .env da topilmadi! (o\'zingiz tasodifiy uzun matn o\'ylab toping)')
