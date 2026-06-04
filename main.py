import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import TOKEN, CHANNEL, ADMIN_IDS, PORT, INTERVAL
from database import is_processed, mark_processed, clear_cache, get_stats
from feeds import fetch_news, fetch_og_image
from agents import generate_post

log = logging.getLogger(__name__)


def tg_send(chat_id: int | str, text: str, reply_markup: dict | None = None) -> dict:
    payload: dict = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    res = requests.post(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        json=payload,
        timeout=15,
    )
    return res.json()


def tg_channel(text: str, image_url: str | None = None) -> dict:
    """Kanalga rasm bilan yoki rasmsiz yuboradi."""
    if image_url:
        # Avval sendPhoto bilan urinish
        try:
            res = requests.post(
                f'https://api.telegram.org/bot{TOKEN}/sendPhoto',
                json={
                    'chat_id': CHANNEL,
                    'photo': image_url,
                    'caption': text,
                    'parse_mode': 'Markdown',
                },
                timeout=15,
            )
            result = res.json()
            if result.get('ok'):
                return result
            log.warning(f'[TG] sendPhoto xato: {result.get("description")} — rasmsiz yuborilmoqda')
        except Exception as e:
            log.warning(f'[TG] sendPhoto exception: {e} — rasmsiz yuborilmoqda')

    # Rasmsiz yoki rasm xato bo'lsa — oddiy matn
    res = requests.post(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        json={
            'chat_id': CHANNEL,
            'text': text,
            'parse_mode': 'Markdown',
        },
        timeout=15,
    )
    result = res.json()
    if not result.get('ok') and 'parse' in result.get('description', '').lower():
        log.warning('[TG] Markdown xato — oddiy matn bilan qayta yuborilmoqda')
        res = requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={'chat_id': CHANNEL, 'text': text},
            timeout=15,
        )
        result = res.json()
    return result


def is_admin(chat_id: int) -> bool:
    if not ADMIN_IDS:
        return True
    return chat_id in ADMIN_IDS


def auto_news_post() -> bool:
    log.info('[Auto] Yangilik qidirilmoqda...')
    articles = fetch_news()
    if not articles:
        log.info('[Auto] Yangilik topilmadi.')
        return False

    for article in articles:
        if is_processed(article['url']):
            continue

        log.info(f'[Auto] Qayta ishlanmoqda (score:{article["score"]}): {article["title"][:60]}')
        try:
            post = generate_post(article)
        except Exception as e:
            log.error(f'[Auto] AI xato: {e}')
            mark_processed(article['url'], article['title'], article['score'])
            continue

        if not post or len(post.strip()) < 50:
            mark_processed(article['url'], article['title'], article['score'])
            continue

        # Rasm URL — RSS dan topilmagan bo'lsa og:image dan olishga urinish
        image_url = article.get('image_url')
        if not image_url and article.get('url'):
            log.info('[Auto] RSS da rasm yo\'q — og:image qidirilmoqda...')
            image_url = fetch_og_image(article['url'])

        result = tg_channel(post, image_url)
        if result.get('ok'):
            mark_processed(article['url'], article['title'], article['score'])
            log.info(f'[Auto] ✅ Yuborildi (rasm: {"bor" if image_url else "yo\'q"}): {article["title"][:50]}')
            return True
        else:
            log.error(f'[Auto] TG xato: {result.get("description")}')

    log.info('[Auto] Barcha yangiliklar allaqachon qayta ishlangan.')
    return False


pending: dict[int, dict] = {}


def handle_update(update: dict) -> None:
    msg = update.get('message', {})
    if not msg:
        return

    chat_id: int = msg['chat']['id']
    text: str = msg.get('text', '').strip()

    if text.startswith('/') and not is_admin(chat_id):
        tg_send(chat_id, '⛔ Siz admin emassiz.')
        return

    if text == '/start':
        tg_send(chat_id,
            'Ingliz Futboli Bot v4.1\n\n'
            '3 agent: Researcher + Writer + Editor\n'
            'Rasm: maqola thumbnail avtomatik\n\n'
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
        tg_send(chat_id, '⏳ Yangilik olinayapti (3 agent ishlaydi)...')
        ok = auto_news_post()
        tg_send(chat_id, '✅ Post yuborildi!' if ok else '❌ Yangi yangilik topilmadi.')

    elif text == '/stat':
        cnt, avg = get_stats()
        tg_send(chat_id, f'📊 Bazada: {cnt} ta yangilik\nO\'rtacha ball: {avg}')

    elif text == '/clearcache':
        if not is_admin(chat_id):
            tg_send(chat_id, '⛔ Faqat adminlar uchun.')
            return
        clear_cache()
        tg_send(chat_id, '✅ Kesh tozalandi! /yangilik yuboring.')

    elif text == 'Yuborish' and chat_id in pending:
        tg_channel(pending.pop(chat_id)['text'])
        tg_send(chat_id, '✅ Kanalga yuborildi!',
                reply_markup={'remove_keyboard': True})

    elif text == 'Bekor' and chat_id in pending:
        pending.pop(chat_id)
        tg_send(chat_id, '❌ Bekor qilindi.',
                reply_markup={'remove_keyboard': True})

    elif text and not text.startswith('/'):
        if not is_admin(chat_id):
            return
        tg_send(chat_id, '⏳ 3 agent ishlayapti...')
        try:
            article = {'title': text, 'description': '', 'url': None, 'score': 100, 'image_url': None}
            post = generate_post(article)
            pending[chat_id] = {'text': post}
            tg_send(chat_id, f'Ko\'rib chiqing:\n\n{post}')
            tg_send(chat_id, 'Tasdiqlang:',
                    reply_markup={
                        'keyboard': [['Yuborish'], ['Bekor']],
                        'resize_keyboard': True,
                        'one_time_keyboard': True,
                    })
        except Exception as e:
            log.error(f'[Bot] Post yaratish xatosi: {e}')
            tg_send(chat_id, f'❌ Xatolik: {e}')


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
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
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Ingliz Futboli Bot v4.1')

    def log_message(self, *args):
        pass


def news_loop() -> None:
    time.sleep(10)
    while True:
        try:
            auto_news_post()
        except Exception as e:
            log.error(f'[Loop] {e}')
        time.sleep(INTERVAL)


if __name__ == '__main__':
    log.info(f'[Server] Port {PORT} da ishga tushdi | Admin IDlar: {ADMIN_IDS}')
    threading.Thread(target=news_loop, daemon=True).start()
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Bot to\'xtatildi.')
