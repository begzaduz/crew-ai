import json
import time
import hmac
import base64
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

from config import (
    ADMIN_IDS, PORT, INTERVAL, WEBHOOK_SECRET, DAILY_POST_BUDGET,
    DASHBOARD_USER, DASHBOARD_PASSWORD, BOT_ENABLED, MINI_APP_ENABLED,
)
import database
from database import (
    is_processed, mark_processed, clear_cache, get_stats, init_db,
    get_recent_posts, get_today_api_calls, increment_api_calls,
)
from feeds import fetch_news, fetch_article_image, DEFAULT_RSS_FEEDS
from workflows.rss_news import (
    generate_post, DEFAULT_TERMINOLOGY, DEFAULT_NICKNAMES,
    DEFAULT_CHANNEL_TAG, DEFAULT_TONE, DEFAULT_DOMAIN_DESCRIPTION,
    DEFAULT_CONTENT_TYPES, DEFAULT_JARGON, DEFAULT_EMOJI_LEGEND,
)
from api_football import fetch_standings, fetch_matches_by_date
from webapp import HTML_PAGE
from studio_ui import STUDIO_HTML
from telegram_utils import tg_send, notify_admins
import studio_api

log = logging.getLogger(__name__)

# Bir vaqtda faqat bitta auto_news_post() ishlashi uchun
_news_lock = threading.Lock()

# Pipeline'da 3 ta agent (Researcher+Writer+Editor) ishlaydi,
# demak har bir post urinishi taxminan 3 ta Gemini API chaqiruvini
# sarflaydi. Shu asosda kunlik xavfsiz limit hisoblanadi.
CALLS_PER_POST = 3
DAILY_API_LIMIT = DAILY_POST_BUDGET * CALLS_PER_POST

# "Ingliz Futboli" loyihasining DB dagi identifikatori. Server ishga
# tushganda _bootstrap_project() orqali to'ldiriladi (project mavjud
# bo'lmasa yaratiladi, mavjud bo'lsa faqat id olinadi).
PROJECT_SLUG = 'ingliz-futboli'
PROJECT_ID: int | None = None


def _bootstrap_project() -> int:
    """'Ingliz Futboli' loyihasini DB'da tayyorlaydi: project + workflow
    config (terminologiya/taxalluslar/kanal/uslub/soha/turlar/atamalar/
    emoji) + data_sources (RSS manbalar). Loyiha allaqachon mavjud bo'lsa,
    hech narsa qayta yozilmaydi — Dashboard'dan kiritilgan o'zgarishlar
    saqlanib qoladi."""
    project = database.seed_project_if_empty(
        slug=PROJECT_SLUG,
        name='Ingliz Futboli',
        default_config={
            'terminology': DEFAULT_TERMINOLOGY,
            'nicknames': DEFAULT_NICKNAMES,
            'channel_tag': DEFAULT_CHANNEL_TAG,
            'tone': DEFAULT_TONE,
            'domain_description': DEFAULT_DOMAIN_DESCRIPTION,
            'content_types': DEFAULT_CONTENT_TYPES,
            'jargon': DEFAULT_JARGON,
            'emoji_legend': DEFAULT_EMOJI_LEGEND,
        },
        default_sources=DEFAULT_RSS_FEEDS,
    )
    pid = project['id']

    # KO'CHIRISH (bir martalik): loyiha bugungacha allaqachon mavjud
    # bo'lgani uchun yuqoridagi seed_project_if_empty hech narsa
    # yozmagan bo'lishi mumkin (config allaqachon to'ldirilgan edi).
    # Universallashtirish bilan qo'shilgan YANGI maydonlar
    # (domain_description/content_types/jargon/emoji_legend) esa eski
    # config'da yo'q — ularni ALOHIDA, faqat YETISHMASA qo'shamiz
    # (mavjud qiymatlarga tegmasdan).
    current = database.get_workflow_config(pid)
    missing_patch = {}
    if 'domain_description' not in current:
        missing_patch['domain_description'] = DEFAULT_DOMAIN_DESCRIPTION
    if 'content_types' not in current:
        missing_patch['content_types'] = DEFAULT_CONTENT_TYPES
    if 'jargon' not in current:
        missing_patch['jargon'] = DEFAULT_JARGON
    if 'emoji_legend' not in current:
        missing_patch['emoji_legend'] = DEFAULT_EMOJI_LEGEND
    if missing_patch:
        database.update_workflow_config(pid, missing_patch)
        log.info(f"[Bootstrap] Yangi konfiguratsiya maydonlari qo'shildi: {list(missing_patch.keys())}")

    return pid


# ── Studio Lab Dashboard autentifikatsiyasi (Basic Auth) ──
# /studio sahifasi va /api/studio/* barcha endpointlari shu bilan
# himoyalanadi. Brauzer 'Authorization: Basic ...' headerini avtomatik
# yuboradi (login/parol so'ragan standart oyna orqali) — alohida login
# sahifa yoki sessiya/cookie kodi kerak emas.
def _check_dashboard_auth(headers) -> bool:
    auth_header = headers.get('Authorization', '')
    if not auth_header.startswith('Basic '):
        return False
    try:
        decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
        user, _, pwd = decoded.partition(':')
    except Exception:
        return False
    return hmac.compare_digest(user, DASHBOARD_USER) and hmac.compare_digest(pwd, DASHBOARD_PASSWORD)


def _resolve_project_id(source: dict) -> int:
    """So'rovdan (query yoki JSON body) 'project_id'ni oladi — Dashboard'da
    loyiha almashtirilganda shu orqali qaysi loyiha bilan ishlash
    aniqlanadi. Berilmagan/noto'g'ri bo'lsa, bootstrap qilingan asosiy
    loyihaga (Ingliz Futboli) qaytadi — eski so'rovlar bilan orqaga
    moslik uchun."""
    raw = source.get('project_id')
    if raw:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    return PROJECT_ID


# ── Admin tekshiruvi ──────────────────────────────────────
def is_admin(chat_id: int) -> bool:
    if not ADMIN_IDS:
        return True
    return chat_id in ADMIN_IDS


# ── Kunlik API byudjetini tekshirish ──────────────────────
def _quota_available(project_id: int) -> tuple[bool, int, int]:
    """(mavjudmi, ishlatilgan, limit) qaytaradi — HAR LOYIHA UCHUN ALOHIDA
    (Superside'dagi har mijozga alohida byudjet tamoyiliga mos)."""
    used = get_today_api_calls(project_id)
    return used < DAILY_API_LIMIT, used, DAILY_API_LIMIT


# ── Auto yangilik yuborish ────────────────────────────────
def auto_news_post(project_id: int) -> bool:
    """Berilgan loyiha uchun RSS manbalardan yangilik qidiradi va Review
    Queue'ga qo'shadi. Kvota va manbalar shu loyihaga xos."""
    if not _news_lock.acquire(blocking=False):
        log.info('[Auto] Boshqa jarayon allaqachon ishlayapti, o\'tkazib yuborildi.')
        return False

    try:
        ok, used, limit = _quota_available(project_id)
        if not ok:
            log.info(f'[Auto] (loyiha={project_id}) Kunlik API byudjeti tugagan ({used}/{limit}). O\'tkazib yuborildi.')
            return False

        # RSS manbalar endi kod ichidan emas, DB'dagi data_sources
        # jadvalidan olinadi — Dashboard'da qo'shilgan/o'chirilgan
        # manba shu yerda darhol amalda qo'llaniladi.
        sources = database.get_data_sources(project_id, active_only=True)
        urls = [s['url'] for s in sources]
        if not urls:
            log.info(f'[Auto] (loyiha={project_id}) Faol RSS manbalar yo\'q. O\'tkazib yuborildi.')
            return False

        log.info(f'[Auto] (loyiha={project_id}) Yangilik qidirilmoqda ({len(urls)} ta manbadan)...')
        articles = fetch_news(urls)
        if not articles:
            log.info(f'[Auto] (loyiha={project_id}) Yangilik topilmadi.')
            return False

        for article in articles:
            if is_processed(article['url']):
                continue

            ok, used, limit = _quota_available(project_id)
            if not ok:
                log.info(f'[Auto] (loyiha={project_id}) Kunlik API byudjeti tugadi ({used}/{limit}). To\'xtatildi.')
                return False

            log.info(f'[Auto] (loyiha={project_id}) Qayta ishlanmoqda (score:{article["score"]}): {article["title"][:60]}')
            try:
                post = generate_post(article, project_id)
                increment_api_calls(project_id, CALLS_PER_POST)
            except Exception as e:
                increment_api_calls(project_id, CALLS_PER_POST)
                err = str(e)
                is_quota = '429' in err or 'RESOURCE_EXHAUSTED' in err
                if is_quota:
                    log.error(f'[Auto] (loyiha={project_id}) Gemini kvotasi tugadi. To\'xtatildi.')
                    notify_admins(f'⚠️ Gemini API kvotasi tugadi (loyiha={project_id}). Ertaga (Pacific vaqti bo\'yicha) avtomatik tiklanadi.')
                    return False
                log.error(f'[Auto] (loyiha={project_id}) AI xato: {e}')
                mark_processed(article['url'], article['title'], article['score'])
                continue

            if not post or len(post.strip()) < 50:
                mark_processed(article['url'], article['title'], article['score'])
                continue

            image_url = fetch_article_image(article['url']) if article.get('url') else None
            log.info(f'[Auto] Rasm: {image_url[:60] if image_url else "yoq"}')

            # Post 'assets' jadvaliga status='draft' bilan yoziladi —
            # Dashboard'dagi Review Queue'da admin uni ko'radi, kerak
            # bo'lsa tahrirlaydi, va faqat TASDIQLAGANDAN keyin (darhol
            # yoki publish_interval_minutes navbati orqali) kanalga
            # jo'naydi.
            asset = database.create_asset(
                project_id=project_id,
                source_url=article['url'],
                asset_type='rss_news',
                title=article['title'],
                content=post,
                score=article['score'],
                image_url=image_url,
            )
            mark_processed(article['url'], article['title'], article['score'])
            log.info(f'[Auto] (loyiha={project_id}) ✅ Review Queue-ga qo\'shildi: {article["title"][:60]}')
            return True

        log.info(f'[Auto] (loyiha={project_id}) Barcha yangiliklar allaqachon qayta ishlangan.')
        return False
    finally:
        _news_lock.release()


# ── Update handler ────────────────────────────────────────
def handle_update(update: dict) -> None:
    # Ingliz Futboli boti vaqtincha o'chirilgan bo'lishi mumkin
    # (config.BOT_ENABLED — Railway env orqali boshqariladi). Bu holatda
    # webhook so'rovi baribir 200 bilan qabul qilinadi (main.py'dagi
    # do_POST), lekin hech qanday buyruqqa javob berilmaydi/hech narsa
    # yaratilmaydi — Dashboard va boshqa loyihalarga ta'sir qilmaydi.
    if not BOT_ENABLED:
        return

    msg = update.get('message')
    if not msg:
        return

    chat = msg.get('chat') or {}
    chat_id = chat.get('id')
    if chat_id is None:
        return

    text: str = (msg.get('text') or '').strip()

    # MUHIM: bot buyruqlari endi BITTA global loyihaga (PROJECT_ID)
    # qattiq bog'lanmagan — qaysi loyiha bilan ishlash kerakligi shu
    # chat_id'ning Dashboard'da (workflows.config -> telegram_admin_
    # chat_id) qaysi loyihaga bog'langaniga qarab DB'dan aniqlanadi.
    # Hech qanday loyiha bu chatga bog'lanmagan bo'lsa (masalan hali
    # sozlanmagan, yoki eski/yagona-loyiha o'rnatish), orqaga moslik
    # uchun bootstrap qilingan asosiy loyihaga (PROJECT_ID) qaytiladi —
    # bu "Ingliz Futboli" hech narsa qo'shimcha sozlamasdan ishlashda
    # davom etishini kafolatlaydi.
    project_id = database.get_project_id_by_telegram_admin_chat_id(chat_id) or PROJECT_ID

    try:
        if text == '/whoami':
            tg_send(chat_id, f'Sizning chat_id: {chat_id}')
            return

        if text.startswith('/') and not is_admin(chat_id):
            tg_send(chat_id, f'⛔ Siz admin emassiz. (chat_id: {chat_id})')
            return

        if text == '/start':
            tg_send(chat_id,
                'Studio Lab Bot v5.0\n\n'
                '3 agent: Researcher + Writer + Editor\n'
                '(terminologiya, taxalluslar va manbalar Dashboard orqali boshqariladi)\n\n'
                'MUHIM: Bot endi kanalga hech narsani to\'g\'ridan-to\'g\'ri '
                'yubormaydi. Har qanday matn yoki /yangilik natijasi avval '
                'Review Queue\'ga (Dashboard) qo\'shiladi — tasdiqlash va '
                'kanalga yuborish FAQAT Dashboard\'da bo\'ladi.\n\n'
                'Matn yuboring — tarjima/formatlab Review Queue-ga qo\'shadi\n'
                '/yangilik — RSS dan yangi xabar olib Review Queue-ga qo\'shadi\n'
                '/stat — Statistika\n'
                '/clearcache — Keshni tozalash\n'
                '/help — Yordam'
            )

        elif text == '/help':
            tg_send(chat_id,
                'Qo\'llanma:\n\n'
                '• Har qanday matn yuboring → AI tarjima/formatlab Review Queue-ga qo\'shadi\n'
                '• /yangilik → RSS lentadan eng dolzarb yangilikni Review Queue-ga qo\'shadi\n'
                '• /stat → Nechta yangilik qayta ishlangani\n'
                '• /clearcache → Keshni tozalab /yangilik yuboring\n'
                '• Tasdiqlash va kanalga yuborish → Dashboard (/studio)\n\n'
                f'Admin IDlar: {ADMIN_IDS}'
            )

        elif text == '/yangilik':
            if not is_admin(chat_id):
                tg_send(chat_id, '⛔ Faqat adminlar uchun.')
                return
            ok_quota, used, limit = _quota_available(project_id)
            if not ok_quota:
                tg_send(chat_id, f'⛔ Bugungi API byudjeti tugadi ({used}/{limit}). Ertaga (Pacific vaqti bo\'yicha) tiklanadi.')
                return
            tg_send(chat_id, '⏳ Yangilik olinayapti (3 agent ishlaydi)...')
            ok = auto_news_post(project_id)
            tg_send(chat_id, '✅ Review Queue-ga qo\'shildi! Tasdiqlash uchun Dashboard: /studio' if ok
                    else '❌ Yangi yangilik topilmadi (yoki kvota tugagan).')

        elif text == '/stat':
            cnt, avg = get_stats()
            used, limit = get_today_api_calls(project_id), DAILY_API_LIMIT
            tg_send(chat_id, f'📊 Bazada: {cnt} ta yangilik\nO\'rtacha ball: {avg}\n\n🔋 Bugungi API: {used}/{limit}')

        elif text == '/clearcache':
            if not is_admin(chat_id):
                tg_send(chat_id, '⛔ Faqat adminlar uchun.')
                return
            clear_cache()
            tg_send(chat_id, '✅ Kesh tozalandi! /yangilik yuboring.')

        elif text and not text.startswith('/'):
            if not is_admin(chat_id):
                return
            ok_quota, used, limit = _quota_available(project_id)
            if not ok_quota:
                tg_send(chat_id, f'⛔ Bugungi API byudjeti tugadi ({used}/{limit}). Ertaga (Pacific vaqti bo\'yicha) tiklanadi.')
                return
            tg_send(chat_id, '⏳ 3 agent ishlayapti (tarjima + formatlash)...')
            # MUHIM: increment_api_calls() FAQAT BITTA marta chaqiriladi —
            # generate_post() muvaffaqiyatli tugagach. Avval bu bitta try/except
            # ichida edi va agar generate_post() muvaffaqiyatli tugab, keyin
            # create_asset() (masalan DB xatosi) muvaffaqiyatsiz bo'lsa, kvota
            # IKKI marta oshirilardi (bitta haqiqiy Gemini chaqiruvi uchun).
            try:
                # Matn boshqa tilda bo'lishi ham mumkin — pipeline avtomatik
                # o'zbek tiliga tarjima qilib, kanalga mos formatga soladi.
                article = {'title': text, 'description': '', 'url': None, 'score': 100}
                post = generate_post(article, project_id)
            except Exception as e:
                increment_api_calls(project_id, CALLS_PER_POST)
                log.error(f'[Bot] Post yaratish xatosi (generate_post): {e}')
                tg_send(chat_id, f'❌ Xatolik: {e}')
                return

            increment_api_calls(project_id, CALLS_PER_POST)

            try:
                # MUHIM: bu yerda kanalga to'g'ridan-to'g'ri yubormaymiz —
                # Review Queue'ga qo'shamiz, faqat Dashboard'da tasdiqlangandan
                # keyin kanalga ketadi.
                asset = database.create_asset(
                    project_id=project_id, source_url=None, asset_type='manual',
                    title=text[:80], content=post, score=100, image_url=None,
                )
            except Exception as e:
                log.error(f'[Bot] Post yaratish xatosi (create_asset): {e}')
                tg_send(chat_id, f'❌ Xatolik: {e}')
                return

            tg_send(chat_id, f'✅ Review Queue-ga qo\'shildi. Tasdiqlash uchun Dashboard: /studio\n\n{post}')

    except Exception as e:
        log.error(f'[Bot] handle_update kutilmagan xato: {e}')


# ── Webhook + Mini App + Studio Dashboard HTTP handler ────
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Har bir so'rovni alohida thread'da qayta ishlaydi — Mini App, Studio
    Dashboard va Telegram webhook so'rovlari bir-birini bloklamasligi uchun."""
    daemon_threads = True
class WebhookHandler(BaseHTTPRequestHandler):
    # Autentifikatsiyasiz so'rovchi juda katta body yuborib serverni
    # xotira bilan band qilishi (DoS) mumkin edi — endi Content-Length
    # shu chegaradan oshsa, body o'qilmasdan darhol 413 qaytariladi.
    # 2 MB — eng katta legitim so'rov (masalan uzun custom prompt yoki
    # Telegram webhook update)dan ancha katta, shuning uchun haqiqiy
    # foydalanishga xalaqit bermaydi.
    MAX_BODY_SIZE = 2_000_000

    # Rasm yuklash (base64) — dekodlanmagan JSON payload ~33% kattaroq
    # bo'ladi, shuning uchun oddiy limitdan yuqoriroq kerak. Faqat shu
    # bitta route uchun (auth baribir avval tekshiriladi, DoS xavfi yo'q).
    IMAGE_UPLOAD_MAX_BODY_SIZE = 20_000_000

    def _json(self, data, status: int = 200, cors: bool = False) -> None:
        body = json.dumps(data, default=str, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        # MUHIM: CORS faqat chindan ham tashqi/kross-origin foydalanish
        # kerak bo'lgan PUBLIC endpointlarga (mini-app: /api/posts,
        # /api/matches, /api/standings) yoqiladi. Autentifikatsiya talab
        # qiladigan /api/studio/* endpointlariga bu sarlavha keraksiz —
        # Dashboard JS bir xil origin'dan ishlaydi, va CORS'ni yoqish
        # faqat keraksiz hujum yuzasini kengaytiradi.
        if cors:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(body)

    def _read_body_or_413(self, max_size: int | None = None) -> bytes | None:
        """Content-Length'ni max_size (berilmasa MAX_BODY_SIZE) bilan
        solishtiradi va faqat chegaradan oshmasa body'ni o'qib qaytaradi.
        Oshsa, body UMUMAN o'qilmaydi (xotira band qilinmaydi) va 413
        qaytariladi — chaqiruvchi None qaytgan holatda darhol return
        qilishi kerak."""
        limit = max_size if max_size is not None else self.MAX_BODY_SIZE
        length = int(self.headers.get('Content-Length', 0))
        if length > limit:
            self._json({'error': f'Fayl juda katta (max {limit // 1_000_000}MB)'}, status=413)
            return None
        return self.rfile.read(length)

    def _deny_dashboard_auth(self) -> None:
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Studio Lab Dashboard"')
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'Unauthorized')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ── Studio Dashboard API (manba qo'shish, terminologiya saqlash) ──
        if path in studio_api.POST_ROUTES:
            # MUHIM: auth headerlar orqali tekshiriladi (body kerak emas)
            # — shuning uchun avval shu tekshiriladi. Bo'lmasa,
            # autentifikatsiyasiz so'rovchi katta body yubortirib serverni
            # (hali auth rad etilishidan OLDIN) xotira bilan band qilishi
            # mumkin edi.
            if not _check_dashboard_auth(self.headers):
                self._deny_dashboard_auth()
                return
            body_limit = self.IMAGE_UPLOAD_MAX_BODY_SIZE if path == '/api/studio/images/upload' else None
            body = self._read_body_or_413(body_limit)
            if body is None:
                return
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {}
            if path == '/api/studio/images/upload':
                # PUBLIC_BASE_URL .env'da sozlanishi ixtiyoriy (fallback) —
                # odatiy holatda so'rovning o'zidan (Host/X-Forwarded-Proto
                # headerlari) ochiq manzilni avtomatik aniqlaymiz, shunda
                # admin qo'shimcha sozlash haqida umuman o'ylashi shart emas.
                host = self.headers.get('Host', '')
                if host:
                    scheme = self.headers.get('X-Forwarded-Proto', 'https')
                    data['_request_base_url'] = f'{scheme}://{host}'
            try:
                status, payload = studio_api.POST_ROUTES[path](_resolve_project_id(data), data)
            except Exception as e:
                log.error(f'[StudioAPI] {path}: {e}')
                status, payload = 500, {'error': str(e)}
            self._json(payload, status=status)
            return

        # ── Telegram webhook ──────────────────────────────────────────
        incoming_secret = self.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not hmac.compare_digest(incoming_secret, WEBHOOK_SECRET):
            log.warning('[Webhook] Noto\'g\'ri yoki yo\'q secret token — so\'rov rad etildi.')
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return

        body = self._read_body_or_413()
        if body is None:
            return
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

        # ── Dashboard'dan yuklangan rasmlar (ochiq, autentifikatsiyasiz —
        # Telegram va Mini App ham shu URL'ga ulanishi kerak, ular
        # Basic Auth header yubormaydi) ──────────────────────────────
        if path.startswith('/api/image/'):
            id_part = path[len('/api/image/'):]
            if not id_part.isdigit():
                self.send_response(404)
                self.end_headers()
                return
            upload = database.get_upload(int(id_part))
            if not upload:
                self.send_response(404)
                self.end_headers()
                return
            data = bytes(upload['data'])
            self.send_response(200)
            self.send_header('Content-Type', upload['content_type'])
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
            self.end_headers()
            self.wfile.write(data)
            return

        # ── Studio Dashboard API (o'qish) ──────────────────────────────
        if path in studio_api.GET_ROUTES:
            if not _check_dashboard_auth(self.headers):
                self._deny_dashboard_auth()
                return
            qs = parse_qs(parsed.query)
            query = {k: v[0] for k, v in qs.items()}
            try:
                status, payload = studio_api.GET_ROUTES[path](_resolve_project_id(query), query)
            except Exception as e:
                log.error(f'[StudioAPI] {path}: {e}')
                status, payload = 500, {'error': str(e)}
            self._json(payload, status=status)
            return

        # ── Studio Dashboard sahifasi ───────────────────────────────────
        if path in ('/studio', '/studio/', '/dashboard'):
            if not _check_dashboard_auth(self.headers):
                self._deny_dashboard_auth()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            # Dashboard tez-tez o'zgaradi (har deploy'da) — brauzer yoki
            # mobil operator proksisi eskirgan nusxani ko'rsatib qolishi
            # mumkin edi. Bu buni butunlay taqiqlaydi.
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()
            self.wfile.write(STUDIO_HTML.encode('utf-8'))
            return

        if path == '/api/posts':
            if not MINI_APP_ENABLED:
                self._json({'error': 'Mini App vaqtincha ishlamayapti'}, status=503, cors=True)
                return
            qs = parse_qs(parsed.query)
            pid = _resolve_project_id({k: v[0] for k, v in qs.items()})
            try:
                posts = get_recent_posts(pid, 50)
                self._json(posts, cors=True)
            except Exception as e:
                log.error(f'[API] /api/posts xato: {e}')
                self._json([], status=500, cors=True)
            return

        if path == '/api/standings':
            if not MINI_APP_ENABLED:
                self._json({'error': 'Mini App vaqtincha ishlamayapti'}, status=503, cors=True)
                return
            try:
                rows = fetch_standings()
                self._json(rows, cors=True)
            except Exception as e:
                log.error(f'[API] /api/standings xato: {e}')
                self._json(None, status=500, cors=True)
            return

        if path == '/api/matches':
            if not MINI_APP_ENABLED:
                self._json({'error': 'Mini App vaqtincha ishlamayapti'}, status=503, cors=True)
                return
            qs = parse_qs(parsed.query)
            date_str = (qs.get('date') or [''])[0]
            if not date_str:
                self._json({'error': 'date kerak (YYYY-MM-DD)'}, status=400, cors=True)
                return
            try:
                matches = fetch_matches_by_date(date_str)
                self._json(matches, cors=True)
            except Exception as e:
                log.error(f'[API] /api/matches xato: {e}')
                self._json(None, status=500, cors=True)
            return

        if path in ('/', '/webapp', '/webapp/'):
            if not MINI_APP_ENABLED:
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write('Mini App vaqtincha ishlamayapti. Tez orada qaytadi.'.encode('utf-8'))
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Ingliz Futboli Bot v5.0')

    def log_message(self, *args):
        pass


# ── Background news loop ──────────────────────────────────
def news_loop() -> None:
    """Barcha loyihalarni birma-bir aylanib, har biri uchun RSS
    yangiliklarni tekshiradi. Har loyihaning o'z kvotasi va manbalari
    bo'lgani uchun bittasi ikkinchisiga xalaqit bermaydi."""
    time.sleep(10)
    while True:
        try:
            projects = database.list_projects()
            for project in projects:
                try:
                    auto_news_post(project['id'])
                except Exception as e:
                    log.error(f"[Loop] (loyiha={project['id']}) {e}")
        except Exception as e:
            log.error(f'[Loop] {e}')
        time.sleep(INTERVAL)


# Scheduler necha soniyada bir marta navbatlarni tekshiradi. Bu INTERVAL'dan
# (RSS tsikli, soatlab) ancha qisqaroq bo'lishi kerak — aks holda
# publish_interval_minutes past qiymatga (masalan 5 daq) sozlansa ham,
# post real vaqtda emas, faqat keyingi RSS tsiklida chiqib qolardi.
PUBLISH_SCHEDULER_TICK_SECONDS = 60


def publish_scheduler_loop() -> None:
    """Barcha loyihalarni birma-bir aylanib, har biri uchun navbatda
    (status='scheduled') chiqishni kutayotgan post bor-yo'qligini va
    publish_interval_minutes vaqti o'tganini tekshiradi. Loyihada interval
    sozlanmagan (0) bo'lsa, studio_api.publish_due_scheduled() darhol
    qaytadi — hech narsa qilmaydi (orqaga moslik, eski loyihalarga
    ta'sir qilmaydi)."""
    time.sleep(10)
    while True:
        try:
            projects = database.list_projects()
            for project in projects:
                try:
                    studio_api.publish_due_scheduled(project['id'])
                except Exception as e:
                    log.error(f"[Scheduler] (loyiha={project['id']}) {e}")
        except Exception as e:
            log.error(f'[Scheduler] {e}')
        time.sleep(PUBLISH_SCHEDULER_TICK_SECONDS)


# ── Entry point ───────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    PROJECT_ID = _bootstrap_project()
    # Bir martalik migratsiya: sanitize_telegram_html() generate_post()'ga
    # qo'shilishidan OLDIN yaratilgan draft'larda xom <br> kabi teglar
    # qolib ketgan bo'lishi mumkin edi. Idempotent — hech narsa topilmasa
    # yoki hammasi allaqachon toza bo'lsa, hech narsa o'zgarmaydi.
    try:
        fixed = database.resanitize_draft_assets(PROJECT_ID)
        if fixed:
            log.info(f'[Server] {fixed} ta eski draft xom HTML tegdan tozalandi.')
    except Exception as e:
        log.error(f'[Server] resanitize_draft_assets xato: {e}')
    log.info(
        f'[Server] Port {PORT} da ishga tushdi | Admin IDlar: {ADMIN_IDS} | '
        f'Kunlik API byudjeti: {DAILY_API_LIMIT} | Loyiha ID: {PROJECT_ID} '
        f'| Dashboard: /studio'
    )
    threading.Thread(target=news_loop, daemon=True).start()
    threading.Thread(target=publish_scheduler_loop, daemon=True).start()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Bot to\'xtatildi.')
