import json
import re
import time
import hmac
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import requests

from config import TOKEN, CHANNEL, ADMIN_IDS, PORT, INTERVAL, WEBHOOK_SECRET, DAILY_POST_BUDGET
from database import (
    is_processed, mark_processed, clear_cache, get_stats, init_db,
    save_post, get_recent_posts, get_today_api_calls, increment_api_calls,
)
from feeds import fetch_news, fetch_og_image
from agents import generate_post
from api_football import fetch_standings, fetch_matches_by_date
from webapp import HTML_PAGE

log = logging.getLogger(__name__)

# Bir vaqtda faqat bitta auto_news_post() ishlashi uchun
_news_lock = threading.Lock()

# YANGI: Pipeline'da 3 ta agent (Researcher+Writer+Editor) ishlaydi,
# demak har bir post urinishi taxminan 3 ta Gemini API chaqiruvini
# sarflaydi. Shu asosda kunlik xavfsiz limit hisoblanadi.
CALLS_PER_POST = 3
DAILY_API_LIMIT = DAILY_POST_BUDGET * CALLS_PER_POST


# ── Telegram yordamchi ────────────────────────────────────
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


def tg_channel(text: str, image_url: str | None = None) -> dict:
    """
    Kanalga yuborish:
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


# ── Admin tekshiruvi ──────────────────────────────────────
def is_admin(chat_id: int) -> bool:
    if not ADMIN_IDS:
        return True
    return chat_id in ADMIN_IDS


# ── YANGI: Kunlik API byudjetini tekshirish ───────────────
def _quota_available() -> tuple[bool, int, int]:
    """(mavjudmi, ishlatilgan, limit) qaytaradi."""
    used = get_today_api_calls()
    return used < DAILY_API_LIMIT, used, DAILY_API_LIMIT


# ── Auto yangilik yuborish ────────────────────────────────
def auto_news_post() -> bool:
    if not _news_lock.acquire(blocking=False):
        log.info('[Auto] Boshqa jarayon allaqachon ishlayapti, o\'tkazib yuborildi.')
        return False

    try:
        ok, used, limit = _quota_available()
        if not ok:
            log.info(f'[Auto] Kunlik API byudjeti tugagan ({used}/{limit}). O\'tkazib yuborildi.')
            return False

        log.info('[Auto] Yangilik qidirilmoqda...')
        articles = fetch_news()
        if not articles:
            log.info('[Auto] Yangilik topilmadi.')
            return False

        for article in articles:
            if is_processed(article['url']):
                continue

            ok, used, limit = _quota_available()
            if not ok:
                log.info(f'[Auto] Kunlik API byudjeti tugadi ({used}/{limit}). To\'xtatildi.')
                return False

            log.info(f'[Auto] Qayta ishlanmoqda (score:{article["score"]}): {article["title"][:60]}')
            try:
                post = generate_post(article)
                increment_api_calls(CALLS_PER_POST)
            except Exception as e:
                increment_api_calls(CALLS_PER_POST)
                err = str(e)
                is_quota = '429' in err or 'RESOURCE_EXHAUSTED' in err
                if is_quota:
                    log.error('[Auto] Gemini kvotasi tugadi. To\'xtatildi.')
                    notify_admins('⚠️ Gemini API kvotasi tugadi. Ertaga (Pacific vaqti bo\'yicha) avtomatik tiklanadi.')
                    return False
                log.error(f'[Auto] AI xato: {e}')
                mark_processed(article['url'], article['title'], article['score'])
                continue

            if not post or len(post.strip()) < 50:
                mark_processed(article['url'], article['title'], article['score'])
                continue

            image_url = fetch_og_image(article['url']) if article.get('url') else None
            log.info(f'[Auto] Rasm: {image_url[:60] if image_url else "yoq"}')

            result = tg_channel(post, image_url=image_url)
            if result.get('ok'):
                mark_processed(article['url'], article['title'], article['score'])
                save_post(article['url'], article['title'], post, image_url)
                log.info(f'[Auto] ✅ Yuborildi: {article["title"][:60]}')
                return True
            else:
                log.error(f'[Auto] TG xato: {result.get("description")}')

        log.info('[Auto] Barcha yangiliklar allaqachon qayta ishlangan.')
        return False
    finally:
        _news_lock.release()


# ── Foydalanuvchi holati ──────────────────────────────────
pending: dict[int, dict] = {}


# ── Update handler ────────────────────────────────────────
def handle_update(update: dict) -> None:
    msg = update.get('message')
    if not msg:
        return

    chat = msg.get('chat') or {}
    chat_id = chat.get('id')
    if chat_id is None:
        return

    text: str = (msg.get('text') or '').strip()

    try:
        if text == '/whoami':
            tg_send(chat_id, f'Sizning chat_id: {chat_id}\nADMIN_IDS: {ADMIN_IDS}')
            return

        if text.startswith('/') and not is_admin(chat_id):
            tg_send(chat_id, f'⛔ Siz admin emassiz. (chat_id: {chat_id})')
            return

        if text == '/start':
            tg_send(chat_id,
                'Ingliz Futboli Bot v4.0\n\n'
                '3 agent: Researcher + Writer + Editor\n\n'
                'Matn yuboring — professional post\n'
                '/yangilik — RSS dan yangi xabar olish\n'
                '/stat — Statistika\n'
                '/clearcache — Keshni tozalash\n'
                '/help — Yordam'
            )

        elif text == '/help':
            tg_send(chat_id,
                'Qo\'llanma:\n\n'
                '• Har qanday matn yuboring → AI post yaratadi → tasdiqlang\n'
                '• /yangilik → RSS lentadan eng dolzarb yangilik\n'
                '• /stat → Nechta yangilik qayta ishlangani\n'
                '• /clearcache → Keshni tozalab /yangilik yuboring\n\n'
                f'Admin IDlar: {ADMIN_IDS}'
            )

        elif text == '/yangilik':
            if not is_admin(chat_id):
                tg_send(chat_id, '⛔ Faqat adminlar uchun.')
                return
            ok_quota, used, limit = _quota_available()
            if not ok_quota:
                tg_send(chat_id, f'⛔ Bugungi API byudjeti tugadi ({used}/{limit}). Ertaga (Pacific vaqti bo\'yicha) tiklanadi.')
                return
            tg_send(chat_id, '⏳ Yangilik olinayapti (3 agent ishlaydi)...')
            ok = auto_news_post()
            tg_send(chat_id, '✅ Post yuborildi!' if ok else '❌ Yangi yangilik topilmadi (yoki kvota tugagan).')

        elif text == '/stat':
            cnt, avg = get_stats()
            used, limit = get_today_api_calls(), DAILY_API_LIMIT
            tg_send(chat_id, f'📊 Bazada: {cnt} ta yangilik\nO\'rtacha ball: {avg}\n\n🔋 Bugungi API: {used}/{limit}')

        elif text == '/clearcache':
            if not is_admin(chat_id):
                tg_send(chat_id, '⛔ Faqat adminlar uchun.')
                return
            clear_cache()
            tg_send(chat_id, '✅ Kesh tozalandi! /yangilik yuboring.')

        elif text == 'Yuborish' and chat_id in pending:
            p = pending.pop(chat_id)
            result = tg_channel(p['text'], image_url=p.get('image_url'))
            if result.get('ok'):
                save_post(None, p['text'][:80], p['text'], p.get('image_url'))
            tg_send(chat_id, '✅ Kanalga yuborildi!',
                    reply_markup={'remove_keyboard': True})

        elif text == 'Bekor' and chat_id in pending:
            pending.pop(chat_id)
            tg_send(chat_id, '❌ Bekor qilindi.',
                    reply_markup={'remove_keyboard': True})

        elif text and not text.startswith('/'):
            if not is_admin(chat_id):
                return
            ok_quota, used, limit = _quota_available()
            if not ok_quota:
                tg_send(chat_id, f'⛔ Bugungi API byudjeti tugadi ({used}/{limit}). Ertaga (Pacific vaqti bo\'yicha) tiklanadi.')
                return
            tg_send(chat_id, '⏳ 3 agent ishlayapti...')
            try:
                article = {'title': text, 'description': '', 'url': None, 'score': 100}
                post = generate_post(article)
                increment_api_calls(CALLS_PER_POST)
                pending[chat_id] = {'text': post, 'image_url': None}
                tg_send(chat_id, f'Ko\'rib chiqing:\n\n{post}')
                tg_send(chat_id, 'Tasdiqlang:',
                        reply_markup={
                            'keyboard': [['Yuborish'], ['Bekor']],
                            'resize_keyboard': True,
                            'one_time_keyboard': True,
                        })
            except Exception as e:
                increment_api_calls(CALLS_PER_POST)
                log.error(f'[Bot] Post yaratish xatosi: {e}')
                tg_send(chat_id, f'❌ Xatolik: {e}')

    except Exception as e:
        log.error(f'[Bot] handle_update kutilmagan xato: {e}')


# ── Webhook + Mini App HTTP handler ───────────────────────
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Har bir so'rovni alohida thread'da qayta ishlaydi — Mini App va
    Telegram webhook so'rovlari bir-birini bloklamasligi uchun."""
    daemon_threads = True
class WebhookHandler(BaseHTTPRequestHandler):
    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data, default=str, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        incoming_secret = self.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not hmac.compare_digest(incoming_secret, WEBHOOK_SECRET):
            log.warning('[Webhook] Noto\'g\'ri yoki yo\'q secret token — so\'rov rad etildi.')
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
        try:
            update = json.loads(body)
            threading.Thread(target=handle_update, args=(update,), daemon=True).start()
        except Exception as e:
            log.error(f'[Webhook] {e}')

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/posts':
            try:
                posts = get_recent_posts(50)
                self._json(posts)
            except Exception as e:
                log.error(f'[API] /api/posts xato: {e}')
                self._json([], status=500)
            return

        if path == '/api/standings':
            try:
                rows = fetch_standings()
                self._json(rows)
            except Exception as e:
                log.error(f'[API] /api/standings xato: {e}')
                self._json(None, status=500)
            return

        if path == '/api/matches':
            qs = parse_qs(parsed.query)
            date_str = (qs.get('date') or [''])[0]
            if not date_str:
                self._json({'error': 'date kerak (YYYY-MM-DD)'}, status=400)
                return
            try:
                matches = fetch_matches_by_date(date_str)
                self._json(matches)
            except Exception as e:
                log.error(f'[API] /api/matches xato: {e}')
                self._json(None, status=500)
            return

        if path in ('/', '/webapp', '/webapp/'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Ingliz Futboli Bot v4.0')

    def log_message(self, *args):
        pass


# ── Background news loop ──────────────────────────────────
def news_loop() -> None:
    time.sleep(10)
    while True:
        try:
            auto_news_post()
        except Exception as e:
            log.error(f'[Loop] {e}')
        time.sleep(INTERVAL)


# ── Entry point ───────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    log.info(f'[Server] Port {PORT} da ishga tushdi | Admin IDlar: {ADMIN_IDS} | Kunlik API byudjeti: {DAILY_API_LIMIT}')
    threading.Thread(target=news_loop, daemon=True).start()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Bot to\'xtatildi.')
