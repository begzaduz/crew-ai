import logging
import os

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

log = logging.getLogger(__name__)
# published_posts jadvali, save_post(), get_recent_posts() — mini-app uchun.

DATABASE_URL = os.getenv('DATABASE_URL', '')

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL .env da topilmadi!')

# Thread-safe connection pool (min 1, max 10)
_pool = ThreadedConnectionPool(1, 10, DATABASE_URL)


def _get_conn():
    return _pool.getconn()

def _put_conn(conn):
    _pool.putconn(conn)


def init_db() -> None:
    """Jadval yo'q bo'lsa yaratadi. Dastur start da bir marta chaqiriladi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS processed_articles (
                    url          TEXT PRIMARY KEY,
                    title        TEXT,
                    score        INTEGER DEFAULT 0,
                    processed_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            # Mini-app uchun: kanalga chiqqan har bir postning to'liq nusxasi
            cur.execute('''
                CREATE TABLE IF NOT EXISTS published_posts (
                    id           SERIAL PRIMARY KEY,
                    url          TEXT,
                    title        TEXT,
                    post_text    TEXT,
                    image_url    TEXT,
                    published_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_published_posts_date
                ON published_posts (published_at DESC)
            ''')
            # YANGI: Gemini API kunlik chaqiruv sanoqchisi (RPD kvotasini
            # oldindan boshqarish uchun). Sana Pacific Time bo'yicha
            # saqlanadi, chunki Google RPD kvotasi shu vaqt zonasida
            # yarim tunda tiklanadi.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS daily_api_usage (
                    usage_date TEXT PRIMARY KEY,
                    call_count INTEGER DEFAULT 0
                )
            ''')
        conn.commit()
        log.info('[DB] PostgreSQL jadval tayyor.')
    finally:
        _put_conn(conn)


def is_processed(url: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM processed_articles WHERE url=%s', (url,))
            return cur.fetchone() is not None
    finally:
        _put_conn(conn)


def mark_processed(url: str, title: str = '', score: int = 0) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO processed_articles (url, title, score)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (url) DO NOTHING''',
                (url, title, score),
            )
        conn.commit()
    finally:
        _put_conn(conn)


def clear_cache() -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM processed_articles')
        conn.commit()
        log.info('[DB] Kesh tozalandi.')
    finally:
        _put_conn(conn)


def get_stats() -> tuple[int, float]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*), COALESCE(AVG(score), 0) FROM processed_articles')
            row = cur.fetchone()
            return int(row[0]), round(float(row[1]))
    finally:
        _put_conn(conn)


# ── Mini App uchun ─────────────────────────────────────────
def save_post(url: str | None, title: str, post_text: str, image_url: str | None) -> None:
    """Kanalga yuborilgan har bir postni saqlaydi (mini app shundan o'qiydi)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO published_posts (url, title, post_text, image_url)
                   VALUES (%s, %s, %s, %s)''',
                (url, title, post_text, image_url),
            )
        conn.commit()
    except Exception as e:
        log.error(f'[DB] save_post xato: {e}')
    finally:
        _put_conn(conn)


def get_recent_posts(limit: int = 50) -> list[dict]:
    """Mini app uchun so'nggi postlar ro'yxati (eng yangisi birinchi)."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT id, url, title, post_text, image_url, published_at
                   FROM published_posts
                   ORDER BY published_at DESC
                   LIMIT %s''',
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        _put_conn(conn)


# ── YANGI: Kunlik Gemini API kvota sanoqchisi ─────────────
def _today_pacific() -> str:
    """Joriy sanani Pacific Time bo'yicha 'YYYY-MM-DD' shaklida qaytaradi
    (Gemini RPD kvotasi shu vaqt zonasida yarim tunda tiklanadi)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT (NOW() AT TIME ZONE 'America/Los_Angeles')::date::text")
            return cur.fetchone()[0]
    finally:
        _put_conn(conn)


def get_today_api_calls() -> int:
    """Bugungi (Pacific Time) Gemini API chaqiruvlar sonini qaytaradi."""
    today = _today_pacific()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT call_count FROM daily_api_usage WHERE usage_date = %s',
                (today,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        _put_conn(conn)


def increment_api_calls(n: int = 1) -> None:
    """Bugungi (Pacific Time) API chaqiruvlar sonini n ga oshiradi."""
    today = _today_pacific()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO daily_api_usage (usage_date, call_count)
                   VALUES (%s, %s)
                   ON CONFLICT (usage_date)
                   DO UPDATE SET call_count = daily_api_usage.call_count + %s''',
                (today, n, n),
            )
        conn.commit()
    except Exception as e:
        log.error(f'[DB] increment_api_calls xato: {e}')
    finally:
        _put_conn(conn)
