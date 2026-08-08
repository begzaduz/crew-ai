"""Studio Lab Dashboard uchun REST API funksiyalari.

main.py'dagi HTTP handler (WebhookHandler) shu funksiyalarni GET_ROUTES /
POST_ROUTES orqali chaqiradi. Har bir funksiya (http_status, json_payload)
juftligini qaytaradi — HTTP transport qatlamidan mustaqil, shuning uchun
kelajakda boshqa transport (masalan haqiqiy web-framework)ga o'tish oson.
"""
import logging
import re

import database
import telegram_utils
from config import DAILY_POST_BUDGET, INTERVAL, PUBLIC_BASE_URL
from workflows.rss_news import (
    RESEARCHER_PROMPT_TEMPLATE, WRITER_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE,
)

log = logging.getLogger(__name__)

# Pipeline 3 ta agent (Researcher+Writer+Editor) ishlatadi — har bir
# generate_post() chaqiruvi ~3 ta Gemini API chaqiruvi sarflaydi.
# (main.py'dagi CALLS_PER_POST/DAILY_API_LIMIT bilan bir xil hisob —
# takrorlanadi, chunki main.py'ni bu yerdan import qilib bo'lmaydi
# (circular import): main.py studio_api.py'ni import qiladi.)
CALLS_PER_POST = 3
DAILY_API_LIMIT = DAILY_POST_BUDGET * CALLS_PER_POST


# ── Data manbalar (RSS) ────────────────────────────────────
def list_sources(project_id: int) -> tuple[int, object]:
    try:
        return 200, database.get_data_sources(project_id)
    except Exception as e:
        log.error(f'[StudioAPI] list_sources: {e}')
        return 500, {'error': str(e)}


def add_source(project_id: int, data: dict) -> tuple[int, object]:
    url = (data.get('url') or '').strip()
    if not url:
        return 400, {'error': "url kerak"}
    if not (url.startswith('http://') or url.startswith('https://')):
        return 400, {'error': "url http:// yoki https:// bilan boshlanishi kerak"}
    try:
        priority = int(data.get('priority') or 0)
    except (TypeError, ValueError):
        return 400, {'error': 'priority butun son bo\'lishi kerak'}
    category = (data.get('category') or '').strip() or None
    try:
        row = database.add_data_source(project_id, url, priority=priority, category=category)
        log.info(f'[StudioAPI] Yangi manba qo\'shildi (project={project_id}): {url}')
        return 200, row
    except Exception as e:
        log.error(f'[StudioAPI] add_source: {e}')
        return 500, {'error': str(e)}


def update_source_meta(data: dict) -> tuple[int, object]:
    sid = data.get('id')
    if sid is None:
        return 400, {'error': 'id kerak'}
    priority = data.get('priority')
    category = data.get('category')
    if priority is not None:
        try:
            priority = int(priority)
        except (TypeError, ValueError):
            return 400, {'error': 'priority butun son bo\'lishi kerak'}
    if category is not None:
        category = category.strip() or None
    try:
        database.update_data_source_meta(int(sid), priority=priority, category=category)
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] update_source_meta: {e}')
        return 500, {'error': str(e)}


def toggle_source(data: dict) -> tuple[int, object]:
    sid = data.get('id')
    if sid is None:
        return 400, {'error': 'id kerak'}
    try:
        database.set_data_source_active(int(sid), bool(data.get('active')))
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] toggle_source: {e}')
        return 500, {'error': str(e)}


def delete_source(data: dict) -> tuple[int, object]:
    sid = data.get('id')
    if sid is None:
        return 400, {'error': 'id kerak'}
    try:
        database.delete_data_source(int(sid))
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] delete_source: {e}')
        return 500, {'error': str(e)}


# ── Workflow config (terminologiya, taxalluslar, kanal, uslub) ────
def get_config(project_id: int) -> tuple[int, object]:
    try:
        cfg = database.get_workflow_config(project_id) or {}
        cfg = dict(cfg)
        # 'prompt_defaults' faqat Dashboard'da ko'rsatish uchun — DB'da
        # saqlanmaydi. Admin custom prompt yozmagan bo'lsa, Dashboard shu
        # standart matnni boshlang'ich qiymat sifatida ko'rsatadi.
        cfg['prompt_defaults'] = {
            'researcher': RESEARCHER_PROMPT_TEMPLATE,
            'writer': WRITER_PROMPT_TEMPLATE,
            'editor': EDITOR_PROMPT_TEMPLATE,
        }
        # Gemini API kalit — Dashboard'ga to'liq qiymat qaytarilmaydi (bu
        # brauzer Network panelida ko'rinib qolishi mumkin). Faqat
        # o'rnatilganmi degan belgi va oxirgi 4 belgi ko'rsatiladi;
        # frontend buni saqlangan/saqlanmaganini bildirish uchun ishlatadi.
        raw_key = cfg.pop('gemini_api_key', None)
        cfg['gemini_api_key_set'] = bool(raw_key)
        cfg['gemini_api_key_hint'] = raw_key[-4:] if raw_key else ''
        return 200, cfg
    except Exception as e:
        log.error(f'[StudioAPI] get_config: {e}')
        return 500, {'error': str(e)}


_ALLOWED_CONFIG_KEYS = {
    'terminology', 'nicknames', 'channel_tag', 'tone',
    'domain_description', 'content_types', 'jargon', 'emoji_legend',
    'telegram_channel_id', 'prompts', 'gemini_api_key', 'auto_publish',
    'publish_interval_minutes',
}
_ALLOWED_PROMPT_KEYS = {'researcher', 'writer', 'editor'}


def update_config(project_id: int, data: dict) -> tuple[int, object]:
    patch = {k: v for k, v in data.items() if k in _ALLOWED_CONFIG_KEYS}
    if not patch:
        return 400, {'error': "saqlanadigan maydon topilmadi (" + ', '.join(sorted(_ALLOWED_CONFIG_KEYS)) + ")"}
    if 'terminology' in patch and not isinstance(patch['terminology'], dict):
        return 400, {'error': "terminology obyekt (key-value) bo'lishi kerak"}
    if 'nicknames' in patch and not isinstance(patch['nicknames'], dict):
        return 400, {'error': "nicknames obyekt (key-value) bo'lishi kerak"}
    if 'jargon' in patch and not isinstance(patch['jargon'], dict):
        return 400, {'error': "jargon obyekt (key-value) bo'lishi kerak"}
    if 'emoji_legend' in patch and not isinstance(patch['emoji_legend'], dict):
        return 400, {'error': "emoji_legend obyekt (key-value) bo'lishi kerak"}
    if 'content_types' in patch and not isinstance(patch['content_types'], list):
        return 400, {'error': "content_types massiv (list) bo'lishi kerak"}
    if 'domain_description' in patch and not isinstance(patch['domain_description'], str):
        return 400, {'error': "domain_description matn bo'lishi kerak"}
    if 'telegram_channel_id' in patch and not isinstance(patch['telegram_channel_id'], str):
        return 400, {'error': "telegram_channel_id matn bo'lishi kerak (masalan @KanalNomi)"}
    if 'auto_publish' in patch:
        # Frontend checkbox true/false yuboradi, lekin xavfsizlik uchun
        # istalgan "haqiqiy" qiymatni ham bool'ga aylantiramiz.
        patch['auto_publish'] = bool(patch['auto_publish'])
    if 'publish_interval_minutes' in patch:
        try:
            interval = int(patch['publish_interval_minutes'])
        except (TypeError, ValueError):
            return 400, {'error': "publish_interval_minutes butun son bo'lishi kerak (0 = darhol chiqarish)"}
        if interval < 0:
            return 400, {'error': "publish_interval_minutes manfiy bo'lishi mumkin emas"}
        patch['publish_interval_minutes'] = interval
    if 'gemini_api_key' in patch:
        if not isinstance(patch['gemini_api_key'], str):
            return 400, {'error': "gemini_api_key matn bo'lishi kerak"}
        # Bo'sh qiymat yuborilsa — bu "o'zgartirmayman" degani (frontend
        # parol maydonini bo'sh qoldirsa yuboradi), saqlangan kalitga
        # tegilmaydi.
        if not patch['gemini_api_key'].strip():
            del patch['gemini_api_key']
    if 'prompts' in patch:
        if not isinstance(patch['prompts'], dict):
            return 400, {'error': "prompts obyekt (researcher/writer/editor) bo'lishi kerak"}
        bad_keys = set(patch['prompts']) - _ALLOWED_PROMPT_KEYS
        if bad_keys:
            return 400, {'error': f"prompts faqat researcher/writer/editor kalitlarini qabul qiladi (noto'g'ri: {sorted(bad_keys)})"}
        # Bo'sh qiymat chiqarib tashlanadi — shu orqali admin bitta
        # promptni "tozalab" standartga qaytarishi mumkin.
        patch['prompts'] = {k: v for k, v in patch['prompts'].items() if isinstance(v, str) and v.strip()}
    if not patch:
        return 200, database.get_workflow_config(project_id) or {}
    try:
        cfg = database.update_workflow_config(project_id, patch)
        log.info(f'[StudioAPI] Config yangilandi (project={project_id}): {list(patch.keys())}')
        return 200, cfg
    except Exception as e:
        log.error(f'[StudioAPI] update_config: {e}')
        return 500, {'error': str(e)}


# ── Dashboard KPI ("posts today", pending, published, sources) ────
# Yangi jadval yoki ustun qo'shilmadi — faqat mavjud get_assets()/
# get_data_sources() natijalarini Dashboard uchun birlashtiradi.
# Avtomatik yangilik sikli (main.py'dagi news_loop) har INTERVAL soniyada
# ishga tushadi. Agar oxirgi asset shu oraliqning 2 barobaridan ko'proq
# vaqt oldin yaratilgan bo'lsa (bitta o'tkazib yuborilgan tsikl uchun
# joy qoldirib), loyiha holati "error" (yoki hali umuman ishlamagan
# bo'lsa "idle") deb belgilanadi.
_STATUS_STALE_THRESHOLD_SECONDS = INTERVAL * 2


def get_dashboard_stats(project_id: int) -> tuple[int, object]:
    try:
        import datetime as _dt
        drafts = database.get_assets(project_id, status='draft', limit=200)
        scheduled = database.get_assets(project_id, status='scheduled', limit=200)
        published = database.get_assets(project_id, status='published', limit=200)
        rejected = database.get_assets(project_id, status='rejected', limit=200)
        sources = database.get_data_sources(project_id)

        today = _dt.datetime.now(_dt.timezone.utc).date()
        posts_today = 0
        for a in published:
            pub = a.get('published_at')
            if not pub:
                continue
            try:
                d = pub.date() if hasattr(pub, 'date') else _dt.datetime.fromisoformat(str(pub)).date()
                if d == today:
                    posts_today += 1
            except Exception:
                continue

        last_run_at = database.get_last_asset_created_at(project_id)
        if last_run_at is None:
            project_status = 'idle'
        else:
            now = _dt.datetime.now(_dt.timezone.utc)
            last_dt = last_run_at if last_run_at.tzinfo else last_run_at.replace(tzinfo=_dt.timezone.utc)
            age_seconds = (now - last_dt).total_seconds()
            project_status = 'active' if age_seconds <= _STATUS_STALE_THRESHOLD_SECONDS else 'error'

        api_calls_used = database.get_today_api_calls(project_id)
        cfg = database.get_workflow_config(project_id)
        auto_publish = bool(cfg.get('auto_publish'))
        try:
            publish_interval_minutes = int(cfg.get('publish_interval_minutes') or 0)
        except (TypeError, ValueError):
            publish_interval_minutes = 0

        return 200, {
            'pending_review': len(drafts),
            'scheduled_count': len(scheduled),
            'published_total': len(published),
            'rejected_total': len(rejected),
            'posts_today': posts_today,
            'active_sources': sum(1 for s in sources if s.get('active')),
            'total_sources': len(sources),
            'auto_publish': auto_publish,
            'publish_interval_minutes': publish_interval_minutes,
            'project_status': project_status,
            'last_run_at': last_run_at,
            'api_calls_used_today': api_calls_used,
            'api_calls_limit_today': DAILY_API_LIMIT,
        }
    except Exception as e:
        log.error(f'[StudioAPI] get_dashboard_stats: {e}')
        return 500, {'error': str(e)}


# ── Review Queue (assets + reviews) ────────────────────────
# AI post yaratganda TO'G'RIDAN-TO'G'RI kanalga yubormaydi — 'assets'ga
# status='draft' bilan yoziladi (bu ishni main.py bajaradi). Bu yerdagi
# funksiyalar Dashboard orqali ko'rish/tahrirlash/tasdiqlash/rad etish
# uchun. FAQAT approve_asset() haqiqatan Telegram kanaliga yuboradi.
def list_assets(project_id: int, query: dict) -> tuple[int, object]:
    """MUHIM: bu yerda content HAR DOIM sanitize_telegram_html() orqali
    o'tkaziladi — DB'dagi xom holatidan qat'i nazar. generate_post()
    pipeline'i allaqachon tozalab saqlaydi, LEKIN bu fix'dan OLDIN
    yaratilgan eski draft'larda xom '<br>' qolib ketishi mumkin edi, va
    server startup'dagi bir martalik migratsiya (resanitize_draft_assets)
    hali ishlamagan yoki keyinroq yaratilgan holatlar ham bo'lishi mumkin.
    Shu tozalash har o'qishda qo'llanadi (arzon, sof funksiya) — agar
    farq topilsa, DB'ga ham darhol yozib qo'yiladi (self-heal), shunda
    bu asset boshqa hech qachon xom holatda ko'rinmaydi."""
    status = (query or {}).get('status') or 'draft'
    try:
        assets = database.get_assets(project_id, status=status)
        for a in assets:
            raw = a.get('content') or ''
            cleaned = telegram_utils.sanitize_telegram_html(raw)
            if cleaned != raw:
                a['content'] = cleaned
                try:
                    database.update_asset_content(a['id'], cleaned, a.get('title'))
                except Exception as e:
                    log.warning(f'[StudioAPI] list_assets: self-heal xato (asset={a["id"]}): {e}')
        return 200, assets
    except Exception as e:
        log.error(f'[StudioAPI] list_assets: {e}')
        return 500, {'error': str(e)}


def update_asset(data: dict) -> tuple[int, object]:
    asset_id = data.get('id')
    content = data.get('content')
    if asset_id is None or content is None:
        return 400, {'error': 'id va content kerak'}
    title = data.get('title')
    try:
        database.update_asset_content(int(asset_id), content, title)
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] update_asset: {e}')
        return 500, {'error': str(e)}


def _publish_asset_now(asset: dict, reviewer: str = 'dashboard', notes: str = '') -> tuple[int, object]:
    """Postni HAQIQATAN Telegram kanaliga yuboradi va 'published' deb
    belgilaydi. Ichki funksiya — to'g'ridan-to'g'ri (interval sozlanmagan
    loyihalarda, orqaga moslik) va scheduler (interval sozlangan
    loyihalarda, navbatdan chiqqanda) IKKALASI HAM shu yerdan o'tadi —
    kanalga chiqishning yagona yo'li."""
    asset_id = asset['id']
    # MUHIM: postni QAYSI loyiha yaratgan bo'lsa, aynan O'SHA loyihaning
    # Telegram kanaliga yuboriladi — so'rov qaysi loyihadan kelganidan
    # qat'i nazar. Bu bitta bot bir nechta kanalga xizmat qilishi uchun
    # to'g'ri manzilni kafolatlaydi (bir loyiha posti boshqa loyiha
    # kanaliga tasodifan chiqib qolmasligi uchun).
    owner_config = database.get_workflow_config(asset['project_id'])
    target_channel = owner_config.get('telegram_channel_id') or None

    result = telegram_utils.tg_channel(
        asset['content'], image_url=asset.get('image_url'), chat_id=target_channel,
    )
    if not result.get('ok'):
        log.error(f'[StudioAPI] _publish_asset_now: TG xato: {result.get("description")}')
        return 502, {'error': f"Telegram xato: {result.get('description')}"}

    database.mark_asset_published(asset_id)
    database.add_review(asset_id, reviewer=reviewer, decision='approved', notes=notes)
    # Mini App (/webapp) endi FAQAT tasdiqlangan postlarni ko'rsatadi —
    # shuning uchun published_posts jadvaliga ham yozamiz. MUHIM: postning
    # O'Z LOYIHASI (asset['project_id']) bilan bog'lab saqlanadi — aks
    # holda boshqa loyihaning Mini App'ida bu post ham ko'rinib qolardi.
    database.save_post(asset['project_id'], asset.get('source_url'), asset['title'], asset['content'], asset.get('image_url'))
    log.info(f'[StudioAPI] Asset #{asset_id} kanalga yuborildi.')
    return 200, {'ok': True}


def approve_asset(data: dict) -> tuple[int, object]:
    """Postni tasdiqlaydi. FAQAT shu funksiya orqali post kanalga chiqish
    yo'liga kiradi — bot buyruqlarida bunday imkoniyat yo'q.

    Agar loyihada publish_interval_minutes > 0 sozlangan bo'lsa (Dashboard
    -> Loyiha sozlamalari), post DARHOL yubormaydi — status='scheduled'
    bilan navbatga qo'yiladi, background scheduler (main.py'dagi
    publish_scheduler_loop) o'z vaqtida chiqaradi. Sozlanmagan bo'lsa
    (default, orqaga moslik) — eski xatti-harakat: darhol yuboriladi."""
    asset_id = data.get('id')
    if asset_id is None:
        return 400, {'error': 'id kerak'}
    asset_id = int(asset_id)
    asset = database.get_asset(asset_id)
    if not asset:
        return 404, {'error': 'topilmadi'}
    if asset.get('status') in ('published', 'scheduled'):
        return 400, {'error': 'bu post allaqachon tasdiqlangan'}

    reviewer = data.get('reviewer', 'dashboard')
    notes = data.get('notes', '')

    config = database.get_workflow_config(asset['project_id'])
    try:
        interval_minutes = int(config.get('publish_interval_minutes') or 0)
    except (TypeError, ValueError):
        interval_minutes = 0

    if interval_minutes > 0:
        database.schedule_asset(asset_id)
        database.add_review(asset_id, reviewer=reviewer, decision='approved', notes=notes)
        log.info(f"[StudioAPI] Asset #{asset_id} navbatga qo'yildi (interval={interval_minutes} daq).")
        return 200, {'ok': True, 'scheduled': True, 'publish_interval_minutes': interval_minutes}

    status, payload = _publish_asset_now(asset, reviewer=reviewer, notes=notes)
    if status == 200:
        payload = {**payload, 'scheduled': False}
    return status, payload


def publish_due_scheduled(project_id: int) -> None:
    """Background scheduler (main.py) har loyiha uchun davriy chaqiradi:
    agar loyihada publish_interval_minutes sozlangan va oxirgi
    nashrdan beri shu vaqt o'tgan bo'lsa, navbatdagi ENG ESKI postni
    chiqaradi. Bir chaqiruvda FAQAT bitta post chiqadi — keyingisi
    navbatdagi keyingi tsiklda (interval to'liq qayta o'tgach) ketadi."""
    config = database.get_workflow_config(project_id)
    try:
        interval_minutes = int(config.get('publish_interval_minutes') or 0)
    except (TypeError, ValueError):
        interval_minutes = 0
    if interval_minutes <= 0:
        return

    import datetime as _dt
    last_published = database.get_last_published_at(project_id)
    if last_published is not None:
        now = _dt.datetime.now(_dt.timezone.utc)
        last_dt = last_published if last_published.tzinfo else last_published.replace(tzinfo=_dt.timezone.utc)
        elapsed_minutes = (now - last_dt).total_seconds() / 60
        if elapsed_minutes < interval_minutes:
            return

    asset = database.get_next_scheduled_asset(project_id)
    if not asset:
        return

    status, payload = _publish_asset_now(asset, reviewer='scheduler', notes="publish_interval_minutes bo'yicha avtomatik chiqarildi")
    if status != 200:
        log.error(f'[Scheduler] (loyiha={project_id}) Asset #{asset["id"]} chiqarishda xato: {payload}')


def reject_asset(data: dict) -> tuple[int, object]:
    asset_id = data.get('id')
    if asset_id is None:
        return 400, {'error': 'id kerak'}
    asset_id = int(asset_id)
    try:
        database.set_asset_status(asset_id, 'rejected')
        database.add_review(
            asset_id,
            reviewer=data.get('reviewer', 'dashboard'),
            decision='rejected',
            notes=data.get('notes', ''),
        )
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] reject_asset: {e}')
        return 500, {'error': str(e)}


def unschedule_asset(data: dict) -> tuple[int, object]:
    """Navbatdagi postni bekor qiladi — qaytadan Review Queue'ga
    (status='draft') qo'yadi, admin qayta ko'rib chiqishi mumkin."""
    asset_id = data.get('id')
    if asset_id is None:
        return 400, {'error': 'id kerak'}
    asset_id = int(asset_id)
    asset = database.get_asset(asset_id)
    if not asset or asset.get('status') != 'scheduled':
        return 400, {'error': "bu post navbatda emas"}
    try:
        database.unschedule_asset(asset_id)
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] unschedule_asset: {e}')
        return 500, {'error': str(e)}


def submit_manual_content(project_id: int, data: dict) -> tuple[int, object]:
    """Dashboard'dan qo'lda kiritilgan xom matn (boshqa tilda bo'lishi ham
    mumkin) — pipeline uni tarjima qilib, formatlab, Review Queue'ga
    (status='draft') qo'shadi. Kanalga hech narsa avtomatik yuborilmaydi."""
    text = (data.get('text') or '').strip()
    if not text:
        return 400, {'error': 'text kerak'}
    image_url = (data.get('image_url') or '').strip() or None

    used = database.get_today_api_calls(project_id)
    if used >= DAILY_API_LIMIT:
        return 429, {'error': f"Kunlik API byudjeti tugagan ({used}/{DAILY_API_LIMIT})"}

    try:
        from workflows.rss_news import generate_post
        article = {'title': text[:120], 'description': '', 'url': None, 'score': 100}
        post = generate_post(article, project_id)
        database.increment_api_calls(project_id, CALLS_PER_POST)
        asset = database.create_asset(
            project_id=project_id,
            source_url=None,
            asset_type='manual',
            title=text[:80],
            content=post,
            score=100,
            image_url=image_url,
        )
        log.info(f'[StudioAPI] Qo\'lda kiritilgan kontent Review Queue-ga qo\'shildi (asset #{asset["id"]}).')
        return 200, asset
    except Exception as e:
        database.increment_api_calls(project_id, CALLS_PER_POST)
        log.error(f'[StudioAPI] submit_manual_content: {e}')
        return 500, {'error': str(e)}


# ── Loyihalar (CaaS: bitta Dashboard — ko'p loyiha) ────────────────
def list_projects(_project_id, _query) -> tuple[int, object]:
    try:
        return 200, database.list_projects()
    except Exception as e:
        log.error(f'[StudioAPI] list_projects: {e}')
        return 500, {'error': str(e)}


def create_project(_project_id, data: dict) -> tuple[int, object]:
    name = (data.get('name') or '').strip()
    if not name:
        return 400, {'error': 'name kerak'}
    slug = (data.get('slug') or '').strip()
    if not slug:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if not slug:
        return 400, {'error': "slug yaratib bo'lmadi — name'da lotin harflari/raqam bo'lishi kerak"}
    try:
        project = database.get_or_create_project(slug, name)
        log.info(f"[StudioAPI] Yangi loyiha yaratildi: {slug} ({name}, id={project['id']})")
        return 200, project
    except Exception as e:
        log.error(f'[StudioAPI] create_project: {e}')
        return 500, {'error': str(e)}


def delete_project(project_id: int, _data: dict) -> tuple[int, object]:
    """Loyihani va unga tegishli barcha ma'lumotlarni butunlay o'chiradi.
    Boshqa loyihalarga tegmaydi (database.delete_project() faqat shu
    project_id bo'yicha filtrlangan qatorlarni o'chiradi)."""
    if project_id is None:
        return 400, {'error': 'project_id kerak'}
    try:
        ok = database.delete_project(int(project_id))
        if not ok:
            return 404, {'error': 'loyiha topilmadi'}
        log.info(f'[StudioAPI] Loyiha o\'chirildi: {project_id}')
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] delete_project: {e}')
        return 500, {'error': str(e)}


def reset_api_budget(project_id: int, _data: dict) -> tuple[int, object]:
    """Loyihaning BUGUNGI ichki API hisoblagichini nolga tushiradi.
    Sinov/debug paytida ichki kunlik limit (DAILY_POST_BUDGET) tugab
    qolganda Dashboard'dan qo'lda tozalash uchun. Haqiqiy Gemini
    kvotasiga (Google tomonida) ta'sir qilmaydi."""
    try:
        database.reset_today_api_calls(project_id)
        log.info(f'[StudioAPI] Kunlik API byudjeti tozalandi (project={project_id}).')
        return 200, {'ok': True}
    except Exception as e:
        log.error(f'[StudioAPI] reset_api_budget: {e}')
        return 500, {'error': str(e)}


# ── Rasmlar: yuklash (upload) ────────────────────────────────────
# asset_id talab qilmaydi — New Request'da asset hali yaratilmasdan
# turib rasm tanlanadi (image_url keyin submit_manual_content orqali
# create_asset()ga beriladi), Review Queue'da esa mavjud draft'ning
# rasmini almashtirish uchun alohida set_asset_image() ishlatiladi.
_MAX_UPLOAD_BYTES = 15_000_000
_ALLOWED_IMAGE_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


def upload_image(project_id: int, data: dict) -> tuple[int, object]:
    """Dashboard'dan yuklangan rasmni DB'ga saqlaydi va shu serverning
    o'zidan ochiladigan (to'liq, https://... bilan boshlanuvchi) URL
    qaytaradi — tashqi fayl-hosting shart emas.

    Ochiq manzil (base_url) ODATDA so'rovning o'zidan (Host/
    X-Forwarded-Proto headerlari, main.py'da aniqlanadi va
    data['_request_base_url']ga qo'yiladi) avtomatik olinadi — admin
    hech qanday qo'shimcha sozlash qilishi shart emas. PUBLIC_BASE_URL
    .env o'zgaruvchisi faqat ZAXIRA (masalan agar so'rov proksi ortidan
    kelib, header'lar ishonchli bo'lmasa)."""
    import base64

    content_type = (data.get('content_type') or '').strip().lower()
    if content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        return 400, {'error': f"content_type quyidagilardan biri bo'lishi kerak: {', '.join(sorted(_ALLOWED_IMAGE_CONTENT_TYPES))}"}

    b64 = (data.get('image_base64') or '').strip()
    if not b64:
        return 400, {'error': 'image_base64 kerak'}
    if b64.startswith('data:'):
        b64 = b64.split(',', 1)[-1]

    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        return 400, {'error': "image_base64 noto'g'ri formatda"}

    if not raw:
        return 400, {'error': "Rasm bo'sh"}
    if len(raw) > _MAX_UPLOAD_BYTES:
        return 400, {'error': f"Rasm juda katta (max {_MAX_UPLOAD_BYTES // 1_000_000}MB)"}

    try:
        upload_id = database.save_upload(project_id, content_type, raw)
    except Exception as e:
        log.error(f'[StudioAPI] upload_image: {e}')
        return 500, {'error': str(e)}

    base_url = (data.get('_request_base_url') or PUBLIC_BASE_URL or '').rstrip('/')
    if not base_url:
        log.warning('[StudioAPI] Ochiq manzil aniqlanmadi — yuklangan rasm URL nisbiy qoladi, Telegram unga ulana olmaydi.')
        url = f'/api/image/{upload_id}'
    else:
        url = f'{base_url}/api/image/{upload_id}'

    log.info(f'[StudioAPI] Rasm yuklandi (project={project_id}, upload_id={upload_id}, {len(raw)} bayt, url={url}).')
    return 200, {'id': upload_id, 'url': url}


def set_asset_image(data: dict) -> tuple[int, object]:
    """Review Queue'dagi mavjud draft'ning rasmini o'rnatadi/almashtiradi
    (upload'dan tanlangan URL bilan). Rasmni olib tashlash uchun
    image_url bo'sh yuboriladi."""
    asset_id = data.get('id')
    if asset_id is None:
        return 400, {'error': 'id kerak'}
    image_url = (data.get('image_url') or '').strip() or None
    try:
        database.update_asset_image(int(asset_id), image_url)
        return 200, {'ok': True, 'image_url': image_url}
    except Exception as e:
        log.error(f'[StudioAPI] set_asset_image: {e}')
        return 500, {'error': str(e)}


# ── Route jadvallari — main.py shu yerdan dispatch qiladi ──────────
# GET: (project_id, query_dict) -> (status, payload)
GET_ROUTES = {
    '/api/studio/projects': list_projects,
    '/api/studio/sources': lambda project_id, _q: list_sources(project_id),
    '/api/studio/config':  lambda project_id, _q: get_config(project_id),
    '/api/studio/assets':  lambda project_id, q: list_assets(project_id, q),
    '/api/studio/stats':   lambda project_id, _q: get_dashboard_stats(project_id),
}

# POST: (project_id, body_dict) -> (status, payload)
POST_ROUTES = {
    '/api/studio/projects':         create_project,
    '/api/studio/projects/delete':  lambda project_id, body: delete_project(project_id, body),
    '/api/studio/sources':          lambda project_id, body: add_source(project_id, body),
    '/api/studio/sources/update':   lambda project_id, body: update_source_meta(body),
    '/api/studio/sources/toggle':   lambda project_id, body: toggle_source(body),
    '/api/studio/sources/delete':   lambda project_id, body: delete_source(body),
    '/api/studio/config':           lambda project_id, body: update_config(project_id, body),
    '/api/studio/assets/update':    lambda project_id, body: update_asset(body),
    '/api/studio/assets/approve':   lambda project_id, body: approve_asset(body),
    '/api/studio/assets/reject':    lambda project_id, body: reject_asset(body),
    '/api/studio/assets/unschedule': lambda project_id, body: unschedule_asset(body),
    '/api/studio/assets/submit':    lambda project_id, body: submit_manual_content(project_id, body),
    '/api/studio/assets/set_image': lambda project_id, body: set_asset_image(body),
    '/api/studio/images/upload':    lambda project_id, body: upload_image(project_id, body),
    '/api/studio/budget/reset':     lambda project_id, body: reset_api_budget(project_id, body),
}
