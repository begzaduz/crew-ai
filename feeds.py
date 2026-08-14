import re
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests
from config import ARTICLE_MAX_AGE_HOURS, MIN_SCORE

log = logging.getLogger(__name__)

# MUHIM: feedparser standart holatda O'ZINING User-Agent'ini
# ('python-feedparser/...') yuboradi — ko'p yirik nashriyot saytlari
# (masalan talkSPORT/News UK) buni bot-himoya orqali avtomatik bloklab,
# BO'SH (0 ta entries) javob qaytaradi — HTTP xato ham, exception ham
# bo'lmaydi, shuning uchun bu jimgina "manba ishlamayapti" ko'rinishida
# namoyon bo'ladi. Oddiy brauzer User-Agent'i bilan so'rov yuborish bu
# muammoni oldini oladi (fetch_article_text/fetch_article_image'da
# allaqachon xuddi shu sabab bilan qo'llanilgan yondashuv).
_FEED_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

# Faqat seed (birinchi marta DB bo'sh bo'lganda data_sources jadvaliga
# yoziladigan) standart ro'yxat. Runtime'da fetch_news() BU o'zgaruvchini
# ishlatmaydi — chaqiruvchi (main.py) manbalarni har doim DB'dagi
# data_sources jadvalidan olib, parametr sifatida beradi.
DEFAULT_RSS_FEEDS = [
    'https://www.theguardian.com/football/premierleague/rss',
    'https://www.skysports.com/rss/12040',
    'https://www.90min.com/posts.rss',
    'https://www.caughtoffside.com/feed',
]

HIGH_KEYWORDS = [
    'premier league', 'transfer', 'signing', 'manager', 'sacked', 'fired',
    'injured', 'injury', 'goal', 'match', 'result', 'win', 'defeat', 'score',
    'champions league', 'fa cup', 'europa league', 'breaking', 'confirmed', 'official',
    'arsenal', 'chelsea', 'liverpool', 'manchester', 'tottenham', 'newcastle',
    'aston villa', 'west ham', 'brighton', 'everton', 'wolves', 'bournemouth',
    'brentford', 'fulham', 'crystal palace', 'million', 'contract', 'deal', 'fee',
]

# Premier League klublari — kamida bittasi (yoki "premier league" so'zi) matnda
# bo'lishi SHART, aks holda maqola avtomatik rad etiladi.
PL_SIGNAL_KEYWORDS = [
    'premier league', 'epl', 'arsenal', 'chelsea', 'liverpool',
    'manchester united', 'manchester city', 'man utd', 'man city', 'man united',
    'tottenham', 'spurs', 'newcastle', 'aston villa', 'west ham', 'brighton',
    'everton', 'wolves', 'wolverhampton', 'bournemouth', 'brentford', 'fulham',
    'crystal palace', 'nottingham forest', 'leeds', 'sunderland', 'burnley',
    'ipswich', 'southampton',
]

# Hard blacklist — bu so'zlardan biri topilsa, maqola qanchalik "PL"ga o'xshab
# ko'rinmasin, darhol -999 ball bilan rad etiladi.
BLACKLIST_PHRASES = [
    'nba', 'nfl', 'cricket', 'rugby', 'golf', 'tennis', 'formula 1', 'nascar',
    'baseball', 'hockey', 'basketball', 'ufc', 'boxing', 'bundesliga',
    'serie a', 'ligue 1', 'la liga', 'mls', 'eredivisie', 'saudi pro league',
    'championship play-off', 'efl championship', 'league one', 'league two',
    'scottish premiership', "women's super league", ' wsl ',
    'under-21', 'under-23', 'u21', 'u23', 'youth team', 'academy fixture',
]

# Rasm URL da bo'lmasligi kerak bo'lgan so'zlar
IMAGE_BLACKLIST = [
    'gossip', 'logo', 'badge', 'icon', 'avatar', 'placeholder',
    'generic', 'default', 'blank', 'sport/images/generic',
]


def _normalize_url(url: str) -> str:
    """Dublikatlarni aniqlash uchun URL'ni normallashtiradi: query
    parametrlari (masalan ?utm_source=..., ?ref=...) va fragment olib
    tashlanadi.

    SABAB: ko'p sport saytlari bir xil maqolaga har safar boshqa
    tracking parametr bilan RSS'da havola beradi (masalan
    caughtoffside.com) — bu aks holda bir xil maqolani "yangi" deb
    qayta ishlashga, natijada Review Queue'da dublikat postlarga olib
    keladi (va behuda Gemini API xarajatiga)."""
    if not url:
        return url
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def score_article(title: str, desc: str) -> int:
    text = f'{title} {desc}'.lower()

    # 1) Hard blacklist — boshqa sport/liga so'zi topilsa, darhol rad
    if any(bad in text for bad in BLACKLIST_PHRASES):
        return -999

    # 2) Premier League signali SHART — bo'lmasa, generic so'zlar (transfer,
    #    million, contract kabi) ko'p bo'lsa ham maqola rad etiladi
    if not any(sig in text for sig in PL_SIGNAL_KEYWORDS):
        return -999

    score = sum(10 for kw in HIGH_KEYWORDS if kw in text)
    if any(w in text for w in ('breaking', 'official', 'confirmed')):
        score += 15
    return score


def _is_blacklisted_image(img_url: str) -> bool:
    return any(bad in img_url.lower() for bad in IMAGE_BLACKLIST)


def _parse_og_image(html: str) -> str | None:
    """HTML matnidan og:image meta teg qiymatini ajratib oladi (rasm hali
    yuklab olinmagan, faqat HTML matni tahlil qilinadi — tarmoq so'rovi
    yo'q)."""
    match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if not match:
        # Boshqa tartib: content oldin, property keyin kelishi ham mumkin
        match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            html, re.IGNORECASE
        )
    return match.group(1).strip() if match else None


def _extract_body_image(html: str, exclude: str | None = None) -> str | None:
    """Maqola MATNI ICHIDAGI birinchi mos rasmni topadi (trafilatura
    orqali) — navigatsiya, logo, footer, reklama rasmlari avtomatik
    chetlab o'tiladi, chunki trafilatura faqat asosiy kontent blokini
    o'qiydi.

    `exclude` — og:image URL manzili beriladi: ko'p saytlar muqova
    rasmini maqola matni ichiga HAM qo'shib qo'yadi (birinchi rasm
    sifatida takrorlanadi); bunday holatda uni o'tkazib, keyingi
    (haqiqiy, matn ichidagi) rasmni qaytaramiz."""
    try:
        import trafilatura
        md = trafilatura.extract(
            html, include_images=True, output_format='markdown',
            include_comments=False, include_tables=False,
        )
        if not md:
            return None
        for m in re.finditer(r'!\[[^\]]*\]\(([^)\s]+)\)', md):
            img_url = m.group(1).strip()
            if not img_url.startswith('http'):
                continue
            if exclude and img_url == exclude:
                continue
            if _is_blacklisted_image(img_url):
                continue
            return img_url
    except ImportError:
        pass
    except Exception as e:
        log.warning(f'[Image] Body-image tahlili xato: {e}')
    return None


def fetch_article_image(url: str) -> str | None:
    """Postga qo'shiladigan rasmni tanlaydi.

    USTUVORLIK: maqola MATNI ICHIDAGI rasm — chunki sayt bergan "muqova"
    (og:image) ko'pincha o'sha saytning o'z headline matni va
    logotipi/watermarki bilan tayyorlangan grafika bo'ladi (masalan
    Sky Sports, 90min), va buni @Inglizfutbol kanalida ishlatish boshqa
    manba brendini ko'rsatib, chalkashtirib yuboradi. Matn ichidagi oddiy
    foto (futbolchi/o'yin surati) bunday muammoni keltirib chiqarmaydi.

    Agar maqola ichida mos rasm topilmasa, fallback sifatida og:image
    ishlatiladi (umuman rasmsiz qolishdan ko'ra shu afzal).
    """
    if not url:
        return None
    try:
        res = requests.get(url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
        })
        res.raise_for_status()
        html = res.text
    except Exception as e:
        log.warning(f'[Image] {url}: {e}')
        return None

    og_image = _parse_og_image(html)

    body_image = _extract_body_image(html, exclude=og_image)
    if body_image:
        return body_image

    if og_image and not _is_blacklisted_image(og_image):
        log.info('[Image] Matn ichida mos rasm topilmadi — og:image (muqova) ishlatildi')
        return og_image

    return None


def fetch_news(rss_feeds: list[str]) -> list[dict]:
    """RSS manbalar ro'yxatidan yangiliklarni oladi.

    MUHIM: rss_feeds endi majburiy parametr — chaqiruvchi (main.py) buni
    DB'dagi data_sources jadvalidan olib beradi. Bu yerda RSS manzillari
    qattiq yozilmagan (hardcode qilinmagan), shu bilan Dashboard'dan
    qo'shilgan/o'chirilgan manbalar darhol amalda qo'llaniladi.
    """
    if not rss_feeds:
        log.warning("[Feeds] RSS manbalar ro'yxati bo'sh — hech narsa olinmadi.")
        return []

    seen: set[str] = set()
    articles: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ARTICLE_MAX_AGE_HOURS)

    # Har bir manba nechta yangilik berayotganini (va nega ko'plari
    # chetlanayotganini) ko'rish uchun — Railway loglarida ko'rinadi.
    # Buni Dashboard'dagi "faqat bitta manba ishlayaptimi yoki bu
    # tasodifmi" degan savolga javob berish uchun qo'shildi.
    feed_stats: list[tuple[str, dict]] = []

    for feed_url in rss_feeds:
        stats = {'jami': 0, 'eski': 0, 'mos_emas': 0, 'otdi': 0, 'xato': None}
        try:
            feed = feedparser.parse(feed_url, request_headers={'User-Agent': _FEED_USER_AGENT})
            stats['jami'] = len(feed.entries)
            # Diagnostika: agar hech qanday entry topilmasa, sabab (HTTP
            # status yoki parsing xatosi — 'bozo') loglarga qo'shiladi,
            # shunda "0 ta" natija User-Agent bloklanishimi, noto'g'ri
            # URL'mi yoki boshqa sababmi — logdan darhol bilinadi.
            if not feed.entries:
                http_status = getattr(feed, 'status', None)
                bozo_reason = str(feed.get('bozo_exception', '')) if feed.get('bozo') else ''
                stats['xato'] = f"bo'sh javob (http_status={http_status}, bozo={bozo_reason[:80]})"
            for entry in feed.entries:
                url = _normalize_url(entry.get('link', ''))
                if not url or url in seen:
                    continue

                published = entry.get('published_parsed')
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        stats['eski'] += 1
                        continue

                title = entry.get('title', '')
                desc = re.sub(r'<[^>]+>', ' ', entry.get('summary', '')).strip()
                score = score_article(title, desc)

                if score >= MIN_SCORE:
                    seen.add(url)
                    stats['otdi'] += 1
                    articles.append({
                        'url': url,
                        'title': title,
                        'description': desc[:300],
                        'score': score,
                    })
                else:
                    stats['mos_emas'] += 1
        except Exception as e:
            stats['xato'] = str(e)
            log.error(f'[RSS] {feed_url}: {e}')
        feed_stats.append((feed_url, stats))

    for feed_url, s in feed_stats:
        if s['xato']:
            log.info(f"[Feeds] {feed_url} -> XATO: {s['xato']}")
        else:
            log.info(
                f"[Feeds] {feed_url} -> jami:{s['jami']} "
                f"o'tdi:{s['otdi']} mos_emas:{s['mos_emas']} eski:{s['eski']}"
            )

    articles.sort(key=lambda x: x['score'], reverse=True)
    log.info(f'[Feeds] Topildi: {len(articles)} ta yangilik ({len(rss_feeds)} ta manbadan)')
    return articles


def fetch_article_text(url: str) -> str | None:
    """Maqola matnini olish."""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if text and len(text) > 100:
                return text[:2500]
    except ImportError:
        pass
    except Exception as e:
        log.warning(f'[Trafilatura] {url}: {e}')

    try:
        from markdownify import markdownify
        res = requests.get(url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
        })
        res.raise_for_status()
        import re as _re
        md = markdownify(res.text, heading_style='ATX', strip=['script', 'style', 'nav', 'footer'])
        return _re.sub(r'\n{3,}', '\n\n', md).strip()[:2500]
    except Exception as e:
        log.warning(f'[FetchText] {url}: {e}')
        return None
