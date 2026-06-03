import sqlite3
import logging
import threading

log = logging.getLogger(__name__)

DB_PATH = 'news_cache.db'

# Har bir thread uchun alohida connection — check_same_thread=False xavfini yo'q qiladi
_local = threading.local()

def _get_conn() -> sqlite3.Connection:
    if not getattr(_local, 'conn', None):
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute('''
            CREATE TABLE IF NOT EXISTS processed_articles (
                url          TEXT PRIMARY KEY,
                title        TEXT,
                score        INTEGER DEFAULT 0,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        _local.conn.commit()
    return _local.conn


def is_processed(url: str) -> bool:
    cur = _get_conn().execute(
        'SELECT 1 FROM processed_articles WHERE url=?', (url,)
    )
    return cur.fetchone() is not None


def mark_processed(url: str, title: str = '', score: int = 0) -> None:
    conn = _get_conn()
    conn.execute(
        'INSERT OR IGNORE INTO processed_articles (url, title, score) VALUES (?,?,?)',
        (url, title, score),
    )
    conn.commit()


def clear_cache() -> None:
    conn = _get_conn()
    conn.execute('DELETE FROM processed_articles')
    conn.commit()
    log.info('[DB] Kesh tozalandi.')


def get_stats() -> tuple[int, float]:
    cur = _get_conn().execute(
        'SELECT COUNT(*), COALESCE(AVG(score), 0) FROM processed_articles'
    )
    row = cur.fetchone()
    return int(row[0]), round(float(row[1]))
