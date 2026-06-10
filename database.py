import logging
import os

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

log = logging.getLogger(__name__)

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
