import logging

import requests

from config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_CX

log = logging.getLogger(__name__)

_SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'


def is_configured() -> bool:
    return bool(GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX)


def search_images(query: str, count: int = 8) -> list[dict] | None:
    """Google Custom Search (Image) orqali rasm qidiradi.

    Qaytadi: [{"url": "...", "thumbnail": "...", "title": "..."}]
    Kalitlar sozlanmagan yoki so'rov xato bo'lsa — None (chaqiruvchi
    buni "funksiya o'chirilgan/xato" deb talqin qilishi kerak).
    """
    if not is_configured():
        return None
    query = (query or '').strip()
    if not query:
        return []
    try:
        res = requests.get(
            _SEARCH_URL,
            params={
                'key': GOOGLE_SEARCH_API_KEY,
                'cx': GOOGLE_SEARCH_CX,
                'q': query,
                'searchType': 'image',
                'num': min(max(int(count), 1), 10),
                'safe': 'active',
            },
            timeout=10,
        )
        res.raise_for_status()
        items = res.json().get('items', []) or []
        results = []
        for it in items:
            link = it.get('link')
            if not link:
                continue
            image_meta = it.get('image') or {}
            results.append({
                'url': link,
                'thumbnail': image_meta.get('thumbnailLink') or link,
                'title': it.get('title', ''),
            })
        return results
    except Exception as e:
        log.error(f'[ImageSearch] Google Custom Search xato: {e}')
        return None
