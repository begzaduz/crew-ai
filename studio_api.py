"""Studio Lab Dashboard uchun REST API funksiyalari.

main.py'dagi HTTP handler (WebhookHandler) shu funksiyalarni GET_ROUTES /
POST_ROUTES orqali chaqiradi. Har bir funksiya (http_status, json_payload)
juftligini qaytaradi — HTTP transport qatlamidan mustaqil, shuning uchun
kelajakda boshqa transport (masalan haqiqiy web-framework)ga o'tish oson.
"""
import logging

import database
import telegram_utils
from config import DAILY_POST_BUDGET

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
        row = database.add_data_source(project_id, url)
        log.info(f'[StudioAPI] Yangi manba qo\'shildi (project={project_id}): {url}')
        return 200, row
    except Exception as e:
        log.error(f'[StudioAPI] add_source: {e}')
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
        return 200, cfg
    except Exception as e:
        log.error(f'[StudioAPI] get_config: {e}')
        return 500, {'error': str(e)}


_ALLOWED_CONFIG_KEYS = {'terminology', 'nicknames', 'channel_tag', 'tone'}


def update_config(project_id: int, data: dict) -> tuple[int, object]:
    patch = {k: v for k, v in data.items() if k in _ALLOWED_CONFIG_KEYS}
    if not patch:
        return 400, {'error': "saqlanadigan maydon topilmadi (terminology/nicknames/channel_tag/tone)"}
    if 'terminology' in patch and not isinstance(patch['terminology'], dict):
        return 400, {'error': "terminology obyekt (key-value) bo'lishi kerak"}
    if 'nicknames' in patch and not isinstance(patch['nicknames'], dict):
        return 400, {'error': "nicknames obyekt (key-value) bo'lishi kerak"}
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
def get_dashboard_stats(project_id: int) -> tuple[int, object]:
    try:
        import datetime as _dt
        drafts = database.get_assets(project_id, status='draft', limit=200)
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

        return 200, {
            'pending_review': len(drafts),
            'published_total': len(published),
            'rejected_total': len(rejected),
            'posts_today': posts_today,
            'active_sources': sum(1 for s in sources if s.get('active')),
            'total_sources': len(sources),
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
    status = (query or {}).get('status') or 'draft'
    try:
        return 200, database.get_assets(project_id, status=status)
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


def approve_asset(data: dict) -> tuple[int, object]:
    """Postni Telegram kanaliga yuboradi va 'published' deb belgilaydi.
    FAQAT shu funksiya orqali kanalga chiqish mumkin — bot buyruqlarida
    bunday imkoniyat yo'q."""
    asset_id = data.get('id')
    if asset_id is None:
        return 400, {'error': 'id kerak'}
    asset_id = int(asset_id)
    asset = database.get_asset(asset_id)
    if not asset:
        return 404, {'error': 'topilmadi'}
    if asset.get('status') == 'published':
        return 400, {'error': 'bu post allaqachon yuborilgan'}

    result = telegram_utils.tg_channel(asset['content'], image_url=asset.get('image_url'))
    if not result.get('ok'):
        log.error(f'[StudioAPI] approve_asset: TG xato: {result.get("description")}')
        return 502, {'error': f"Telegram xato: {result.get('description')}"}

    database.mark_asset_published(asset_id)
    database.add_review(
        asset_id,
        reviewer=data.get('reviewer', 'dashboard'),
        decision='approved',
        notes=data.get('notes', ''),
    )
    # Mini App (/webapp) endi FAQAT tasdiqlangan postlarni ko'rsatadi —
    # shuning uchun published_posts jadvaliga ham yozamiz.
    database.save_post(asset.get('source_url'), asset['title'], asset['content'], asset.get('image_url'))
    log.info(f'[StudioAPI] Asset #{asset_id} tasdiqlandi va kanalga yuborildi.')
    return 200, {'ok': True}


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


def submit_manual_content(project_id: int, data: dict) -> tuple[int, object]:
    """Dashboard'dan qo'lda kiritilgan xom matn (boshqa tilda bo'lishi ham
    mumkin) — pipeline uni tarjima qilib, formatlab, Review Queue'ga
    (status='draft') qo'shadi. Kanalga hech narsa avtomatik yuborilmaydi."""
    text = (data.get('text') or '').strip()
    if not text:
        return 400, {'error': 'text kerak'}

    used = database.get_today_api_calls()
    if used >= DAILY_API_LIMIT:
        return 429, {'error': f"Kunlik API byudjeti tugagan ({used}/{DAILY_API_LIMIT})"}

    try:
        from workflows.rss_news import generate_post
        article = {'title': text[:120], 'description': '', 'url': None, 'score': 100}
        post = generate_post(article, project_id)
        database.increment_api_calls(CALLS_PER_POST)
        asset = database.create_asset(
            project_id=project_id,
            source_url=None,
            asset_type='manual',
            title=text[:80],
            content=post,
            score=100,
            image_url=None,
        )
        log.info(f'[StudioAPI] Qo\'lda kiritilgan kontent Review Queue-ga qo\'shildi (asset #{asset["id"]}).')
        return 200, asset
    except Exception as e:
        database.increment_api_calls(CALLS_PER_POST)
        log.error(f'[StudioAPI] submit_manual_content: {e}')
        return 500, {'error': str(e)}


# ── Route jadvallari — main.py shu yerdan dispatch qiladi ──────────
# GET: (project_id, query_dict) -> (status, payload)
GET_ROUTES = {
    '/api/studio/sources': lambda project_id, _q: list_sources(project_id),
    '/api/studio/config':  lambda project_id, _q: get_config(project_id),
    '/api/studio/assets':  lambda project_id, q: list_assets(project_id, q),
    '/api/studio/stats':   lambda project_id, _q: get_dashboard_stats(project_id),
}

# POST: (project_id, body_dict) -> (status, payload)
POST_ROUTES = {
    '/api/studio/sources':          lambda project_id, body: add_source(project_id, body),
    '/api/studio/sources/toggle':   lambda project_id, body: toggle_source(body),
    '/api/studio/sources/delete':   lambda project_id, body: delete_source(body),
    '/api/studio/config':           lambda project_id, body: update_config(project_id, body),
    '/api/studio/assets/update':    lambda project_id, body: update_asset(body),
    '/api/studio/assets/approve':   lambda project_id, body: approve_asset(body),
    '/api/studio/assets/reject':    lambda project_id, body: reject_asset(body),
    '/api/studio/assets/submit':    lambda project_id, body: submit_manual_content(project_id, body),
}
