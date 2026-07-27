"""
studio_api.py
─────────────────────────────────────────────────────────────
Studio Lab dashboard uchun API qatlami.

Bu fayl HECH QANDAY loyihaga (Ingliz Futboli'ga ham) qattiq
bog'lanmagan — barcha endpoint'lar project_id parametr orqali
ishlaydi, shuning uchun ertaga ikkinchi loyiha qo'shilganda
bu kodga tegish shart emas.

Himoya: oddiy Bearer token (.env'dagi STUDIO_ADMIN_TOKEN).
Login sahifasi tokenni so'raydi, frontend uni localStorage'da
saqlab, har bir so'rovga 'Authorization: Bearer <token>' sifatida
qo'shadi.
"""

import os
import hmac
import logging

from studio_schema import (
    list_projects, get_project_by_slug,
    list_data_sources, set_data_source_enabled,
    get_workflow, update_workflow_config,
    list_assets, set_asset_status, update_asset_content,
    list_outputs, set_output_enabled,
)

log = logging.getLogger(__name__)

STUDIO_ADMIN_TOKEN = os.getenv('STUDIO_ADMIN_TOKEN', '')

if not STUDIO_ADMIN_TOKEN:
    log.error(
        '[Studio API] STUDIO_ADMIN_TOKEN .env\'da o\'rnatilmagan! '
        'Xavfsizlik uchun dashboard API endi FAIL-CLOSED ishlaydi — '
        'token o\'rnatilmaguncha barcha so\'rovlar rad etiladi (401). '
        'Railway → Variables → STUDIO_ADMIN_TOKEN qo\'shing.'
    )


def _check_auth(headers) -> bool:
    """Token yo'q bo'lsa — HAR DOIM rad etadi (fail-closed). Eski
    "token yo'q bo'lsa hammaga ochiq" xatti-harakati olib tashlandi,
    chunki bu real xavfsizlik teshigi edi."""
    if not STUDIO_ADMIN_TOKEN:
        return False
    auth_header = headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip()
    return hmac.compare_digest(token, STUDIO_ADMIN_TOKEN)


def _require_project_id(query: dict) -> int | None:
    raw = (query.get('project_id') or [''])[0]
    try:
        pid = int(raw)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


# ═══════════════════════════════════════════════════════════
#  GET
# ═══════════════════════════════════════════════════════════
def handle_get(path: str, query: dict, headers) -> tuple[int, dict | list]:
    if not _check_auth(headers):
        return 401, {'error': 'unauthorized'}

    try:
        if path == '/api/studio/projects':
            return 200, list_projects()

        if path == '/api/studio/project':
            slug = (query.get('slug') or [''])[0]
            project = get_project_by_slug(slug)
            return (200, project) if project else (404, {'error': 'loyiha topilmadi'})

        if path == '/api/studio/sources':
            project_id = _require_project_id(query)
            if project_id is None:
                return 400, {'error': 'project_id kerak'}
            return 200, list_data_sources(project_id)

        if path == '/api/studio/workflow':
            project_id = _require_project_id(query)
            if project_id is None:
                return 400, {'error': 'project_id kerak'}
            wf_type = (query.get('type') or ['content_production'])[0]
            wf = get_workflow(project_id, wf_type)
            return (200, wf) if wf else (404, {'error': 'workflow topilmadi'})

        if path == '/api/studio/queue':
            project_id = _require_project_id(query)
            if project_id is None:
                return 400, {'error': 'project_id kerak'}
            status = (query.get('status') or [None])[0]
            return 200, list_assets(project_id, status)

        if path == '/api/studio/outputs':
            project_id = _require_project_id(query)
            if project_id is None:
                return 400, {'error': 'project_id kerak'}
            return 200, list_outputs(project_id)

        return 404, {'error': 'noma\'lum endpoint'}

    except Exception as e:
        log.error(f'[Studio API] GET {path} xato: {e}')
        return 500, {'error': str(e)}


# ═══════════════════════════════════════════════════════════
#  POST  (harakat qiluvchi endpoint'lar)
# ═══════════════════════════════════════════════════════════
def handle_post(path: str, body: dict, headers) -> tuple[int, dict]:
    if not _check_auth(headers):
        return 401, {'error': 'unauthorized'}

    try:
        if path == '/api/studio/sources/toggle':
            set_data_source_enabled(int(body['id']), bool(body['enabled']))
            return 200, {'ok': True}

        if path == '/api/studio/outputs/toggle':
            set_output_enabled(int(body['id']), bool(body['enabled']))
            return 200, {'ok': True}

        if path == '/api/studio/workflow/update':
            wf_id = int(body['workflow_id'])
            update_workflow_config(wf_id, body['config'])
            return 200, {'ok': True}

        if path == '/api/studio/assets/update':
            update_asset_content(
                asset_id=int(body['asset_id']),
                title=body.get('title', ''),
                content=body['content'],
                reviewer=body.get('reviewer', 'admin'),
            )
            if body.get('approve_after'):
                set_asset_status(int(body['asset_id']), 'approved',
                                  reviewer=body.get('reviewer', 'admin'),
                                  notes='Tahrirlangandan keyin tasdiqlandi')
            return 200, {'ok': True}

        if path == '/api/studio/assets/review':
            # decision: 'approved' / 'rejected'
            set_asset_status(
                asset_id=int(body['asset_id']),
                status=body['decision'],
                reviewer=body.get('reviewer', 'admin'),
                notes=body.get('notes', ''),
            )
            return 200, {'ok': True}

        return 404, {'error': 'noma\'lum endpoint'}

    except KeyError as e:
        return 400, {'error': f'{e} maydoni kerak'}
    except Exception as e:
        log.error(f'[Studio API] POST {path} xato: {e}')
        return 500, {'error': str(e)}
