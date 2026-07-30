"""Telegram bilan bog'liq past-darajali funksiyalar.

Alohida faylga chiqarilgan, chunki bu funksiyalarni ikkala joy ham
ishlatadi: main.py (bot xabarlariga javob) VA studio_api.py (Dashboard'da
"Tasdiqlash" bosilganda postni kanalga yuborish). Agar bular main.py ichida
qolganida, studio_api.py'dan main.py'ni import qilish kerak bo'lardi, bu esa
main.py studio_api.py'ni import qilgani uchun circular import hosil qilardi.
"""
import re
import logging

import requests

from config import TOKEN, CHANNEL, ADMIN_IDS

log = logging.getLogger(__name__)


def tg_send(chat_id: int | str, text: str, reply_markup: dict | None = None) -> dict:
    payload: dict = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        res = requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json=payload,
            timeout=15,
        )
        return res.json()
    except Exception as e:
        log.error(f'[TG] tg_send xato: {e}')
        return {'ok': False, 'description': str(e)}


def notify_admins(text: str) -> None:
    """Barcha adminlarga xabar yuboradi (masalan xatolar haqida)."""
    for admin_id in ADMIN_IDS:
        tg_send(admin_id, text)


def _clean_post(post: str) -> str:
    """
    Sarlavha qatorini <b>...</b> bilan o'raydi (agar allaqachon o'ralmagan bo'lsa).
    Boshlang'ich emoji bo'lsa, uni bold tashqarisida qoldiradi:
    masalan "🚨 Sarlavha matni" -> "🚨 <b>Sarlavha matni</b>"
    """
    lines = post.split('\n')
    cleaned = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if i == 0 and stripped:
            bold_match = re.search(r'<b>(.*?)</b>', stripped)
            if bold_match:
                cleaned.append(f'<b>{bold_match.group(1)}</b>')
            else:
                m = re.match(r'^([\U0001F300-\U0001FAFF\u2600-\u27BF]+\s*)?(.*)$', stripped)
                prefix = m.group(1) or ''
                title = m.group(2).strip()
                cleaned.append(f'{prefix}<b>{title}</b>' if title else stripped)
        else:
            cleaned.append(line)
    return '\n'.join(cleaned)


def tg_channel(text: str, image_url: str | None = None) -> dict:
    """
    Kanalga yuborish (FAQAT Dashboard'da 'Tasdiqlash' bosilganda chaqiriladi):
    - image_url bo'lsa: sendPhoto (rasm + caption HTML)
    - bo'lmasa: sendMessage (faqat matn HTML)
    """
    text = _clean_post(text)

    if image_url:
        caption = text[:1024]
        res = requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendPhoto',
            json={
                'chat_id': CHANNEL,
                'photo': image_url,
                'caption': caption,
                'parse_mode': 'HTML',
            },
            timeout=15,
        )
        result = res.json()
        if not result.get('ok'):
            log.warning(f'[TG] sendPhoto xato: {result.get("description")} — matn sifatida yuborilmoqda')
            return tg_channel(text, image_url=None)
        return result
    else:
        res = requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={
                'chat_id': CHANNEL,
                'text': text,
                'parse_mode': 'HTML',
            },
            timeout=15,
        )
        return res.json()
