import re
import logging
from datetime import datetime, timezone, timedelta

import feedparser
import requests
from config import ARTICLE_MAX_AGE_HOURS, MIN_SCORE

log = logging.getLogger(__name__)

RSS_FEEDS = [
    'https://www.theguardian.com/football/premierleague/rss',
    'https://feeds.bbci.co.uk/sport/football/rss.xml',
    'https://www.skysports.com/rss/12040',
]

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

# ── Qattiq blacklist — bu so'zlar bo'lsa maqola o'tkazilmaydi ──
BLACKLIST_PHRASES = [
    # Ayollar futboli
    "women's", "women's super league", "wsl", "lionesses", "barclays women",
    "women's football", "women's world cup",
    # Boshqa ligalar
    'scottish premiership', 'scottish league', 'scottish cup',
    'championship', 'league one', 'league two', 'league cup',
    'fa trophy', 'national league', 'non-league',
    # Boshqa sport turlari
    'darts', 'premier league darts', 'snooker', 'cycling',
    'swimming', 'athletics', 'olympics',
    'soccer', 'cricket', 'boxing', 'rugby',
    # Yoshlar va xalqaro
    'under-21', 'under-23', 'u21', 'u23', 'youth team',
    'international break', 'world cup qualifier', 'nations league',
    'euro 2024', 'euro 2025', 'euro 2026',
]


def score_article(title: str, desc: str) -> int:
    text = f'{title} {desc}'.lower()

    # ── Qattiq blacklist tekshiruvi ──
    for phrase in BLACKLIST_PHRASES:
        if phrase in text:
            log.debug(f'[Filter] Blacklist: "{phrase}" → {title[:50]}')
            return -999

    score = sum(10 for kw in HIGH_KEYWORDS if kw in text)
    score -= sum(20 for kw in LOW_KEYWORDS if kw in text)
    if any(w in text for w in ('breaking', 'official', 'confirmed')):
        score += 15
    return score


def fetch_news() -> list[dict]:
    seen: set[str] = set()
    articles: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ARTICLE_MAX_AGE_HOURS)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get('link', '')
                if not url or url in seen:
                    continue

                published = entry.get('published_parsed')
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue

                title = entry.get('title', '')
                desc = re.sub(r'<[^>]+>', ' ', entry.get('summary', '')).strip()
                score = score_article(title, desc)

                if score >= MIN_SCORE:
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
    log.info(f'[Feeds] Topildi: {len(articles)} ta yangilik')
    return articles


def fetch_article_text(url: str) -> str | None:
    """Maqola matnini olish. Avval trafilatura, keyin oddiy requests."""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if text and len(text) > 100:
                return text[:1500]
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
        return _re.sub(r'\n{3,}', '\n\n', md).strip()[:1500]
    except Exception as e:
        log.warning(f'[FetchText] {url}: {e}')
        return None


def fetch_og_image(url: str) -> str | None:
    """Maqoladan og:image URL olish."""
    if not url:
        return None
    try:
        res = requests.get(url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
        })
        res.raise_for_status()
        # og:image meta tagini qidirish
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
            res.text
        )
        if not match:
            # Ba'zi saytlarda tartib teskari bo'ladi
            match = re.search(
                r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']',
                res.text
            )
        if match:
            image_url = match.group(1)
            log.info(f'[OGImage] ✓ Topildi: {image_url[:60]}')
            return image_url
    except Exception as e:
        log.warning(f'[OGImage] {url}: {e}')
    return None
