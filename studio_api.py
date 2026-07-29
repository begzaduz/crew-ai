"""Studio Lab Dashboard uchun REST API funksiyalari.

main.py'dagi HTTP handler (WebhookHandler) shu funksiyalarni GET_ROUTES /
POST_ROUTES orqali chaqiradi. Har bir funksiya (http_status, json_payload)
juftligini qaytaradi — HTTP transport qatlamidan mustaqil, shuning uchun
kelajakda boshqa transport (masalan haqiqiy web-framework)ga o'tish oson.
"""
import logging

import database

log = logging.getLogger(__name__)


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


# ── Route jadvallari — main.py shu yerdan dispatch qiladi ──────────
# GET: (project_id, _unused_body) -> (status, payload)
GET_ROUTES = {
    '/api/studio/sources': lambda project_id, _body: list_sources(project_id),
    '/api/studio/config':  lambda project_id, _body: get_config(project_id),
}

# POST: (project_id, body_dict) -> (status, payload)
POST_ROUTES = {
    '/api/studio/sources':          lambda project_id, body: add_source(project_id, body),
    '/api/studio/sources/toggle':   lambda project_id, body: toggle_source(body),
    '/api/studio/sources/delete':   lambda project_id, body: delete_source(body),
    '/api/studio/config':           lambda project_id, body: update_config(project_id, body),
}
