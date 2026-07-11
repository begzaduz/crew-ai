import re
import json
import time
import logging

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from config import GEMINI_KEY, GEMINI_MODEL
from feeds import fetch_article_text

log = logging.getLogger(__name__)
gemini_client = genai.Client(api_key=GEMINI_KEY)

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
        result = re.sub(rf'(?<!\w){re.escape(eng)}(?!\w)', uzb, result, flags=re.IGNORECASE)
    return result


# ── Gemini API — kvota tejash uchun retry o'chirilgan ─────
def _generate(system_prompt: str, user_prompt: str, temperature: float,
               max_tokens: int, json_mode: bool) -> str:
    """Bitta Gemini so'rovini bajaradi. json_mode=True bo'lsa, Gemini'dan
    faqat valid JSON qaytarishni majburlaydi (response_mime_type orqali) —
    Editor agent uchun ishlatiladi, chunki matn ichidan 'APPROVED' kabi
    so'zlarni qidirish (eski usul) yolg'on-musbat va aniqlanmagan javob
    holatlariga moyil edi."""
    config_kwargs: dict = dict(
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    if json_mode:
        config_kwargs['response_mime_type'] = 'application/json'

    resp = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return (resp.text or '').strip()


def groq_call(system_prompt: str, user_prompt: str,
              temperature: float = 0.4, max_tokens: int = 700,
              json_mode: bool = False) -> str:
    """
    Gemini ga so'rov.
    RPD (kunlik) limit juda kichik bo'lgani uchun 429/RESOURCE_EXHAUSTED
    kelsa DARHOL xato ko'taradi — qayta urinish yo'q. Qayta urinish RPD
    tugagan holatda befoyda, faqat vaqtni yo'qotadi va process'ni bloklaydi.
    Faqat vaqtinchalik server xatosida (5xx) 1 marta 15s dan keyin
    qayta urinadi, chunki bu kvotaga aloqasi yo'q, tarmoq/server muammosi.
    Funksiya nomi 'groq_call' saqlanib qoldi — pastdagi agentlar shu nomni
    chaqiradi, ularga tegmaslik uchun.

    json_mode=True bo'lsa, javob response_mime_type='application/json'
    bilan so'raladi (Editor agent buni ishlatadi).
    """
    try:
        return _generate(system_prompt, user_prompt, temperature, max_tokens, json_mode)

    except ClientError as e:
        is_rate_limit = '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e)
        if is_rate_limit:
            log.error('[Gemini] Kvota tugadi (429) — qayta urinilmaydi, kvota tejaldi.')
        else:
            log.error(f'[Gemini] Client xato: {e}')
        raise

    except ServerError as e:
        log.warning('[Gemini] Server xato. 15s kutib 1 marta qayta urinamiz...')
        time.sleep(15)
        try:
            return _generate(system_prompt, user_prompt, temperature, max_tokens, json_mode)
        except Exception as e2:
            log.error(f'[Gemini] Server xato — qayta urinishdan keyin ham: {e2}')
            raise


# ── Rule-based validator ──────────────────────────────────
def validate_post(post: str) -> tuple[bool, str]:
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

LANGUAGE RULE (CRITICAL):
- Write MAIN, STATS, and CONTEXT entirely in Uzbek (Latin script), even though the source article is in English.
- Do NOT copy English sentences or phrases from the article into these fields.
- Club and player names may stay in their English form (they will be converted separately) — but all other words must be Uzbek.
- QUOTE may keep the original quoted words if translating would risk changing their meaning, but the speaker attribution should still read naturally.

Respond EXACTLY in this format:
MAIN: [fact, in Uzbek]
STATS: [numbers or NONE]
QUOTE: [quote — Name or NONE]
CONTEXT: [context or NONE, in Uzbek]
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
WRITER_PROMPT = """Sen @Inglizfutbol Telegram kanali uchun professional sport muharriri va jurnalistisan.

VAZIFA

Berilgan ma'lumotlardan qisqa, aniq va ishonchli sport yangiligi yarat.

ASOSIY QOIDALAR

- Faqat berilgan faktlardan foydalan.
- Hech qachon ma'lumot to'qib chiqma.
- Taxminni fakt sifatida yozma.
- Mish-mishni rasmiy yangilik sifatida ko'rsatma.
- Sonlar, sanalar va statistikalarni o'zgartirma.
- Eng muhim ma'lumot birinchi paragrafda bo'lsin.
- Professional sport jurnalistikasi uslubida yoz.
- Telegram uchun o'qilishi qulay format ishlat.
- Sun'iy iboralar va ortiqcha gaplardan qoch.
- Agar eng muhim faktni 15 ta so'z ichida aytish mumkin bo'lsa, uni birinchi jumlada ayt.

YANGILIK TURLARI

- TRANSFER
- MATCH_REPORT
- PRE_MATCH
- INJURY
- OFFICIAL
- INTERVIEW
- STATISTICS
- RECORD
- SUSPENSION
- TOURNAMENT

BREAKING

Faqat juda muhim va yangi yangiliklarda ishlat:

- Transfer tasdiqlansa
- Murabbiy iste'fosi
- Katta jarohat
- Rasmiy tayinlov
- Rekord darajadagi voqea

EMOJI

🚨 Muhim yangilik
🔥 Transfer
⚽ O'yin natijasi
🏆 Sovrin
🤕 Jarohat
✅ Rasmiy
📊 Statistika
⭐ Yulduz futbolchi

SARLAVHA

- Maksimum 8 so'z
- Qisqa va kuchli
- Clickbait yo'q
- Faktga asoslangan
- Senga "SARLAVHA:" nomi bilan berilgan matn — bu manbaning ASL (ko'pincha ingliz tilidagi) sarlavhasi, faqat mazmunni tushunish uchun berilgan
- Uni SO'ZMA-SO'Z yoki QISMAN ko'chirish QATʼIYAN TAQIQLANADI
- O'zing FAKTLAR asosida to'liq YANGI, original o'zbekcha sarlavha yoz
- Sarlavhada bitta ham ingliz so'zi yoki iborasi bo'lmasligi kerak (klub/futbolchi nomlaridan tashqari)

KLUB TAXALLUSLARI

Arsenal = to'pchilar | Liverpool = qizillar | Chelsea = aristokratlar
Man City = fuqarolar | Man Utd = qizil iblislar | Tottenham = xo'rozlar
Newcastle = qarg'alar | Bournemouth = olchalar | West Ham = bolg'achilar
Crystal Palace = burgutlar | Wolves = bo'rilar | Brighton = qaldirg'ochlar
Brentford = arilar | Everton = karamellar | Aston Villa = villalar
Fulham = fulhamliklar | Nottingham Forest = o'rmonchilar

FUTBOL ATAMALAR

- "survival" / "stay up" = "qolish", "ligada qolish"
- "relegation" = "past ligaga tushish"
- "top four" = "to'rtlik"
- "title" = "chempionlik"
- "clean sheet" = "darvozaga o'tkazmaslik"
- "hat-trick" = "het-trik"
- "penalty" = "jarima zarbasi"
- "red card" = "qizil karta"

FORMAT

[#BREAKING faqat kerak bo'lsa]

[Emoji] [Sarlavha]

[Lead paragraf]
Eng muhim ma'lumot.

[Asosiy paragraf]
Muhim tafsilotlar va kontekst.

[Statistika yoki qo'shimcha fakt]
Faqat mavjud bo'lsa.

[🎙 Iqtibos]
Faqat mavjud bo'lsa.

[Yakuniy paragraf]
Qisqa xulosa yoki keyingi voqea.

@Inglizfutbol

FORMAT TALABLARI

- Sarlavhadan keyin bitta bo'sh qator.
- Har bir paragraf orasida bitta bo'sh qator.
- Har bir paragraf 1–2 jumladan iborat bo'lsin.
- Uzun matn bloklari yaratma.
- O'qilishi oson bo'lsin.

Natijada faqat tayyor Telegram post qaytar.
Hech qanday izoh yozma.
Hech qanday markdown ishlatma."""

def writer_agent(article: dict, facts: str) -> str:
    result = groq_call(
        WRITER_PROMPT,
        f"Yangilik yoz:\n\nSARLAVHA: {article['title']}\nFAKTLAR:\n{facts}\n\nFaqat postni yoz:",
        temperature=0.5, max_tokens=600,
    )
    log.info(f'[Writer] ✓ {len(result)} belgi')
    return result


# ── Agent 3: Editor ───────────────────────────────────────
# YANGI: Editor endi erkin matn o'rniga QAT'IY JSON formatda javob beradi
# (Gemini response_mime_type='application/json' orqali majburlanadi).
# Bu eski 'APPROVED' in result / 'FIXED:' in result kabi satr-ichidan-qidirish
# usulini almashtiradi — u usul ikkita jiddiy kamchilikka ega edi:
#   1) 'APPROVED' so'zi tasodifiy boshqa kontekstda chiqsa — yolg'on-musbat.
#   2) Javob na 'APPROVED' na 'FIXED:' ni o'z ichiga olmasa, tekshirilmagan
#      original post baribir kanalga yuborilar edi (silent failure).
EDITOR_PROMPT = """Sen qattiq o'zbek sport muharririsan. Quyidagi Telegram postni tekshir:

1. Sarlavha VA matn 100% o'zbek tilidami? (Klub/futbolchi ismidan tashqari BITTA HAM ingliz so'z yoki ibora bo'lmasligi kerak — bo'lsa, bu jiddiy xato)
2. Sarlavhadan keyin bo'sh qator bormi?
3. Har paragraf orasida bo'sh qator bormi?
4. Har paragraf 1-2 jumladan iborat?
5. Markdown belgilari yo'qmi (* _ [ ] **)?
6. O'ylab topilgan fakt yo'qmi?
7. @Inglizfutbol bilan tugadimi?
8. Sarlavha 8 so'zdan oshmaydimi?

JAVOB FORMATI (QAT'IY — boshqa hech narsa yozma, faqat quyidagi JSON):

{
  "approved": true yoki false,
  "reason": "approved=false bo'lsa aniq sabab (o'zbekcha, qisqa, 1 jumla); approved=true bo'lsa bo'sh satr",
  "fixed_text": "agar tuzatish mumkin bo'lsa — postning TO'LIQ tuzatilgan matni (boshidan @Inglizfutbol gacha); aks holda null"
}

Qoidalar:
- Barcha 8 tekshiruvdan o'tsa: approved=true, fixed_text=null
- Kichik xato bo'lsa va tuzatish mumkin bo'lsa: approved=false, fixed_text ga TO'LIQ tuzatilgan postni yoz
- Post tuzatib bo'lmaydigan darajada buzilgan/noto'g'ri bo'lsa: approved=false, fixed_text=null
- fixed_text har doim postning TO'LIQ matni bo'lishi kerak, faqat o'zgargan qism emas
- JSON tashqarisida hech qanday matn, izoh yoki ``` belgisi yozma"""


def _parse_editor_json(raw: str) -> dict | None:
    """Editor javobini xavfsiz JSON'ga aylantiradi.
    Model ba'zan ```json ... ``` bilan o'rab yuborishi mumkin — shu holatni
    ham hisobga oladi. Har qanday parsing xatosida None qaytaradi (bu holat
    editor_agent tomonidan 'rad etildi' sifatida talqin qilinadi)."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def editor_agent(post: str, title: str) -> dict:
    """
    Postni Gemini orqali strukturaviy JSON formatda tekshiradi.
    Qaytaradi: {"approved": bool, "reason": str, "fixed_text": str|None}

    approved=False bo'lsa — chaqiruvchi tomon (generate_post) postni
    HECH QACHON kanalga yubormasligi kerak. Bu quyidagi barcha holatlar
    uchun amal qiladi: Editor rad etdi, JSON parse bo'lmadi, yoki javob
    kutilgan sxemaga mos kelmadi. Xavfsizlik tomoni har doim "rad etish"
    — noaniq holatda ham post yuborilmaydi.
    """
    raw = groq_call(
        EDITOR_PROMPT,
        f"Review this Uzbek post about: {title}\n\nPOST:\n{post}",
        temperature=0.1, max_tokens=800,
        json_mode=True,
    )

    data = _parse_editor_json(raw)
    if data is None:
        log.error(f'[Editor] JSON parse xato. Xom javob: {raw[:200]!r}')
        return {'approved': False, 'reason': 'editor_parse_error', 'fixed_text': None}

    approved = data.get('approved')
    reason = str(data.get('reason') or '').strip()
    fixed_text = data.get('fixed_text')

    if not isinstance(approved, bool):
        log.error(f'[Editor] "approved" maydoni yaroqsiz yoki yo\'q: {data!r}')
        return {'approved': False, 'reason': 'editor_schema_error', 'fixed_text': None}

    if approved:
        log.info('[Editor] ✓ Tasdiqlandi')
        return {'approved': True, 'reason': '', 'fixed_text': None}

    if isinstance(fixed_text, str) and len(fixed_text.strip()) >= 50:
        log.info(f'[Editor] ✓ Tuzatildi ({reason[:60] or "sabab ko\'rsatilmagan"})')
        return {'approved': True, 'reason': reason, 'fixed_text': fixed_text.strip()}

    log.warning(f'[Editor] ✗ Rad etildi: {reason or "sabab ko\'rsatilmagan"}')
    return {'approved': False, 'reason': reason or 'unspecified', 'fixed_text': None}


# ── Pipeline ──────────────────────────────────────────────
def generate_post(article: dict) -> str | None:
    """
    To'liq pipeline: Researcher -> Writer -> Editor -> Validator.

    Qaytaradi:
        str  — kanalga yuborishga tayyor, to'liq tekshirilgan post
        None — Editor postni tasdiqlamadi (yoki uni tekshira olmadi),
               yoki post oxirgi rule-based validatordan o'tmadi.
               Bu holatda chaqiruvchi tomon (main.py) postni HECH QACHON
               kanalga yubormasligi va shu maqolani qayta ishlangan deb
               belgilab, keyingisiga o'tishi kerak.

    Eslatma: avvalgi versiyada Editor/validator rad etsa ham, tekshirilmagan
    'raw_post' baribir kanalga yuborilar edi (fallback). Bu xavfli edi —
    endi bunday fallback yo'q: tekshiruvdan o'tmagan post umuman
    yuborilmaydi.
    """
    log.info(f'[Pipeline] Boshlandi: {article["title"][:60]}')

    facts = researcher_agent(article)
    raw_post = writer_agent(article, facts)

    editor_result = editor_agent(raw_post, article['title'])

    if not editor_result['approved']:
        log.warning(
            f'[Pipeline] ✗ Editor postni rad etdi, YUBORILMAYDI. '
            f'Sabab: {editor_result["reason"][:150]}'
        )
        return None

    final_text = editor_result['fixed_text'] or raw_post
    post = ensure_channel_tag(final_text)

    ok, reason = validate_post(post)
    if not ok:
        log.warning(f'[Pipeline] ✗ Rule-based validator rad etdi: {reason} — YUBORILMAYDI')
        return None

    return apply_names(post)
