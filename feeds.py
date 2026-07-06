import re
import logging
from datetime import datetime, timezone, timedelta

import feedparser
import requests
from config import ARTICLE_MAX_AGE_HOURS, MIN_SCORE

log = logging.getLogger(__name__)

RSS_FEEDS = [
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


def fetch_og_image(url: str) -> str | None:
    """Maqola sahifasidan og:image URL ni oladi."""
    if not url:
        return None
    try:
        res = requests.get(url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
        })
        res.raise_for_status()
        # og:image meta tegini qidirish
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            res.text, re.IGNORECASE
        )
        if not match:
            # Boshqa tartib
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                res.text, re.IGNORECASE
            )
        if match:
            img_url = match.group(1).strip()
            # Blacklist tekshiruvi
            img_lower = img_url.lower()
            if any(bad in img_lower for bad in IMAGE_BLACKLIST):
                log.info(f'[Image] Blacklist: {img_url[:60]}')
                return None
            return img_url
    except Exception as e:
        log.warning(f'[Image] {url}: {e}')
    return None


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
    """Maqola matnini olish."""
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
