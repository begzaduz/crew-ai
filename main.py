import os
import re
import time
import sqlite3
import hashlib
import logging
import threading
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import feedparser
import requests
from markdownify import markdownify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ═══════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════
TOKEN    = os.getenv('TOKEN')
CHANNEL  = os.getenv('CHANNEL', '@Inglizfutbol')
GROQ_KEY = os.getenv('GROQ_KEY')
PORT     = int(os.getenv('PORT', 8080))
INTERVAL = 10 * 60  # 10 daqiqa

if not TOKEN or not GROQ_KEY:
    log.error('TOKEN yoki GROQ_KEY topilmadi!')
    exit(1)

groq_client = Groq(api_key=GROQ_KEY)

# ═══════════════════════════════════════
# SQLITE
# ═══════════════════════════════════════
conn = sqlite3.connect('news_cache.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS processed_articles (
    url          TEXT PRIMARY KEY,
    title        TEXT,
    score        INTEGER DEFAULT 0,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()

db_lock = threading.Lock()

def is_processed(url):
    with db_lock:
        cur = conn.execute('SELECT url FROM processed_articles WHERE url=?', (url,))
        return cur.fetchone() is not None

def mark_processed(url, title='', score=0):
    with db_lock:
        conn.execute(
            'INSERT OR IGNORE INTO processed_articles (url,title,score) VALUES (?,?,?)',
            (url, title, score)
        )
        conn.commit()

def clear_cache():
    with db_lock:
        conn.execute('DELETE FROM processed_articles')
        conn.commit()

def get_stats():
    with db_lock:
        cur = conn.execute('SELECT COUNT(*), AVG(score) FROM processed_articles')
        return cur.fetchone()

# ═══════════════════════════════════════
# RELEVANCE SCORING
# ═══════════════════════════════════════
HIGH_KEYWORDS = [
    'premier league', 'transfer', 'signing', 'manager', 'sacked', 'fired',
    'injured', 'injury', 'goal', 'match', 'result', 'win', 'defeat', 'score',
    'champions league', 'fa cup', 'europa league', 'breaking', 'confirmed', 'official',
    'arsenal', 'chelsea', 'liverpool', 'manchester', 'tottenham', 'newcastle',
    'aston villa', 'west ham', 'brighton', 'everton', 'wolves', 'bournemouth',
    'brentford', 'fulham', 'crystal palace', 'million', 'contract', 'deal', 'fee',
]

LOW_KEYWORDS = [
    'nba', 'nfl', 'cricket', 'rugby', 'golf', 'tennis', 'formula 1', 'nascar',
    'baseball', 'hockey', 'basketball', 'ufc', 'boxing', 'bundesliga',
    'serie a', 'ligue 1', 'la liga', 'mls', 'eredivisie',
]

def score_article(title, desc):
    text = f"{title} {desc}".lower()
    score = 0
    for kw in HIGH_KEYWORDS:
        if kw in text:
            score += 10
    for kw in LOW_KEYWORDS:
        if kw in text:
            score -= 20
    if any(w in text for w in ['breaking', 'official', 'confirmed']):
        score += 15
    return score

# ═══════════════════════════════════════
# O'ZBEK NOMLARI
# ═══════════════════════════════════════
NAMES = {
    'Premier League': 'Premier-liga',
    'Champions League': 'Chempionlar ligasi',
    'FA Cup': 'FA Kubogi',
    'Carabao Cup': 'Karabao Kubogi',
    'Europa League': 'Evropa ligasi',
    'Conference League': 'Konferensiyalar ligasi',
    'Manchester City': 'Manchester Siti',
    'Man City': 'Manchester Siti',
    'Manchester United': 'Manchester Yunayted',
    'Man United': 'Manchester Yunayted',
    'Man Utd': 'Manchester Yunayted',
    'Chelsea': 'Chelsi',
    'Liverpool': 'Liverpul',
    'Tottenham Hotspur': 'Tottenhem Xotspur',
    'Tottenham': 'Tottenhem',
    'Spurs': 'Tottenhem',
    'Newcastle United': 'Nyukasl Yunayted',
    'Newcastle': 'Nyukasl',
    'West Ham United': 'Vest Hem Yunayted',
    'West Ham': 'Vest Hem',
    'Brighton': 'Brayton',
    'Crystal Palace': 'Kristal Pelas',
    'Fulham': 'Fulhem',
    'Bournemouth': 'Bornmut',
    'Nottingham Forest': 'Nottingem Forest',
    'Leicester City': 'Lester Siti',
    'Leicester': 'Lester',
    'Wolverhampton': 'Vulverhempton',
    'Wolves': 'Vulverhempton',
    'Erling Haaland': 'Erling Holland',
    'Haaland': 'Holland',
    'Mohamed Salah': 'Muhammad Saloh',
    'Salah': 'Saloh',
    'Virgil van Dijk': 'Virjil van Deyk',
    'Pep Guardiola': 'Pep Gvardiola',
    'Guardiola': 'Gvardiola',
    'Marcus Rashford': 'Markus Reshford',
    'Rashford': 'Reshford',
}

def apply_names(text):
    if not text:
        return ''
    result = text
    for eng, uzb in sorted(NAMES.items(), key=lambda x: -len(x[0])):
        result = re.sub(rf'\b{re.escape(eng)}\b', uzb, result, flags=re.IGNORECASE)
    return result

# ═══════════════════════════════════════
# RSS FEEDS
# ═══════════════════════════════════════
RSS_FEEDS = [
    'https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml',
    'https://www.skysports.com/rss/12040',
    'https://talksport.com/feed/',
]

def fetch_news():
    seen = set()
    articles = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=6)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get('link', '')
                if not url or url in seen:
                    continue

                # Yangilik yoshi tekshiruv
                published = entry.get('published_parsed')
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue

                title = entry.get('title', '')
                desc  = entry.get('summary', '')
                desc  = re.sub(r'<[^>]+>', ' ', desc).strip()

                score = score_article(title, desc)
                if score >= 20:
                    seen.add(url)
                    articles.append({
                        'url': url,
                        'title': title,
                        'description': desc[:300],
                        'score': score,
                    })
        except Exception as e:
            log.error(f'[RSS] {feed_url}: {e}')

    articles.sort(key=lambda x: x['score'], reverse=True)
    log.info(f'[News] Topildi: {len(articles)} (6 soat ichida, score>=20)')
    return articles

def fetch_article_text(url):
    try:
        res = requests.get(url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
        })
        md = markdownify(res.text, heading_style='ATX', strip=['script', 'style', 'nav', 'footer'])
        return re.sub(r'\n{3,}', '\n\n', md).strip()[:1500]
    except:
        return None

# ═══════════════════════════════════════
# CREWAI AGENTLAR — Groq bilan
# ═══════════════════════════════════════

def groq_call(system_prompt, user_prompt, temperature=0.4, max_tokens=700):
    """Groq API ga so'rov yuborish"""
    response = groq_client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# AGENT 1 — RESEARCHER
RESEARCHER_PROMPT = """You are a Premier League football news analyst. Extract ONLY real facts from the article.

Extract exactly:
1. MAIN: One sentence — who did what (club, player, action, result)
2. STATS: Goals, minutes, assists, table position, points, transfer fee — or NONE
3. QUOTE: Exact quote with speaker name — or NONE
4. CONTEXT: Next match, current table position, record, history — or NONE
5. BREAKING: YES only for: confirmed transfer, manager sacked, season-ending injury, shock result. Otherwise NO

STRICT RULES:
- Only facts from the article. Zero invented content.
- "survival" = "qolish" (staying in league), NOT "quvayt"
- "relegation battle" = "pasayish kurashi"
- "top four" = "to'rtlik"
- "title race" = "chempionlik kurashi"

Respond EXACTLY in this format:
MAIN: [fact]
STATS: [numbers or NONE]
QUOTE: [quote — Name or NONE]
CONTEXT: [context or NONE]
BREAKING: [YES or NO]"""

def researcher_agent(article):
    """Yangilikni tahlil qiladi va faktlarni ajratadi"""
    content = fetch_article_text(article['url']) or ''
    if len(content) < 100:
        content = f"{article['title']}\n{article['description']}"

    user_prompt = f"""Analyze this Premier League news article:

HEADLINE: {article['title']}
CONTENT: {content[:1200]}

Extract key facts."""

    result = groq_call(RESEARCHER_PROMPT, user_prompt, temperature=0.2, max_tokens=300)
    log.info(f'[Researcher] Done: {article["title"][:50]}')
    return result


# AGENT 2 — WRITER
WRITER_PROMPT = """Sen @Inglizfutbol Telegram kanaliga professional o'zbek sport jurnalistisan.

KLUB TAXALLUSLARI — juda kam ishtilsin:
Arsenal = to'pchilar | Liverpool = qizillar | Chelsea = aristokratlar
Man City = fuqarolar | Man Utd = qizil iblislar | Tottenham = xo'rozlar
Newcastle = qarg'alar | Bournemouth = olchalar | West Ham = bolg'achilar
Crystal Palace = burgutlar | Wolves = bo'rilar | Brighton = qaldirg'ochlar
Brentford = arilar | Everton = karamellar | Aston Villa = villalar
Fulham = fulhamliklar | Nottingham Forest = o'rmonchilar

FUTBOL ATAMALAR — to'g'ri o'zbekcha:
- "survival" / "stay up" = "qolish", "ligada qolish"
- "relegation" = "past ligaga tushish"
- "top four" = "to'rtlik"
- "title" = "chempionlik"
- "clean sheet" = "darvozaga o'tkazmaslik"
- "hat-trick" = "het-trik"
- "penalty" = "jarima zarbasi"
- "red card" = "qizil karta"

FORMAT (aniq shu tartibda):
[BREAKING=YES bo'lsa: #BREAKING]
[Emoji] [Sarlavha — maksimal 8 so'z, jozibali]

[Asosiy gap — 1-2 jumla. Eng muhim fakt birinchi. Faol gap.]

[Tafsilot — 2-3 jumla. Raqamlar, statistika, jadval o'rni.]

[🎙 "Iqtibos" — Ismi (faqat mavjud bo'lsa)]

[Xulosa — jadval o'rni yoki keyingi o'yin]

@Inglizfutbol

QOIDALAR:
- Faqat o'zbek tili. Faol gap. Qisqa jumlalar.
- Markdown yo'q (* _ [ ] **)
- O'ylab topilgan fakt yo'q — faqat berilgan faktlar
- 400-600 belgi
- Takrorlanish YO'Q — bir xil fikrni ikki marta aytma
- OXIRIDA doim @Inglizfutbol bo'lishi shart
- Faqat postni yoz, boshqa hech narsa yo'q"""

def writer_agent(article, research_facts):
    """Faktlar asosida o'zbek post yozadi"""
    user_prompt = f"""Write an Uzbek Telegram post using these extracted facts:

HEADLINE: {article['title']}
FACTS:
{research_facts}

Write ONLY the post:"""

    result = groq_call(WRITER_PROMPT, user_prompt, temperature=0.5, max_tokens=600)
    log.info(f'[Writer] Done: {len(result)} chars')
    return result


# AGENT 3 — EDITOR
EDITOR_PROMPT = """Sen qattiq o'zbek sport muharririsan. Postni tekshir:

1. O'zbek tilimi? (rus/ingliz so'z yo'qmi, atamalar to'g'rimi)
2. 400-600 belgi orasidami?
3. Klub taxalluslari ishlatildimi?
4. Markdown belgilari yo'qmi (* _ [ ] **)?
5. O'ylab topilgan fakt yo'qmi?
6. @Inglizfutbol bilan tugadimi?
7. Faol gap ishlatildimi?
8. Takrorlanish yo'qmi?
9. Sarlavha 8 so'zdan oshmaydimi?

Agar HAMMA tekshiruvdan o'tsa: APPROVED yoz
Agar muammo bo'lsa: REJECTED: [sabab] yoz, keyin tuzatilgan versiyani FIXED: dan keyin yoz

MUHIM: @Inglizfutbol yo'q bo'lsa — doim FIXED versiyada qo'sh."""

def editor_agent(post, article_title):
    """Postni tekshiradi va kerak bo'lsa tuzatadi"""
    user_prompt = f"""Review this Uzbek Telegram post about: {article_title}

POST TO REVIEW:
{post}

Check all quality criteria and respond."""

    result = groq_call(EDITOR_PROMPT, user_prompt, temperature=0.2, max_tokens=700)

    if 'APPROVED' in result:
        log.info('[Editor] Approved!')
        return post
    elif 'FIXED:' in result:
        fixed = result.split('FIXED:')[-1].strip()
        log.info('[Editor] Fixed post')
        return fixed
    else:
        log.warning(f'[Editor] Issue: {result[:100]}')
        return post  # Original post qaytaradi


# ═══════════════════════════════════════
# PIPELINE — 3 AGENT ZANJIRI
# ═══════════════════════════════════════
def generate_post(article):
    """3 agent zanjiri: Researcher → Writer → Editor"""
    log.info(f'[Pipeline] Starting: {article["title"][:60]}')

    # 1. Researcher
    facts = researcher_agent(article)

    # 2. Writer
    raw_post = writer_agent(article, facts)

    # 3. Editor
    final_post = editor_agent(raw_post, article['title'])

    # O'zbek nomlari qo'llash
    return apply_names(final_post)


# ═══════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════
def tg_send(chat_id, text):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    res = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=15)
    return res.json()

def tg_send_channel(text):
    return tg_send(CHANNEL, text)


# ═══════════════════════════════════════
# AUTO NEWS POST
# ═══════════════════════════════════════
def auto_news_post():
    log.info(f'[autoPost] Boshlandi: {datetime.now().strftime("%H:%M")}')

    articles = fetch_news()
    if not articles:
        log.info('[autoPost] Yangilik topilmadi.')
        return False

    for article in articles:
        if is_processed(article['url']):
            continue

        log.info(f'[autoPost] Processing (score:{article["score"]}): {article["title"][:60]}')

        try:
            post = generate_post(article)
        except Exception as e:
            log.error(f'[autoPost] AI xato: {e}')
            mark_processed(article['url'], article['title'], article['score'])
            continue

        if not post or len(post.strip()) < 50:
            mark_processed(article['url'], article['title'], article['score'])
            continue

        result = tg_send_channel(post)
        if result.get('ok'):
            mark_processed(article['url'], article['title'], article['score'])
            log.info(f'[autoPost] ✅ Yuborildi: {article["title"][:60]}')
            return True
        else:
            log.error(f'[autoPost] TG xato: {result.get("description")}')

    log.info('[autoPost] Barcha yangiliklar qayta ishlangan.')
    return False


# ═══════════════════════════════════════
# ADMIN BOT — Webhook handler
# ═══════════════════════════════════════
pending = {}

def handle_update(update):
    msg = update.get('message', {})
    if not msg:
        return

    chat_id = msg['chat']['id']
    text = msg.get('text', '').strip()
    photo = msg.get('photo')

    if text == '/start':
        tg_send(chat_id,
            'Ingliz Futboli Bot v3.0 (CrewAI)\n\n'
            '3 agent: Researcher + Writer + Editor\n\n'
            'Matn yuboring — professional post\n'
            '/yangilik — Yangi xabar\n'
            '/stat — Statistika\n'
            '/clearcache — Keshni tozalash'
        )

    elif text == '/yangilik':
        tg_send(chat_id, 'Yangilik olinayapti (3 agent ishlaydi)...')
        ok = auto_news_post()
        tg_send(chat_id, '✅ Post yuborildi!' if ok else '❌ Yangi yangilik topilmadi.')

    elif text == '/stat':
        cnt, avg = get_stats()
        tg_send(chat_id, f'Bazada {cnt} ta yangilik.\nO\'rtacha ball: {round(avg or 0)}')

    elif text == '/clearcache':
        clear_cache()
        tg_send(chat_id, '✅ Kesh tozalandi! /yangilik yuboring.')

    elif text == 'Yuborish' and chat_id in pending:
        p = pending[chat_id]
        tg_send_channel(p['text'])
        del pending[chat_id]
        tg_send(chat_id, '✅ Kanalga yuborildi!')

    elif text == 'Bekor' and chat_id in pending:
        del pending[chat_id]
        tg_send(chat_id, '❌ Bekor qilindi.')

    elif text and not text.startswith('/'):
        tg_send(chat_id, '⏳ 3 agent ishlayapti...')
        try:
            article = {'title': text, 'description': '', 'url': None, 'score': 100}
            post = generate_post(article)
            pending[chat_id] = {'text': post}
            tg_send(chat_id, f'Ko\'rib chiqing:\n\n{post}')
            tg_send(chat_id, 'Yuborishni tasdiqlaysizmi?')
            requests.post(
                f'https://api.telegram.org/bot{TOKEN}/sendMessage',
                json={
                    'chat_id': chat_id,
                    'text': 'Tasdiqlang:',
                    'reply_markup': {
                        'keyboard': [['Yuborish'], ['Bekor']],
                        'resize_keyboard': True
                    }
                },
                timeout=10
            )
        except Exception as e:
            tg_send(chat_id, f'❌ Xatolik: {e}')


# ═══════════════════════════════════════
# HTTP SERVER
# ═══════════════════════════════════════
import json

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
            log.error(f'[webhook] {e}')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Ingliz Futboli Bot v3.0 - CrewAI')

    def log_message(self, *args):
        pass  # Server loglarini o'chirish


# ═══════════════════════════════════════
# INTERVAL THREAD
# ═══════════════════════════════════════
def news_loop():
    time.sleep(5)  # Serverga biroz vaqt
    while True:
        try:
            auto_news_post()
        except Exception as e:
            log.error(f'[loop] {e}')
        time.sleep(INTERVAL)


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════
if __name__ == '__main__':
    log.info(f'[server] Port {PORT} da ishga tushdi')

    # Background thread
    threading.Thread(target=news_loop, daemon=True).start()

    # HTTP server
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Bot to\'xtatildi.')
