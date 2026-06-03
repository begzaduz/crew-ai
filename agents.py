import re
import time
import logging

from groq import Groq, RateLimitError, APIStatusError
from config import GROQ_KEY, GROQ_MODEL
from feeds import fetch_article_text

log = logging.getLogger(__name__)
groq_client = Groq(api_key=GROQ_KEY)

# ── O'zbek nomlari ────────────────────────────────────────
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

def apply_names(text: str) -> str:
    if not text:
        return ''
    result = text
    for eng, uzb in sorted(NAMES.items(), key=lambda x: -len(x[0])):
        result = re.sub(rf'\b{re.escape(eng)}\b', uzb, result, flags=re.IGNORECASE)
    return result


# ── Groq API — retry bilan ────────────────────────────────
def groq_call(system_prompt: str, user_prompt: str,
              temperature: float = 0.4, max_tokens: int = 700) -> str:
    """
    Groq ga so'rov. Rate limit bo'lsa 3 marta qayta urinadi:
    1-urinish: 60s kutadi, 2-urinish: 120s, 3-urinish: xato ko'taradi.
    """
    delays = [60, 120]
    for attempt, delay in enumerate(delays + [None], start=1):
        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user',   'content': user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()

        except RateLimitError:
            if delay is None:
                log.error('[Groq] Rate limit — 3 urinishdan keyin ham xato.')
                raise
            log.warning(f'[Groq] Rate limit. {delay}s kutilmoqda... ({attempt}/3)')
            time.sleep(delay)

        except APIStatusError as e:
            log.error(f'[Groq] API xato: {e}')
            raise


# ── Rule-based validator ──────────────────────────────────
def validate_post(post: str) -> tuple[bool, str]:
    """
    Post qoidalarga mos ekanligini tekshiradi.
    (False, sabab) — rad etilgan
    (True, '')     — qabul qilindi
    """
    if len(post.strip()) < 50:
        return False, 'Post juda qisqa (< 50 belgi)'
    if len(post) > 1000:
        return False, f'Post juda uzun ({len(post)} belgi, max 1000)'
    markdown_patterns = [r'\*\*', r'__', r'\[.+\]\(.+\)', r'^#{1,6} ']
    for pat in markdown_patterns:
        if re.search(pat, post, re.MULTILINE):
            return False, f'Markdown belgisi topildi: {pat}'
    return True, ''


def ensure_channel_tag(post: str, tag: str = '@Inglizfutbol') -> str:
    """Post oxirida kanal tegi borligini kafolatlaydi."""
    if tag not in post:
        post = post.rstrip() + f'\n\n{tag}'
    return post


# ── Agent 1: Researcher ───────────────────────────────────
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

def researcher_agent(article: dict) -> str:
    content = fetch_article_text(article['url']) or ''
    if len(content) < 100:
        content = f"{article['title']}\n{article['description']}"

    result = groq_call(
        RESEARCHER_PROMPT,
        f"Analyze this Premier League news:\n\nHEADLINE: {article['title']}\nCONTENT: {content[:1200]}",
        temperature=0.2, max_tokens=300,
    )
    log.info(f'[Researcher] ✓ {article["title"][:50]}')
    return result


# ── Agent 2: Writer ───────────────────────────────────────
WRITER_PROMPT = """Sen @Inglizfutbol Telegram kanaliga professional o'zbek sport jurnalistisan.

KLUB TAXALLUSLARI — juda kam ishtilsin:
Arsenal = to'pchilar | Liverpool = qizillar | Chelsea = aristokratlar
Man City = fuqarolar | Man Utd = qizil iblislar | Tottenham = xo'rozlar
Newcastle = qarg'alar | Bournemouth = olchalar | West Ham = bolg'achilar
Crystal Palace = burgutlar | Wolves = bo'rilar | Brighton = qaldirg'ochlar
Brentford = arilar | Everton = karamellar | Aston Villa = villalar
Fulham = fulhamliklar | Nottingham Forest = o'rmonchilar

FUTBOL ATAMALAR:
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
- Takrorlanish YO'Q
- OXIRIDA doim @Inglizfutbol bo'lishi shart
- Faqat postni yoz, boshqa hech narsa yo'q"""

def writer_agent(article: dict, facts: str) -> str:
    result = groq_call(
        WRITER_PROMPT,
        f"Write Uzbek Telegram post:\n\nHEADLINE: {article['title']}\nFACTS:\n{facts}\n\nWrite ONLY the post:",
        temperature=0.5, max_tokens=600,
    )
    log.info(f'[Writer] ✓ {len(result)} belgi')
    return result


# ── Agent 3: Editor ───────────────────────────────────────
EDITOR_PROMPT = """Sen qattiq o'zbek sport muharririsan. Postni tekshir:

1. O'zbek tilimi? (rus/ingliz so'z yo'qmi)
2. 400-600 belgi orasidami?
3. Markdown belgilari yo'qmi (* _ [ ] **)?
4. O'ylab topilgan fakt yo'qmi?
5. @Inglizfutbol bilan tugadimi?
6. Faol gap ishlatildimi?
7. Takrorlanish yo'qmi?
8. Sarlavha 8 so'zdan oshmaydimi?

Agar HAMMA tekshiruvdan o'tsa: APPROVED yoz
Agar muammo bo'lsa: REJECTED: [sabab] yoz, keyin tuzatilgan versiyani FIXED: dan keyin yoz"""

def editor_agent(post: str, title: str) -> str:
    result = groq_call(
        EDITOR_PROMPT,
        f"Review this Uzbek post about: {title}\n\nPOST:\n{post}",
        temperature=0.2, max_tokens=700,
    )
    if 'APPROVED' in result:
        log.info('[Editor] ✓ Tasdiqlandi')
        return post
    elif 'FIXED:' in result:
        fixed = result.split('FIXED:')[-1].strip()
        log.info('[Editor] ✓ Tuzatildi')
        return fixed
    else:
        log.warning(f'[Editor] Natija noaniq: {result[:80]}')
        return post


# ── Pipeline: 3 agent zanjiri ─────────────────────────────
def generate_post(article: dict) -> str:
    """Researcher → Writer → Editor → Validator → apply_names"""
    log.info(f'[Pipeline] Boshlandi: {article["title"][:60]}')

    facts    = researcher_agent(article)
    raw_post = writer_agent(article, facts)
    edited   = editor_agent(raw_post, article['title'])

    # Rule-based validator (LLM dan mustaqil)
    post = ensure_channel_tag(edited)
    ok, reason = validate_post(post)
    if not ok:
        log.warning(f'[Validator] Rad: {reason} — original post qaytarildi')
        post = ensure_channel_tag(raw_post)

    # O'zbek nomlari
    return apply_names(post)
