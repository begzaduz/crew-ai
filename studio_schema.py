"""
studio_schema.py
─────────────────────────────────────────────────────────────
Studio Lab — ichki operatsion tizim uchun DB sxemasi.

MUHIM PRINSIP: bu sxema HECH QANDAY loyihaga (jumladan Ingliz
Futboli'ga) qattiq bog'lanmagan. Superside modeliga o'xshab:

    Project → Data Sources → AI Workflow → Assets → Review → Outputs

Har bir loyiha — shu umumiy jadvallarda bitta qator. Ingliz
Futboli — birinchi qator, mustasno emas. Kelajakda yangi loyiha
qo'shish = yangi qator qo'shish, yangi jadval yoki yangi kod EMAS.

Mavjud database.py'dagi connection pool qayta ishlatiladi —
yangi ulanish yaratilmaydi.
"""

import json
import logging

import psycopg2.extras

from database import _get_conn, _put_conn

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  SXEMA — jadval yaratish
# ═══════════════════════════════════════════════════════════
def init_studio_schema() -> None:
    """Studio Lab jadvallarini yaratadi (mavjud bo'lmasa). Dastur
    start'ida init_db() bilan birga bir marta chaqiriladi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:

            # ── PROJECTS — har bir mijoz/loyiha shu yerda bitta qator ──
            cur.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id           SERIAL PRIMARY KEY,
                    slug         TEXT UNIQUE NOT NULL,   -- masalan 'ingliz-futboli'
                    name         TEXT NOT NULL,           -- ko'rinadigan nom
                    client_name  TEXT,                    -- tashqi mijoz nomi (ichki loyiha bo'lsa NULL)
                    status       TEXT NOT NULL DEFAULT 'active',  -- active / paused / completed
                    start_date   DATE DEFAULT CURRENT_DATE,
                    end_date     DATE,                    -- xizmat muddati tugashi, davom etsa NULL
                    created_at   TIMESTAMPTZ DEFAULT NOW()
                )
            ''')

            # ── DATA SOURCES — loyihaning kirish manbalari ──
            cur.execute('''
                CREATE TABLE IF NOT EXISTS data_sources (
                    id          SERIAL PRIMARY KEY,
                    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    type        TEXT NOT NULL,             -- 'rss' / 'api' / 'manual' / 'pdf' / 'gdocs'
                    name        TEXT NOT NULL,              -- ko'rinadigan nom, masalan "The Guardian"
                    config      JSONB NOT NULL DEFAULT '{}', -- {"url": "..."} yoki {"feeds": [...]}
                    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_data_sources_project
                ON data_sources (project_id)
            ''')

            # ── WORKFLOWS — AI pipeline sozlamalari (Brand Brain shu yerda) ──
            cur.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id             SERIAL PRIMARY KEY,
                    project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    workflow_type  TEXT NOT NULL,           -- 'content_production' (Research+Writer+Editor)
                    config         JSONB NOT NULL DEFAULT '{}',
                    -- config namunasi:
                    -- {
                    --   "language": "uz-latin",
                    --   "tone": "professional sport journalism",
                    --   "terminology": {"Manchester City": "Manchester Siti", ...},
                    --   "banned_phrases": [...],
                    --   "model": "gemini-2.5-flash"
                    -- }
                    created_at     TIMESTAMPTZ DEFAULT NOW(),
                    updated_at     TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_workflows_project
                ON workflows (project_id)
            ''')

            # ── ASSETS — pipeline orqali ishlab chiqarilgan kontent ──
            cur.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id           SERIAL PRIMARY KEY,
                    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    source_url   TEXT,                      -- qaysi manba maqoladan kelgan
                    type         TEXT NOT NULL DEFAULT 'text',  -- 'text' / 'image'
                    title        TEXT,
                    content      TEXT,
                    score        INTEGER DEFAULT 0,
                    status       TEXT NOT NULL DEFAULT 'draft',  -- draft / approved / rejected / published
                    created_at   TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_assets_project_status
                ON assets (project_id, status)
            ''')

            # ── REVIEWS — har bir asset uchun tekshiruv tarixi ──
            cur.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id          SERIAL PRIMARY KEY,
                    asset_id    INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                    reviewer    TEXT NOT NULL,               -- 'ai:editor' yoki admin nomi
                    decision    TEXT NOT NULL,                -- 'approved' / 'rejected' / 'fixed'
                    notes       TEXT,
                    reviewed_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_reviews_asset
                ON reviews (asset_id)
            ''')

            # ── OUTPUTS — loyihaning chiqish kanallari ──
            cur.execute('''
                CREATE TABLE IF NOT EXISTS outputs (
                    id            SERIAL PRIMARY KEY,
                    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    channel_type  TEXT NOT NULL,             -- 'telegram' / 'instagram' / 'linkedin' / 'blog'
                    name          TEXT NOT NULL,              -- masalan "@Inglizfutbol"
                    config        JSONB NOT NULL DEFAULT '{}', -- {"channel": "@Inglizfutbol"}
                    enabled       BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at    TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_outputs_project
                ON outputs (project_id)
            ''')

        conn.commit()
        log.info('[Studio] Sxema tayyor — projects/data_sources/workflows/assets/reviews/outputs.')
    finally:
        _put_conn(conn)


# ═══════════════════════════════════════════════════════════
#  PROJECTS
# ═══════════════════════════════════════════════════════════
def create_project(slug: str, name: str, client_name: str | None = None) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO projects (slug, name, client_name)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                   RETURNING id''',
                (slug, name, client_name),
            )
            project_id = cur.fetchone()[0]
        conn.commit()
        return project_id
    finally:
        _put_conn(conn)


def list_projects() -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM projects ORDER BY created_at ASC')
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def get_project_by_slug(slug: str) -> dict | None:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM projects WHERE slug = %s', (slug,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


# ═══════════════════════════════════════════════════════════
#  DATA SOURCES
# ═══════════════════════════════════════════════════════════
def add_data_source(project_id: int, type_: str, name: str, config: dict) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO data_sources (project_id, type, name, config)
                   VALUES (%s, %s, %s, %s) RETURNING id''',
                (project_id, type_, name, json.dumps(config)),
            )
            source_id = cur.fetchone()[0]
        conn.commit()
        return source_id
    finally:
        _put_conn(conn)


def list_data_sources(project_id: int, enabled_only: bool = False) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            q = 'SELECT * FROM data_sources WHERE project_id = %s'
            params: tuple = (project_id,)
            if enabled_only:
                q += ' AND enabled = TRUE'
            cur.execute(q + ' ORDER BY id', params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def set_data_source_enabled(source_id: int, enabled: bool) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE data_sources SET enabled = %s WHERE id = %s', (enabled, source_id))
        conn.commit()
    finally:
        _put_conn(conn)


# ═══════════════════════════════════════════════════════════
#  WORKFLOWS  (Brand Brain shu yerda saqlanadi)
# ═══════════════════════════════════════════════════════════
def upsert_workflow(project_id: int, workflow_type: str, config: dict) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO workflows (project_id, workflow_type, config)
                   VALUES (%s, %s, %s) RETURNING id''',
                (project_id, workflow_type, json.dumps(config)),
            )
            workflow_id = cur.fetchone()[0]
        conn.commit()
        return workflow_id
    finally:
        _put_conn(conn)


def get_workflow(project_id: int, workflow_type: str) -> dict | None:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT * FROM workflows WHERE project_id = %s AND workflow_type = %s
                   ORDER BY id DESC LIMIT 1''',
                (project_id, workflow_type),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


def update_workflow_config(workflow_id: int, config: dict) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE workflows SET config = %s, updated_at = NOW() WHERE id = %s',
                (json.dumps(config), workflow_id),
            )
        conn.commit()
    finally:
        _put_conn(conn)


# ═══════════════════════════════════════════════════════════
#  ASSETS + REVIEWS  (Navbat / Tekshiruv)
# ═══════════════════════════════════════════════════════════
def create_asset(project_id: int, source_url: str | None, title: str,
                  content: str, score: int = 0, type_: str = 'text') -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO assets (project_id, source_url, type, title, content, score)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
                (project_id, source_url, type_, title, content, score),
            )
            asset_id = cur.fetchone()[0]
        conn.commit()
        return asset_id
    finally:
        _put_conn(conn)


def list_assets(project_id: int, status: str | None = None) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute(
                    'SELECT * FROM assets WHERE project_id = %s AND status = %s ORDER BY created_at DESC',
                    (project_id, status),
                )
            else:
                cur.execute(
                    'SELECT * FROM assets WHERE project_id = %s ORDER BY created_at DESC',
                    (project_id,),
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def set_asset_status(asset_id: int, status: str, reviewer: str, notes: str = '') -> None:
    """Asset holatini yangilaydi VA review yozuvini qo'shadi — ikkalasi
    bitta tranzaksiyada, chunki har bir status o'zgarishi tekshiruv izi
    qoldirishi kerak."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE assets SET status = %s WHERE id = %s', (status, asset_id))
            cur.execute(
                '''INSERT INTO reviews (asset_id, reviewer, decision, notes)
                   VALUES (%s, %s, %s, %s)''',
                (asset_id, reviewer, status, notes),
            )
        conn.commit()
    finally:
        _put_conn(conn)


def update_asset_content(asset_id: int, title: str, content: str,
                          reviewer: str = 'admin', log_edit: bool = True) -> None:
    """Admin Navbat'da matnni tahrirlaganda chaqiriladi. Xohlasa,
    tekshiruv tarixiga 'edited' yozuvi ham qo'shiladi — shunda kim
    nimani o'zgartirgani kuzatilib boradi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE assets SET title = %s, content = %s WHERE id = %s',
                (title, content, asset_id),
            )
            if log_edit:
                cur.execute(
                    '''INSERT INTO reviews (asset_id, reviewer, decision, notes)
                       VALUES (%s, %s, %s, %s)''',
                    (asset_id, reviewer, 'edited', 'Matn admin tomonidan tahrirlandi'),
                )
        conn.commit()
    finally:
        _put_conn(conn)


# ═══════════════════════════════════════════════════════════
#  OUTPUTS  (Chiqishlar)
# ═══════════════════════════════════════════════════════════
def add_output(project_id: int, channel_type: str, name: str, config: dict) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO outputs (project_id, channel_type, name, config)
                   VALUES (%s, %s, %s, %s) RETURNING id''',
                (project_id, channel_type, name, json.dumps(config)),
            )
            output_id = cur.fetchone()[0]
        conn.commit()
        return output_id
    finally:
        _put_conn(conn)


def list_outputs(project_id: int, enabled_only: bool = False) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            q = 'SELECT * FROM outputs WHERE project_id = %s'
            if enabled_only:
                q += ' AND enabled = TRUE'
            cur.execute(q + ' ORDER BY id', (project_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def set_output_enabled(output_id: int, enabled: bool) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE outputs SET enabled = %s WHERE id = %s', (enabled, output_id))
        conn.commit()
    finally:
        _put_conn(conn)


# ═══════════════════════════════════════════════════════════
#  SEED — Ingliz Futboli'ni BIRINCHI loyiha sifatida ro'yxatga olish
# ═══════════════════════════════════════════════════════════
def seed_ingliz_futboli() -> None:
    """
    E'TIBOR: bu funksiya Ingliz Futboli uchun MAXSUS kod emas — bu
    shunchaki mavjud bitta loyihani umumiy sxemaga bir martalik
    import qilish. Xuddi shu funksiya shakli ertaga ikkinchi loyiha
    uchun ham ishlatiladi (boshqa slug, boshqa config qiymatlari bilan).
    feeds.py / agents.py'dagi hech narsa hali o'zgarmaydi — bu faqat
    o'sha qiymatlarning DB'dagi nusxasi, migratsiya keyingi bosqichda.
    """
    from feeds import RSS_FEEDS
    from agents import NAMES

    project_id = create_project(
        slug='ingliz-futboli',
        name='Ingliz Futboli',
        client_name=None,  # ichki loyiha — tashqi mijoz emas
    )

    # Data sources — RSS_FEEDS ro'yxatidan
    existing = {s['config'].get('url') for s in list_data_sources(project_id)}
    for url in RSS_FEEDS:
        if url in existing:
            continue
        # domendan o'qiladigan nom hosil qilamiz
        nice_name = url.split('//')[-1].split('/')[0].replace('www.', '')
        add_data_source(project_id, type_='rss', name=nice_name, config={'url': url})

    # Workflow — Brand Brain (terminologiya + ohang) NAMES lug'atidan
    if not get_workflow(project_id, 'content_production'):
        upsert_workflow(project_id, 'content_production', {
            'language': 'uz-latin',
            'tone': 'professional sport journalism',
            'terminology': NAMES,
            'model': 'gemini-2.5-flash',
            'agents': ['researcher', 'writer', 'editor'],
        })

    # Output — Telegram kanali
    if not list_outputs(project_id):
        add_output(project_id, channel_type='telegram', name='@Inglizfutbol',
                   config={'channel': '@Inglizfutbol'})

    log.info(f'[Studio] Ingliz Futboli seed qilindi — project_id={project_id}')


if __name__ == '__main__':
    # Qo'lda ishga tushirish uchun: python studio_schema.py
    init_studio_schema()
    seed_ingliz_futboli()
    print('Studio Lab sxema va seed tayyor.')
