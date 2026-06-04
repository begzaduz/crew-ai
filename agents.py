import re
import time
import logging

from groq import Groq, RateLimitError, APIStatusError
from config import GROQ_KEY, GROQ_MODEL
from feeds import fetch_article_text

log = logging.getLogger(__name__)
groq_client = Groq(api_key=GROQ_KEY)

NAMES = {
    # Turnirlar
    'Premier League': 'Premier-liga',
    'Champions League': 'Chempionlar ligasi',
    'FA Cup': 'FA Kubogi',
    'Carabao Cup': 'Karabao Kubogi',
    'Europa League': 'Evropa ligasi',
    'Conference League': 'Konferensiyalar ligasi',

    # Klublar — faqat to'liq nom, laqab yo'q
    'Manchester City': 'Manchester Siti',
    'Man City': 'Manchester Siti',
    'Manchester United': 'Manchester Yunayted',
    'Man United': 'Manchester Yunayted',
    'Man Utd': 'Manchester Yunayted',
    'Chelsea': 'Chelsea',
    'Liverpool': 'Liverpool',
    'Tottenham Hotspur': 'Tottenham Xotspur',
    'Tottenham': 'Tottenham',
    'Spurs': 'Tottenham',
    'Newcastle United': 'Nyukasl Yunayted',
    'Newcastle': 'Nyukasl',
    'West Ham United': 'Vest Xem Yunayted',
    'West Ham': 'Vest Xem',
    'Brighton': 'Brighton',
    'Crystal Palace': 'Kristal Pelas',
    'Fulham': 'Fulham',
    'Bournemouth': 'Bornmut',
    'Nottingham Forest': 'Nottingem Forest',
    'Leicester City': 'Lester Siti',
    'Leicester': 'Lester',
    'Wolverhampton': 'Vulverhempton',
    'Wolves': 'Vulverhempton',
    'Brentford': 'Brentford',
    'Everton': 'Everton',
    'Aston Villa': 'Aston Villa',
    'Ipswich Town': 'Ipswich Taun',
    'Ipswich': 'Ipswich',
    'Southampton': 'Sauthamton',
    'Arsenal': 'Arsenal',

    # O'yinchilar
    'Erling Haaland': 'Erling Holland',
    'Haaland': 'Holland',
    'Mohamed Salah': 'Muhammad Saloh',
    'Salah': 'Saloh',
    'Virgil van Dijk': 'Virjil van Deyk',
    'Marcus Rashford': 'Markus Reshford',
    'Rashford': 'Reshford',
    'Cole Palmer': 'Koul Palmer',
    'Palmer': 'Palmer',
    'Bukayo Saka': 'Bukayo Saka',
    'Saka': 'Saka',
    'Alexander Isak': 'Aleksandr Isak',
    'Isak': 'Isak',
    'Jarrod Bowen': 'Jarrod Bouen',
    'Declan Rice': 'Deklan Rays',
    'Trent Alexander-Arnold': 'Trent Aleksandr-Arnold',
    'Darwin Nunez': 'Darvin Nunyes',
    'Bruno Fernandes': 'Bruno Fernandesh',
    'Kevin De Bruyne': 'Kevin De Bruyn',
    'De Bruyne': 'De Bruyn',
    'Phil Foden': 'Fil Foden',
    'Foden': 'Foden',
    'Jack Grealish': 'Jek Grilish',
    'Grealish': 'Grilish',
    'Ollie Watkins': 'Olli Uotkins',
    'Watkins': 'Uotkins',
    'Dominic Solanke': 'Dominik Solanke',
    'Solanke': 'Solanke',
    'Cysencio Summerville': 'Saysensio Summervil',
    'Summerville': 'Summervil',

    # Murabbiylar
    'Pep Guardiola': 'Pep Gvardiola',
    'Guardiola': 'Gvardiola',
    'Mikel Arteta': 'Mikel Arteta',
    'Arteta': 'Arteta',
    'Arne Slot': 'Arne Slot',
    'Slot': 'Slot',
    'Enzo Maresca': 'Enzo Maresca',
    'Maresca': 'Maresca',
    'Erik ten Hag': 'Erik ten Xag',
    'ten Hag': 'ten Xag',
    'Eddie Howe': 'Eddi Xau',
    'Howe': 'Xau',
    'Oliver Glasner': 'Oliver Glazner',
    'Glasner': 'Glazner',
    'Marco Silva': 'Marko Silva',
    'Andoni Iraola': 'Andoni Iraola',
    'Iraola': 'Iraola',
    'Thomas Frank': 'Tomas Frank',
    'Julen Lopetegui': 'Xulen Lopetegi',
    'Lopetegui': 'Lopetegi',
    'Graham Potter': 'Grem Potter',
    'Potter': 'Potter',
    'Michael Carrick': 'Maykl Karrik',
    'Carrick': 'Karrik',
    'Ruben Amorim': 'Ruben Amorim',
    'Amorim': 'Amorim',
    'Fabian Hurzeler': 'Fabian Xurtseler',
    'Hurzeler': 'Xurtseler',
    'Nuno Espirito Santo': 'Nuno Espirito Santo',
}


def apply_names(text: str) -> str:
    if not text:
        return ''
    result = text
    for eng, uzb in sorted(NAMES.items(), key=lambda x: -len(x[0])):
        result = re.sub(rf'\b{re.escape(eng)}\b', uzb, result, flags=re.IGNORECASE)
    return result


def groq_call(system_prompt: str, user_prompt: str,
              temperature: float = 0.4, max_tokens: int = 700) -> str:
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


def validate_post(post: str) -> tuple[bool, str]:
    if len(post.strip()) < 50:
        return False, 'Post juda qisqa (< 50 belgi)'
    if len(post) > 1000:
        return False, f'Post juda uzun ({len(post)} belgi, max 1000)'
    # Markdown: faqat **sarlavha** ruxsat, boshqa markdown taqiqlangan
    forbidden_patterns = [r'(?<!\*)\*(?!\*)', r'__', r'\[.+\]\(.+\)', r'^#{1,6} ']
    for pat in forbidden_patterns:
        if re.search(pat, post, re.MULTILINE):
            return False, f'Ruxsatsiz markdown belgisi: {pat}'
    return True, ''


def ensure_channel_tag(post: str, tag: str = '@Inglizfutbol') -> str:
    if tag not in post:
        post = post.rstrip() + f'\n\n{tag}'
    return post


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


WRITER_PROMPT = """Sen @Inglizfutbol Telegram kanaliga professional o'zbek sport jurnalistisan.

JAMOA NOMLARI QOIDASI — MAJBURIY:
- Har doim TO'LIQ nom ishlatiladi: Arsenal, Liverpool, Chelsea, Manchester Siti va h.k.
- HECH QACHON laqab ishlatilmaydi (to'pchilar, qizillar, aristokratlar kabi so'zlar TAQIQLANGAN)
- Bir post ichida jamoa nomi 2 martadan ko'p takrorlanmasin

FORMAT — BREAKING xabar (BREAKING: YES):
```
🔴 #BREAKING

**[Sarlavha — 6-8 so'z, ta'sirchan]**

[Asosiy fakt — kim, nima qildi, qayerda. 1-2 qisqa jumla.]

[Tafsilot — raqamlar, shartnoma muddati, transfer summasi. 2-3 jumla.]

🎙 "[Iqtibos]" — Ismi

[Xulosa — jadval o'rni yoki keyingi o'yin]

@Inglizfutbol
```

FORMAT — Oddiy xabar (BREAKING: NO):
```
[Asosiy fakt — kim, nima qildi. 1-2 qisqa jumla.]

[Tafsilot — raqamlar, statistika, kontekst. 1-2 jumla.]

🎙 "[Iqtibos]" — Ismi (FAQAT mavjud bo'lsa)

@Inglizfutbol
```

UZUNLIK: 300-450 belgi (iqtibossiz), 400-500 belgi (iqtibos bilan)

QOIDALAR:
- Faqat o'zbek tili. Faol gap. Qisqa jumlalar.
- Markdown: FAQAT sarlavhada **qalin** ishlatiladi. Boshqa hech qayerda yo'q.
- O'ylab topilgan fakt yo'q — faqat berilgan faktlar
- Har bir paragraf orasida bo'sh qator bo'lsin
- OXIRIDA doim @Inglizfutbol bo'lishi shart
- Faqat postni yoz, boshqa hech narsa yo'q
- Valyutani soddalashtir: faqat asosiy raqam (million funt yoki million yevro, ikkisi birga emas)"""


def writer_agent(article: dict, facts: str) -> str:
    result = groq_call(
        WRITER_PROMPT,
        f"Write Uzbek Telegram post:\n\nHEADLINE: {article['title']}\nFACTS:\n{facts}\n\nWrite ONLY the post:",
        temperature=0.5, max_tokens=600,
    )
    log.info(f'[Writer] ✓ {len(result)} belgi')
    return result


EDITOR_PROMPT = """Sen qattiq o'zbek sport muharririsan. Postni tekshir:

1. O'zbek tilimi? (rus/ingliz so'z yo'qmi)
2. 300-500 belgi orasidami?
3. BREAKING postda: **sarlavha** qalin yozilganmi? Bo'sh qator bilan ajratilganmi?
4. Oddiy postda: sarlavha yo'qmi? (sarlavha bo'lmasligi kerak)
5. Laqab ishlatilmaganmi? (to'pchilar, qizillar, aristokratlar kabi so'zlar TAQIQLANGAN)
6. Faqat **qalin** markdown bor, boshqa markdown yo'qmi?
7. @Inglizfutbol bilan tugadimi?
8. Har bir paragraf orasida bo'sh qator bormi?
9. Valyuta faqat bittami?
10. Faol gap ishlatildimi?

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


def generate_post(article: dict) -> str:
    log.info(f'[Pipeline] Boshlandi: {article["title"][:60]}')

    facts    = researcher_agent(article)
    raw_post = writer_agent(article, facts)
    edited   = editor_agent(raw_post, article['title'])

    post = ensure_channel_tag(edited)
    ok, reason = validate_post(post)
    if not ok:
        log.warning(f'[Validator] Rad: {reason} — original post qaytarildi')
        post = ensure_channel_tag(raw_post)

    return apply_names(post)
