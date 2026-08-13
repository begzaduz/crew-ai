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

# Telegram HTML parse_mode FAQAT shu teglarni tushunadi. Manba maqoladan
# yoki AI generatsiyasidan boshqa teg (masalan <br>, <p>, <div>) sizib
# kirsa, Telegram butun xabarni "can't parse entities" xatosi bilan rad
# etadi. Shuning uchun yuborishdan oldin har doim tozalanadi.
_TG_ALLOWED_TAGS = {
    'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del',
    'a', 'code', 'pre', 'tg-spoiler', 'span',
}


def sanitize_telegram_html(text: str) -> str:
    """Telegram qo'llab-quvvatlamaydigan HTML teglarni tozalaydi.
    <br>, <br/>, <br />, va ba'zan AI chiqargan bo'shliqli variantlar
    ('< br >', '< br/ >') — barchasi yangi qatorga aylantiriladi (mazmun
    yo'qolmasin uchun). Boshqa ruxsat etilmagan teglar olib tashlanadi,
    lekin ichidagi matn saqlanadi (faqat teg belgisi olinadi) — bu ham
    xuddi shunday bo'shliqli variantlarni hisobga oladi."""
    if not text:
        return text
    text = re.sub(r'<\s*br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)

    def _strip_disallowed(m: re.Match) -> str:
        tag = m.group(1).lower().lstrip('/')
        return m.group(0) if tag in _TG_ALLOWED_TAGS else ''

    text = re.sub(r'<\s*/?\s*([a-zA-Z][a-zA-Z0-9-]*)\b[^>]*>', _strip_disallowed, text)
    return text


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
    Avval Telegram tushunmaydigan teglarni tozalaydi (masalan <br> -> \\n),
    keyin sarlavha qatorini <b>...</b> bilan o'raydi (agar allaqachon
    o'ralmagan bo'lsa). Boshlang'ich emoji bo'lsa, uni bold tashqarisida
    qoldiradi: masalan "🚨 Sarlavha matni" -> "🚨 <b>Sarlavha matni</b>"
    """
    post = sanitize_telegram_html(post)
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


def tg_channel(text: str, image_url: str | None = None, chat_id: str | int | None = None,
                bot_token: str | None = None) -> dict:
    """
    Kanalga yuborish (FAQAT Dashboard'da 'Tasdiqlash' bosilganda chaqiriladi):
    - image_url bo'lsa: sendPhoto (rasm + caption HTML)
    - bo'lmasa: sendMessage (faqat matn HTML)

    chat_id — loyihaning o'z Telegram kanali (workflows.config'dagi
    'telegram_channel_id'). Berilmasa (masalan hali sozlanmagan eski
    loyiha bo'lsa), global CHANNEL (.env) ishlatiladi.

    bot_token — loyihaning O'Z Telegram bot tokeni (workflows.config'dagi
    'telegram_bot_token', gemini_api_key bilan bir xil naqsh: har loyiha
    DB orqali o'z botini sozlashi mumkin, kodga hech qanday bot qattiq
    bog'lanmagan). Berilmasa, global TOKEN (.env — "Ingliz Futboli" o'z
    loyiha boti) ishlatiladi — orqaga moslik, eski loyihalarga ta'sir
    qilmaydi. MUHIM: bu faqat KANALGA YUBORISH uchun — bot buyruqlariga
    javob (tg_send) har doim global TOKEN bilan ishlaydi, chunki admin
    buyruqlar (masalan /yangilik) doim "Ingliz Futboli" loyiha botiga
    keladi.
    """
    text = _clean_post(text)
    target = chat_id or CHANNEL
    token = bot_token or TOKEN

    if image_url:
        caption = text[:1024]
        res = requests.post(
            f'https://api.telegram.org/bot{token}/sendPhoto',
            json={
                'chat_id': target,
                'photo': image_url,
                'caption': caption,
                'parse_mode': 'HTML',
            },
            timeout=15,
        )
        result = res.json()
        if not result.get('ok'):
            log.warning(f'[TG] sendPhoto xato: {result.get("description")} — matn sifatida yuborilmoqda')
            return tg_channel(text, image_url=None, chat_id=chat_id, bot_token=bot_token)
        return result
    else:
        res = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': target,
                'text': text,
                'parse_mode': 'HTML',
            },
            timeout=15,
        )
        return res.json()
