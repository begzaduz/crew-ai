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
            # MUHIM: har bir post O'Z LOYIHASIGA bog'lanadi — aks holda
            # barcha loyihalarning tasdiqlangan postlari bitta umumiy
            # oqimga aralashib, bir loyihaning Mini App'ida boshqa
            # loyihaning postlari ko'rinib qolardi.
            cur.execute("ALTER TABLE published_posts ADD COLUMN IF NOT EXISTS project_id INTEGER")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_published_posts_project ON published_posts(project_id)")
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_published_posts_date
                ON published_posts (published_at DESC)
            ''')
            # Gemini API kunlik chaqiruv sanoqchisi (RPD kvotasini oldindan
            # boshqarish uchun). Sana Pacific Time bo'yicha saqlanadi.
            # MUHIM: HAR LOYIHA UCHUN ALOHIDA hisoblanadi (Superside'dagi
            # har mijozga alohida byudjet tamoyiliga mos) — bitta loyihaning
            # faolligi boshqa loyihaning kunlik kvotasini kamaytirmasin.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS daily_api_usage (
                    usage_date TEXT PRIMARY KEY,
                    call_count INTEGER DEFAULT 0
                )
            ''')
            cur.execute(
                "ALTER TABLE daily_api_usage ADD COLUMN IF NOT EXISTS project_id INTEGER NOT NULL DEFAULT 0"
            )
            # Bir martalik migratsiya: eski jadvalda PRIMARY KEY faqat
            # usage_date ustunida edi (loyihalar mavjud bo'lmagan davrdan
            # qolgan). Endi (usage_date, project_id) composite bo'lishi
            # kerak — aks holda bir xil sanada ikkita turli loyiha uchun
            # qator qo'shib bo'lmaydi. Bu blok idempotent: eski, yagona
            # ustunli PRIMARY KEY topilmasa (ya'ni migratsiya allaqachon
            # bajarilgan bo'lsa), hech narsa qilmaydi.
            cur.execute('''
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'daily_api_usage'
                  AND tc.constraint_type = 'PRIMARY KEY'
                GROUP BY tc.constraint_name
                HAVING COUNT(*) = 1 AND bool_and(kcu.column_name = 'usage_date')
            ''')
            old_pk = cur.fetchone()
            if old_pk:
                cur.execute(f'ALTER TABLE daily_api_usage DROP CONSTRAINT "{old_pk[0]}"')
                cur.execute('ALTER TABLE daily_api_usage ADD PRIMARY KEY (usage_date, project_id)')
                log.info('[DB] daily_api_usage: composite PRIMARY KEY (usage_date, project_id)ga ko\'chirildi.')

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
            # MUHIM: 'workflow_type' — endi o'chirilgan studio_schema.py'dan
            # meros qolgan dublikat ustun ('type' bilan bir xil ma'noda).
            # Eski (production) bazalarda bu ustun studio_schema.py orqali
            # allaqachon yaratilgan va ba'zan NOT NULL bo'lishi mumkin —
            # shuning uchun kodni soddalashtirib bu ustunni butunlay
            # e'tiborsiz qoldirish XAVFLI (eski bazada INSERT xato beradi).
            # Buning o'rniga: YANGI (toza) bazalarda ham shu ustun mavjud
            # bo'lishini kafolatlaymiz — shunda set_workflow_config()/
            # update_workflow_config() ikkala holatda ham ishlaydi.
            cur.execute("ALTER TABLE workflows ADD COLUMN IF NOT EXISTS workflow_type TEXT")
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
            # MUHIM: quyidagi uchtasi ('name', 'enabled', 'config') ham
            # kerak — get_data_sources()/add_data_source()/
            # set_data_source_active() aynan shu ustunlarga yozadi/o'qiydi
            # (eski studio_schema.py'dan meros konvensiya: manzil 'url'
            # ustunida EMAS, 'config' JSONB ichida, yoqilgan/o'chirilgani
            # 'active' emas 'enabled'da saqlanadi — _normalize_source()
            # ikkalasini ham qulaylik uchun tekislaydi). 'url'/'active'
            # ustunlari yuqorida shunchaki orqaga moslik uchun saqlangan.
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS name TEXT")
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}'::jsonb")
            # Manba ustuvorligi (yuqori raqam = birinchi ko'rib chiqiladi,
            # Dashboard'da tartiblash uchun) va kategoriya (masalan
            # "transfer", "match-report" — Dashboard'da filtrlash/guruhlash
            # uchun, hozircha faqat ko'rsatish/tahrirlash maqsadida).
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS category TEXT")

            # 'assets' va 'reviews' jadvallari allaqachon mavjud (studio_schema.py
            # orqali yaratilgan): assets(id, project_id, source_url, type, title,
            # content, score, status, created_at), reviews(id, asset_id, reviewer,
            # decision, notes, reviewed_at). Review Queue uchun ikkita qo'shimcha
            # ustun kerak: post bilan birga yuboriladigan rasm va qachon e'lon
            # qilinganligi.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER
                )
            ''')
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS source_url TEXT")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'text'")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS title TEXT")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS content TEXT")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft'")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS image_url TEXT")
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ")
            # Rejalashtirilgan chiqish uchun: admin Review Queue'da
            # tasdiqlagan post, lekin loyihada publish_interval_minutes
            # > 0 bo'lsa, DARHOL
            # kanalga yubormasdan, shu vaqt belgisi bilan navbatga
            # qo'yiladi (status='scheduled'). Background scheduler shu
            # ustun bo'yicha FIFO tartibda (eng eski tasdiqlangan
            # birinchi) navbatdan chiqaradi.
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ")
            # Published/Rejected sahifalarida "Bugun/Kecha/7 kun/30 kun/
            # Barchasi" filtr-tab'lari uchun — published_at kabi, faqat
            # rad etilgan vaqtni saqlaydi (mark_asset_rejected() to'ldiradi).
            # Bu bo'lmasa, filtrlash created_at (yaratilgan vaqt)ga
            # tayanishga majbur bo'lardi — haftalar oldin yaratilib,
            # BUGUN rad etilgan post "7 kun oldin" bo'limida ko'rinib
            # qolardi, bu chalkashtiradi.
            cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ")
            # Bir martalik backfill: ustun qo'shilishidan OLDIN rad etilgan
            # eski yozuvlarda rejected_at NULL qoladi — ular sana-filtrli
            # ko'rinishlarda (Bugun/Kecha/...) ko'rinmay qolib, faqat
            # "Barchasi"da chiqadi. Yaqinlashtirish sifatida created_at'ni
            # ishlatamiz (aniq rad etilgan vaqt saqlanmagan, lekin bu eng
            # yaqin taxmin). Idempotent — faqat hali NULL qolganlarga tegadi.
            cur.execute("UPDATE assets SET rejected_at = created_at WHERE status = 'rejected' AND rejected_at IS NULL")
            # Range-filtrli so'rovlar (published_at/rejected_at bo'yicha)
            # va sidebar badge COUNT(*) so'rovlari tez ishlashi uchun.
            cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_project_status ON assets(project_id, status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_published_at ON assets(project_id, status, published_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_rejected_at ON assets(project_id, status, rejected_at)")

            cur.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    asset_id INTEGER
                )
            ''')
            cur.execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS reviewer TEXT NOT NULL DEFAULT 'dashboard'")
            cur.execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS decision TEXT NOT NULL DEFAULT 'approved'")
            cur.execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS notes TEXT")
            cur.execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ DEFAULT NOW()")

            # Dashboard'dan qo'lda yuklangan rasmlar (New Request / Review
            # Queue'dagi "Rasm yuklash"). Tashqi fayl hosting kerak emas —
            # rasm baytlari to'g'ridan-to'g'ri shu yerda saqlanadi, va
            # /api/image/<id> orqali oddiy HTTP URL sifatida ochiladi
            # (bu URL keyin assets.image_url'ga xuddi boshqa har qanday
            # URL kabi yoziladi — pipeline/Telegram/Mini App uchun farqi
            # yo'q). Internetdan (Google qidiruv) tanlangan rasmlar bu
            # jadvalga tushmaydi — ularning URL'i tashqi va allaqachon
            # barqaror, to'g'ridan-to'g'ri ishlatiladi.
            cur.execute('''
                CREATE TABLE IF NOT EXISTS asset_uploads (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER,
                    content_type TEXT NOT NULL,
                    data BYTEA NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
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
def save_post(project_id: int, url: str | None, title: str, post_text: str, image_url: str | None) -> None:
    """Kanalga yuborilgan har bir postni O'Z LOYIHASIGA bog'lab saqlaydi
    (mini app shundan o'qiydi) — loyihalar bir-birining postini
    ko'rmasligi uchun MUHIM."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO published_posts (project_id, url, title, post_text, image_url)
                   VALUES (%s, %s, %s, %s, %s)''',
                (project_id, url, title, post_text, image_url),
            )
        conn.commit()
    except Exception as e:
        log.error(f'[DB] save_post xato: {e}')
    finally:
        _put_conn(conn)


def get_recent_posts(project_id: int, limit: int = 50) -> list[dict]:
    """Mini app uchun BERILGAN LOYIHANING so'nggi postlari (eng yangisi
    birinchi). project_id majburiy — aks holda boshqa loyihalarning
    postlari aralashib ketadi."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT id, url, title, post_text, image_url, published_at
                   FROM published_posts
                   WHERE project_id = %s
                   ORDER BY published_at DESC
                   LIMIT %s''',
                (project_id, limit),
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


def get_today_api_calls(project_id: int) -> int:
    """Berilgan loyihaning bugungi (Pacific Time) Gemini API chaqiruvlar
    sonini qaytaradi — har loyiha alohida hisoblanadi."""
    today = _today_pacific()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT call_count FROM daily_api_usage WHERE usage_date = %s AND project_id = %s',
                (today, project_id),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        _put_conn(conn)


def increment_api_calls(project_id: int, n: int = 1) -> None:
    """Berilgan loyihaning bugungi (Pacific Time) API chaqiruvlar sonini
    n ga oshiradi."""
    today = _today_pacific()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO daily_api_usage (usage_date, project_id, call_count)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (usage_date, project_id)
                   DO UPDATE SET call_count = daily_api_usage.call_count + %s''',
                (today, project_id, n, n),
            )
        conn.commit()
    except Exception as e:
        log.error(f'[DB] increment_api_calls xato: {e}')
    finally:
        _put_conn(conn)


def reset_today_api_calls(project_id: int) -> None:
    """Berilgan loyihaning BUGUNGI (Pacific Time) ichki API hisoblagichini
    nolga tushiradi. MUHIM: bu Gemini'ning haqiqiy tashqi kvotasiga
    umuman ta'sir qilmaydi (u Google tomonida, bu yerda ko'rinmaydi) —
    faqat Studio Lab'ning o'z ichki kunlik xavfsizlik limitini (
    DAILY_POST_BUDGET) qayta hisoblaydi. Dashboard'da sinov paytida
    band bo'lib qolgan limitni qo'lda tozalash uchun."""
    today = _today_pacific()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM daily_api_usage WHERE usage_date = %s AND project_id = %s',
                (today, project_id),
            )
        conn.commit()
        log.info(f'[DB] Kunlik API hisoblagich tozalandi (project_id={project_id}).')
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


def list_projects() -> list[dict]:
    """Barcha loyihalarni qaytaradi (eng eskisi birinchi — yaratilish
    tartibida). Dashboard'dagi loyiha almashtirgich shundan foydalanadi."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM projects ORDER BY id')
            return [dict(row) for row in cur.fetchall()]
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


def get_project_id_by_telegram_admin_chat_id(chat_id: int) -> int | None:
    """Berilgan Telegram chat_id qaysi loyihaning 'telegram_admin_chat_id'
    (workflows.config JSONB ichida, Dashboard'dan sozlanadi) qiymatiga
    mos kelishini topadi. MUHIM: bu bot buyruqlarini (main.py) BITTA
    global loyihaga (PROJECT_ID) qattiq bog'lab qo'yish o'rniga, DB
    orqali dinamik aniqlash uchun — kelajakda Telegram'siz (botsiz)
    loyihalar bo'lishi ham, ko'p loyiha bitta botni ulashishi ham
    mumkin bo'lishi kerak. Hech qanday loyiha shu chat_id'ga
    bog'lanmagan bo'lsa, None qaytaradi — chaqiruvchi orqaga moslik
    uchun bootstrap qilingan asosiy loyihaga qaytishi kerak."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT project_id FROM workflows "
                "WHERE config->>'telegram_admin_chat_id' = %s LIMIT 1",
                (str(chat_id),),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
    finally:
        _put_conn(conn)


def set_workflow_config(project_id: int, config: dict, wf_type: str = 'rss_news') -> dict:
    """Config'ni to'liq almashtiradi (overwrite).
    MUHIM: jadvalda 'workflow_type' degan NOT NULL (standart qiymatsiz) ustun
    ham bor (mening qo'shgan 'type' ustunimdan tashqari) — shuning uchun
    ikkalasini ham to'ldiramiz."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO workflows (project_id, type, workflow_type, config)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (project_id, type)
                   DO UPDATE SET config = EXCLUDED.config, updated_at = NOW()
                   RETURNING config''',
                (project_id, wf_type, wf_type, psycopg2.extras.Json(config)),
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
                '''INSERT INTO workflows (project_id, type, workflow_type, config)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (project_id, type)
                   DO UPDATE SET config = workflows.config || EXCLUDED.config, updated_at = NOW()
                   RETURNING config''',
                (project_id, wf_type, wf_type, psycopg2.extras.Json(patch)),
            )
            result = cur.fetchone()[0]
        conn.commit()
        return result
    finally:
        _put_conn(conn)


# ── Studio Lab: data_sources (RSS manbalar) ───────────────
# MUHIM: ushbu jadval avvalroq boshqa kod (studio_schema.py) orqali
# yaratilgan bo'lib, haqiqiy manzil (url) alohida ustunda emas, balki
# 'config' JSONB ustuni ichida ({"url": "..."}) saqlanadi, va yoqilgan/
# o'chirilganligi 'active' emas, 'enabled' ustunida turadi. Quyidagi
# funksiyalar ANA SHU haqiqiy ustunlar bilan ishlaydi. _normalize_source()
# har bir qatorga qulaylik uchun tekis 'url' va 'active' kalitlarini
# qo'shib beradi, shunda dashboard/pipeline kodi ularni to'g'ridan-to'g'ri
# ishlata oladi.
def _normalize_source(row: dict) -> dict:
    row = dict(row)
    cfg = row.get('config') or {}
    if not row.get('url'):
        row['url'] = cfg.get('url', '')
    if row.get('active') is None:
        row['active'] = row.get('enabled', True)
    return row


def get_data_sources(project_id: int, active_only: bool = False) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if active_only:
                cur.execute(
                    '''SELECT * FROM data_sources WHERE project_id=%s AND enabled=TRUE
                       ORDER BY priority DESC, id ASC''',
                    (project_id,),
                )
            else:
                cur.execute(
                    '''SELECT * FROM data_sources WHERE project_id=%s
                       ORDER BY priority DESC, id ASC''',
                    (project_id,),
                )
            return [_normalize_source(dict(r)) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def add_data_source(project_id: int, url: str, source_type: str = 'rss',
                     priority: int = 0, category: str | None = None) -> dict:
    url = url.strip()
    try:
        from urllib.parse import urlparse
        name = urlparse(url).netloc or url
    except Exception:
        name = url
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''INSERT INTO data_sources (project_id, type, name, enabled, config, priority, category)
                   VALUES (%s, %s, %s, TRUE, %s, %s, %s) RETURNING *''',
                (project_id, source_type, name, psycopg2.extras.Json({'url': url}), priority, category),
            )
            row = cur.fetchone()
        conn.commit()
        return _normalize_source(dict(row))
    finally:
        _put_conn(conn)


def update_data_source_meta(source_id: int, priority: int | None = None,
                             category: str | None = None) -> None:
    """Dashboard'dan mavjud manbaning ustuvorligi/kategoriyasini tahrirlash.
    Faqat berilgan (None bo'lmagan) maydonlar yangilanadi."""
    if priority is None and category is None:
        return
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if priority is not None and category is not None:
                cur.execute(
                    'UPDATE data_sources SET priority=%s, category=%s WHERE id=%s',
                    (priority, category, source_id),
                )
            elif priority is not None:
                cur.execute('UPDATE data_sources SET priority=%s WHERE id=%s', (priority, source_id))
            else:
                cur.execute('UPDATE data_sources SET category=%s WHERE id=%s', (category, source_id))
        conn.commit()
    finally:
        _put_conn(conn)


def set_data_source_active(source_id: int, active: bool) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE data_sources SET enabled=%s WHERE id=%s', (active, source_id))
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


# ── Studio Lab: assets & reviews (Review Queue) ───────────
# AI post yaratganda TO'G'RIDAN-TO'G'RI kanalga yuborilmaydi — avval
# 'assets' jadvaliga status='draft' bilan yoziladi. Dashboard'da admin
# postni tahrirlaydi (update_asset_content), so'ng Tasdiqlaydi (bu vaqtda
# 'reviews'ga yozuv qo'shiladi va asset 'published' bo'ladi) yoki Rad
# etadi ('rejected'). Faqat TASDIQLANGAN postlar kanalga ketadi.
def create_asset(project_id: int, source_url: str | None, asset_type: str,
                  title: str, content: str, score: int = 0,
                  image_url: str | None = None) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''INSERT INTO assets (project_id, source_url, type, title, content, score, status, image_url)
                   VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s)
                   RETURNING *''',
                (project_id, source_url, asset_type, title, content, score, image_url),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    finally:
        _put_conn(conn)


def get_assets(project_id: int, status: str | None = None, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute(
                    '''SELECT * FROM assets WHERE project_id=%s AND status=%s
                       ORDER BY created_at DESC LIMIT %s''',
                    (project_id, status, limit),
                )
            else:
                cur.execute(
                    '''SELECT * FROM assets WHERE project_id=%s
                       ORDER BY created_at DESC LIMIT %s''',
                    (project_id, limit),
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


# Published/Rejected uchun sana ustuni: har biri o'z "sodir bo'lgan vaqti"
# bo'yicha filtrlanadi (published_at / rejected_at), draft/scheduled uchun
# range-filtr qo'llanmaydi (get_assets_by_range() faqat shu ikkitasi bilan
# chaqiriladi, boshqasiga tushmaydi).
_RANGE_DATE_COLUMN = {'published': 'published_at', 'rejected': 'rejected_at'}
_RANGE_WINDOW_DAYS = {'today': 0, '7d': 6, '30d': 29}


def count_assets(project_id: int, status: str) -> int:
    """Berilgan status bo'yicha JAMI (barcha vaqt) sonini qaytaradi —
    to'liq qatorlarni yuklamasdan, faqat COUNT(*) (composite index
    (project_id, status) orqali tez). Dashboard'dagi 'Kontent hayot
    sikli' halqasi kabi umumiy statistikalar uchun."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT COUNT(*) FROM assets WHERE project_id=%s AND status=%s',
                (project_id, status),
            )
            return int(cur.fetchone()[0])
    finally:
        _put_conn(conn)


def count_assets_today(project_id: int, status: str) -> int:
    """Berilgan status uchun BUGUNGI (UTC) sonini qaytaradi — 'published'
    uchun published_at, 'rejected' uchun rejected_at bo'yicha. Sidebar
    badge'lar (nav-count-published/rejected) shu bilan ishlaydi."""
    date_col = _RANGE_DATE_COLUMN.get(status, 'created_at')
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f'''SELECT COUNT(*) FROM assets WHERE project_id=%s AND status=%s
                    AND {date_col} >= (NOW() AT TIME ZONE 'UTC')::date
                    AND {date_col} < (NOW() AT TIME ZONE 'UTC')::date + INTERVAL '1 day' ''',
                (project_id, status),
            )
            return int(cur.fetchone()[0])
    finally:
        _put_conn(conn)


def get_assets_by_range(project_id: int, status: str, range_key: str = 'all', limit: int = 100) -> list[dict]:
    """Published/Rejected sahifalaridagi 'Bugun/Kecha/7 kun/30 kun/
    Barchasi' filtr-tab'lari uchun. range_key noto'g'ri yoki 'all' bo'lsa,
    filtrsiz (barcha vaqt, eng yangisi birinchi) qaytaradi."""
    date_col = _RANGE_DATE_COLUMN.get(status, 'created_at')
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if range_key == 'yesterday':
                cur.execute(
                    f'''SELECT * FROM assets WHERE project_id=%s AND status=%s
                        AND {date_col} >= (NOW() AT TIME ZONE 'UTC')::date - INTERVAL '1 day'
                        AND {date_col} < (NOW() AT TIME ZONE 'UTC')::date
                        ORDER BY {date_col} DESC LIMIT %s''',
                    (project_id, status, limit),
                )
            elif range_key in _RANGE_WINDOW_DAYS:
                days_back = _RANGE_WINDOW_DAYS[range_key]
                cur.execute(
                    f'''SELECT * FROM assets WHERE project_id=%s AND status=%s
                        AND {date_col} >= (NOW() AT TIME ZONE 'UTC')::date - (INTERVAL '1 day' * %s)
                        ORDER BY {date_col} DESC LIMIT %s''',
                    (project_id, status, days_back, limit),
                )
            else:
                cur.execute(
                    f'''SELECT * FROM assets WHERE project_id=%s AND status=%s
                        ORDER BY {date_col} DESC NULLS LAST LIMIT %s''',
                    (project_id, status, limit),
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        _put_conn(conn)


def get_asset(asset_id: int) -> dict | None:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM assets WHERE id=%s', (asset_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


def get_last_asset_created_at(project_id: int):
    """Loyihaning eng so'nggi asset (draft/published/rejected — barcha
    status) yaratilgan vaqtini qaytaradi. Dashboard'dagi 'Active/Error'
    status badge shu asosda hisoblanadi — pipeline oxirgi marta qachon
    kontent yaratganini bildiradi. Hech qanday asset bo'lmasa None."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT MAX(created_at) FROM assets WHERE project_id=%s',
                (project_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        _put_conn(conn)


def resanitize_draft_assets(project_id: int | None = None) -> int:
    """Eski kod bilan yaratilgan (hozirgi sanitize_telegram_html() qo'shilishidan
    OLDIN saqlangan) draft'lardagi xom HTML teglarni (masalan <br>) tozalaydi.
    Faqat status='draft' bo'lgan (hali kanalga yuborilmagan) postlarga tegadi —
    published/rejected o'zgarmaydi. Idempotent: allaqachon toza matnga qayta
    ishlov berish hech narsani o'zgartirmaydi, shuning uchun har safar server
    ishga tushganda xavfsiz chaqirilishi mumkin. Nechta yozuv tuzatilganini
    qaytaradi."""
    from telegram_utils import sanitize_telegram_html

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if project_id is not None:
                cur.execute(
                    "SELECT id, content FROM assets WHERE status='draft' AND project_id=%s AND content ~ '<[a-zA-Z/]'",
                    (project_id,),
                )
            else:
                cur.execute(
                    "SELECT id, content FROM assets WHERE status='draft' AND content ~ '<[a-zA-Z/]'",
                )
            rows = cur.fetchall()
            fixed = 0
            for row in rows:
                cleaned = sanitize_telegram_html(row['content'] or '')
                if cleaned != row['content']:
                    cur.execute('UPDATE assets SET content=%s WHERE id=%s', (cleaned, row['id']))
                    fixed += 1
        conn.commit()
        if fixed:
            log.info(f'[DB] {fixed} ta eski draft xom HTML tegdan tozalandi.')
        return fixed
    finally:
        _put_conn(conn)


def update_asset_content(asset_id: int, content: str, title: str | None = None) -> None:
    """Dashboard'dagi 'Edit' — tasdiqlashdan oldin postni qo'lda tahrirlash.
    Saqlashdan oldin HAR DOIM sanitize_telegram_html() orqali o'tkaziladi —
    admin qo'lda <br> yoki boshqa Telegram tushunmaydigan teg kiritib qo'ysa
    ham, DB'da va keyingi Telegram'ga yuborishda toza matn qoladi."""
    from telegram_utils import sanitize_telegram_html
    content = sanitize_telegram_html(content)
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if title is not None:
                cur.execute('UPDATE assets SET content=%s, title=%s WHERE id=%s', (content, title, asset_id))
            else:
                cur.execute('UPDATE assets SET content=%s WHERE id=%s', (content, asset_id))
        conn.commit()
    finally:
        _put_conn(conn)


def set_asset_status(asset_id: int, status: str) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE assets SET status=%s WHERE id=%s', (status, asset_id))
        conn.commit()
    finally:
        _put_conn(conn)


def schedule_asset(asset_id: int) -> None:
    """Postni darhol kanalga yubormasdan, navbatga qo'yadi (status='scheduled').
    scheduled_at — navbat tartibi (FIFO, eng eski tasdiqlangan birinchi
    chiqadi) uchun ishlatiladi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assets SET status='scheduled', scheduled_at=NOW() WHERE id=%s",
                (asset_id,),
            )
        conn.commit()
    finally:
        _put_conn(conn)


def unschedule_asset(asset_id: int) -> None:
    """Navbatdan chiqarib, qaytadan Review Queue'ga (status='draft')
    qo'yadi — admin 'Bekor qilish' bosganda ishlatiladi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assets SET status='draft', scheduled_at=NULL WHERE id=%s AND status='scheduled'",
                (asset_id,),
            )
        conn.commit()
    finally:
        _put_conn(conn)


def get_next_scheduled_asset(project_id: int) -> dict | None:
    """Loyihaning navbatdagi ENG ESKI (birinchi tasdiqlangan) postini
    qaytaradi — scheduler shuni chiqaradi. Navbat bo'sh bo'lsa None."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT * FROM assets WHERE project_id=%s AND status='scheduled'
                   ORDER BY scheduled_at ASC LIMIT 1''',
                (project_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


def get_last_published_at(project_id: int):
    """Loyihaning ENG SO'NGGI haqiqatan kanalga yuborilgan postining vaqti
    (published_posts jadvalidan — yagona haqiqat manbai). Scheduler shu
    asosda 'interval o'tdimi' deb hisoblaydi. Hech qachon nashr etilmagan
    bo'lsa None."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT MAX(published_at) FROM published_posts WHERE project_id=%s',
                (project_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        _put_conn(conn)


def mark_asset_published(asset_id: int) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assets SET status='published', published_at=NOW() WHERE id=%s",
                (asset_id,),
            )
        conn.commit()
    finally:
        _put_conn(conn)


def mark_asset_rejected(asset_id: int) -> None:
    """mark_asset_published()ga o'xshab — status='rejected' bilan birga
    rejected_at=NOW()ni ham yozadi, shunda Rejected sahifasidagi sana
    filtrlari (Bugun/Kecha/...) to'g'ri ishlaydi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assets SET status='rejected', rejected_at=NOW() WHERE id=%s",
                (asset_id,),
            )
        conn.commit()
    finally:
        _put_conn(conn)


def add_review(asset_id: int, reviewer: str, decision: str, notes: str = '') -> dict:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''INSERT INTO reviews (asset_id, reviewer, decision, notes)
                   VALUES (%s, %s, %s, %s) RETURNING *''',
                (asset_id, reviewer, decision, notes),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
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


def delete_project(project_id: int) -> bool:
    """Loyihani va unga tegishli BARCHA ma'lumotlarni (workflow config,
    manbalar, assets, reviews, published_posts, kunlik kvota) butunlay
    o'chiradi. Boshqa loyihalarga tegmaydi. Loyiha topilmasa False
    qaytaradi."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM projects WHERE id=%s', (project_id,))
            if not cur.fetchone():
                return False
            cur.execute(
                '''DELETE FROM reviews WHERE asset_id IN
                   (SELECT id FROM assets WHERE project_id=%s)''',
                (project_id,),
            )
            cur.execute('DELETE FROM assets WHERE project_id=%s', (project_id,))
            cur.execute('DELETE FROM asset_uploads WHERE project_id=%s', (project_id,))
            cur.execute('DELETE FROM data_sources WHERE project_id=%s', (project_id,))
            cur.execute('DELETE FROM workflows WHERE project_id=%s', (project_id,))
            cur.execute('DELETE FROM published_posts WHERE project_id=%s', (project_id,))
            cur.execute('DELETE FROM daily_api_usage WHERE project_id=%s', (project_id,))
            cur.execute('DELETE FROM projects WHERE id=%s', (project_id,))
        conn.commit()
        log.info(f'[DB] Loyiha butunlay o\'chirildi (project_id={project_id}).')
        return True
    finally:
        _put_conn(conn)


# ── Studio Lab: yuklangan rasmlar (Dashboard "Rasm yuklash") ──────
def save_upload(project_id: int, content_type: str, data: bytes) -> int:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO asset_uploads (project_id, content_type, data)
                   VALUES (%s, %s, %s) RETURNING id''',
                (project_id, content_type, psycopg2.Binary(data)),
            )
            upload_id = cur.fetchone()[0]
        conn.commit()
        return upload_id
    finally:
        _put_conn(conn)


def get_upload(upload_id: int) -> dict | None:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT content_type, data FROM asset_uploads WHERE id=%s',
                (upload_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


def update_asset_image(asset_id: int, image_url: str | None) -> None:
    """Review Queue'da mavjud draft'ning rasmini almashtirish/o'rnatish
    uchun (New Request'da esa asset yaratilishidan OLDIN image_url
    to'g'ridan-to'g'ri create_asset()ga beriladi, bu funksiya kerak
    emas)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE assets SET image_url=%s WHERE id=%s', (image_url, asset_id))
        conn.commit()
    finally:
        _put_conn(conn)
