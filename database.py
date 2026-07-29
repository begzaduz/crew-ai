import logging
import os

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

log = logging.getLogger(__name__)
# published_posts jadvali, save_post(), get_recent_posts() — mini-app uchun.
# projects / workflows / data_sources — Studio Lab Dashboard uchun (DB-driven config).

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
            # Gemini API kunlik chaqiruv sanoqchisi (RPD kvotasini oldindan
            # boshqarish uchun). Sana Pacific Time bo'yicha saqlanadi.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS daily_api_usage (
                    usage_date TEXT PRIMARY KEY,
                    call_count INTEGER DEFAULT 0
                )
            ''')

            # ── Studio Lab Dashboard uchun: loyihalar ────────────────
            # MUHIM: bu jadvallar ba'zi repo'larda studio_schema.py orqali
            # ALLAQACHON yaratilgan bo'lishi mumkin (turli ustunlar bilan).
            # "CREATE TABLE IF NOT EXISTS" jadval mavjud bo'lsa hech narsa
            # qilmaydi — shuning uchun yangi ustunlarni har doim ALTER TABLE
            # ADD COLUMN IF NOT EXISTS orqali qo'shamiz. Bu ham yangi, ham
            # eski (boshqacha sxemadagi) jadval uchun xavfsiz.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY
                )
            ''')
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS slug TEXT")
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS name TEXT")
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug)")

            # Har bir loyihaning workflow konfiguratsiyasi (terminologiya,
            # klub taxalluslari, kanal nomi, uslub va h.k.) JSONB'da saqlanadi.
            # Pipeline runtime'da shu yerdan o'qiydi — kod ichida qotib
            # qolgan qiymatlar Dashboard'dan tahrirlanganda darhol ta'sir qiladi.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER
                )
            ''')
            cur.execute("ALTER TABLE workflows ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'rss_news'")
            cur.execute("ALTER TABLE workflows ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}'::jsonb")
            cur.execute("ALTER TABLE workflows ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workflows_project_type ON workflows(project_id, type)")

            # Har bir loyihaning RSS (yoki boshqa turdagi) manbalari.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS data_sources (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER
                )
            ''')
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS url TEXT")
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'rss'")
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
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


# ── Kunlik Gemini API kvota sanoqchisi ────────────────────
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


# ── Studio Lab: loyihalar (projects) ──────────────────────
def get_project_by_slug(slug: str) -> dict | None:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM projects WHERE slug=%s', (slug,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


def get_or_create_project(slug: str, name: str) -> dict:
    existing = get_project_by_slug(slug)
    if existing:
        return existing
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''INSERT INTO projects (slug, name) VALUES (%s, %s)
                   ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                   RETURNING *''',
                (slug, name),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    finally:
        _put_conn(conn)


# ── Studio Lab: workflow config (terminology, nicknames, tone...) ─
def get_workflow_config(project_id: int, wf_type: str = 'rss_news') -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT config FROM workflows WHERE project_id=%s AND type=%s',
                (project_id, wf_type),
            )
            row = cur.fetchone()
            return row[0] if row else {}
    finally:
        _put_conn(conn)


def set_workflow_config(project_id: int, config: dict, wf_type: str = 'rss_news') -> dict:
    """Config'ni to'liq almashtiradi (overwrite)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO workflows (project_id, type, config)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (project_id, type)
                   DO UPDATE SET config = EXCLUDED.config, updated_at = NOW()
                   RETURNING config''',
                (project_id, wf_type, psycopg2.extras.Json(config)),
            )
            result = cur.fetchone()[0]
        conn.commit()
        return result
    finally:
        _put_conn(conn)


def update_workflow_config(project_id: int, patch: dict, wf_type: str = 'rss_news') -> dict:
    """Config ustiga patch'ni yuqori darajadagi kalitlar bo'yicha birlashtiradi
    (jsonb ||). Masalan {"terminology": {...}} yuborilsa, faqat 'terminology'
    kaliti almashadi, boshqa kalitlar (nicknames, channel_tag...) tegilmaydi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO workflows (project_id, type, config)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (project_id, type)
                   DO UPDATE SET config = workflows.config || EXCLUDED.config, updated_at = NOW()
                   RETURNING config''',
                (project_id, wf_type, psycopg2.extras.Json(patch)),
            )
            result = cur.fetchone()[0]
        conn.commit()
        return result
    finally:
        _put_conn(conn)


# ── Studio Lab: data_sources (RSS manbalar) ───────────────
def get_data_sources(project_id: int, active_only: bool = False) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if active_only:
                cur.execute(
                    'SELECT * FROM data_sources WHERE project_id=%s AND active=TRUE ORDER BY id',
                    (project_id,),
                )
            else:
                cur.execute(
                    'SELECT * FROM data_sources WHERE project_id=%s ORDER BY id',
                    (project_id,),
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def add_data_source(project_id: int, url: str, source_type: str = 'rss') -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''INSERT INTO data_sources (project_id, url, type)
                   VALUES (%s, %s, %s) RETURNING *''',
                (project_id, url.strip(), source_type),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    finally:
        _put_conn(conn)


def set_data_source_active(source_id: int, active: bool) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE data_sources SET active=%s WHERE id=%s', (active, source_id))
        conn.commit()
    finally:
        _put_conn(conn)


def delete_data_source(source_id: int) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM data_sources WHERE id=%s', (source_id,))
        conn.commit()
    finally:
        _put_conn(conn)


# ── Studio Lab: bir martalik seed (loyiha bo'sh bo'lsa to'ldiradi) ─
def seed_project_if_empty(
    slug: str,
    name: str,
    default_config: dict,
    default_sources: list[str],
    wf_type: str = 'rss_news',
) -> dict:
    """Loyiha mavjud bo'lmasa yaratadi: project + workflow config + data_sources.
    Loyiha allaqachon mavjud bo'lsa va config/manbalar allaqachon to'ldirilgan
    bo'lsa, HECH NARSANI qayta yozmaydi — chunki foydalanuvchi Dashboard'da
    ularni allaqachon o'zgartirgan bo'lishi mumkin."""
    project = get_or_create_project(slug, name)
    pid = project['id']

    if not get_workflow_config(pid, wf_type):
        set_workflow_config(pid, default_config, wf_type)
        log.info(f'[DB] Workflow config seed qilindi (project={slug}).')

    if not get_data_sources(pid):
        for url in default_sources:
            add_data_source(pid, url)
        log.info(f'[DB] {len(default_sources)} ta data_source seed qilindi (project={slug}).')

    return project
