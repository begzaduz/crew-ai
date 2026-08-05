"""RSS Yangiliklar workflow — Researcher + Writer + Editor pipeline.

MUHIM: Bu pipeline endi loyiha-agnostik (universal) — faqat "Ingliz
Futboli"ga emas, istalgan mavzudagi (sport, texnologiya, moda va h.k.)
loyihaga xizmat qila oladi. Loyihaga xos HAMMA narsa (terminologiya,
taxalluslar, kanal, uslub, soha tavsifi, kontent turlari, maxsus
atamalar, emoji) DB'dagi workflows.config ustunidan (database.
get_workflow_config) HAR BIR chaqiruvda o'qiladi. Dashboard'da bularni
tahrirlab saqlasangiz, keyingi generate_post() chaqiruvi darhol yangi
qiymatlarni ishlatadi — qayta deploy shart emas.

Kod ichida FAQAT haqiqatan loyihadan-loyihaga o'zgarmaydigan "vazifa
qoidalari" qoladi: prompt tuzilishi, formatlash qoidalari (bo'sh
qatorlar, paragraf uzunligi, markdown taqiqi, sarlavha uzunligi va
h.k.), til qoidalari. DEFAULT_* konstantalar esa faqat (a) "Ingliz
Futboli" loyihasini birinchi marta urug'lantirish uchun, va (b) agar
biror loyiha hali konfiguratsiya qilinmagan bo'lsa, oraliq fallback
sifatida ishlatiladi.
"""
import re
import time
import logging

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

import database
from config import GEMINI_KEY, GEMINI_MODEL
from feeds import fetch_article_text
from telegram_utils import sanitize_telegram_html

log = logging.getLogger(__name__)
gemini_client = genai.Client(api_key=GEMINI_KEY)

# Loyihalar endi o'zining alohida Gemini API kalitidan foydalanishi mumkin
# (workflows.config['gemini_api_key']) — shunda bir nechta loyiha bitta
# umumiy kalitning kunlik RPD kvotasini baham ko'rmaydi (har biri o'z
# Google akkaunti/kalitining kvotasi bilan cheklanadi). Kalit berilmagan
# loyihalar avvalgidek global GEMINI_KEY'dan foydalanadi. Har xil kalit
# uchun genai.Client()'ni qayta yaratmaslik uchun keshlanadi.
_client_cache: dict[str, genai.Client] = {GEMINI_KEY: gemini_client}


def get_gemini_client(api_key: str | None = None) -> genai.Client:
    key = (api_key or '').strip() or GEMINI_KEY
    client = _client_cache.get(key)
    if client is None:
        client = genai.Client(api_key=key)
        _client_cache[key] = client
    return client


# ── Standart (seed) qiymatlar — "Ingliz Futboli" loyihasi uchun ────
# Bular FAQAT loyiha birinchi marta yaratilganda DB'ga yoziladi
# (database.seed_project_if_empty), va agar boshqa bir loyiha hali
# konfiguratsiya qilinmagan bo'lsa, oraliq fallback sifatida ishlaydi.
# Runtime'da generate_post() avvalo DB'dagi joriy config'ni ishlatadi.
DEFAULT_CHANNEL_TAG = '@Inglizfutbol'

DEFAULT_TONE = "professional sport jurnalistikasi uslubida, aniq va ishonchli"

DEFAULT_DOMAIN_DESCRIPTION = "Premier League football"

DEFAULT_CONTENT_TYPES = [
    'TRANSFER', 'MATCH_REPORT', 'PRE_MATCH', 'INJURY', 'OFFICIAL',
    'INTERVIEW', 'STATISTICS', 'RECORD', 'SUSPENSION', 'TOURNAMENT',
]

DEFAULT_JARGON = {
    'survival': 'qolish',
    'stay up': 'qolish',
    'relegation': 'past ligaga tushish',
    'relegation battle': 'pasayish kurashi',
    'top four': "to'rtlik",
    'title': 'chempionlik',
    'title race': 'chempionlik kurashi',
    'clean sheet': "darvozaga o'tkazmaslik",
    'hat-trick': 'het-trik',
    'penalty': 'jarima zarbasi',
    'red card': 'qizil karta',
}

DEFAULT_EMOJI_LEGEND = {
    '🚨': 'Muhim yangilik',
    '🔥': 'Transfer',
    '⚽': "O'yin natijasi",
    '🏆': 'Sovrin',
    '🤕': 'Jarohat',
    '✅': 'Rasmiy',
    '📊': 'Statistika',
    '⭐': 'Yulduz futbolchi',
}

DEFAULT_TERMINOLOGY = {
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

DEFAULT_NICKNAMES = {
    'Arsenal': "to'pchilar",
    'Liverpool': 'qizillar',
    'Chelsea': 'aristokratlar',
    'Man City': 'fuqarolar',
    'Man Utd': 'qizil iblislar',
    'Tottenham': "xo'rozlar",
    'Newcastle': "qarg'alar",
    'Bournemouth': 'olchalar',
    'West Ham': "bolg'achilar",
    'Crystal Palace': 'burgutlar',
    'Wolves': "bo'rilar",
    'Brighton': "qaldirg'ochlar",
    'Brentford': 'arilar',
    'Everton': 'karamellar',
    'Aston Villa': 'villalar',
    'Fulham': 'fulhamliklar',
    'Nottingham Forest': "o'rmonchilar",
}


def apply_names(text: str, terminology: dict) -> str:
    """Terminologiya lug'atini matnga qo'llaydi (loyihaga xos, DB'dan keladi)."""
    if not text:
        return ''
    result = text
    for eng, uzb in sorted(terminology.items(), key=lambda x: -len(x[0])):
        result = re.sub(rf'(?<!\w){re.escape(eng)}(?!\w)', uzb, result, flags=re.IGNORECASE)
    return result


# ── Loyihaga xos bloklarni promptga quyish uchun yordamchilar ──────
def _jargon_block(jargon: dict, empty_text: str = '') -> str:
    if not jargon:
        return empty_text
    return '\n'.join(f'- "{eng}" = "{uzb}"' for eng, uzb in jargon.items())


def _content_types_block(content_types: list) -> str:
    if not content_types:
        return "(turlar belgilanmagan — mazmuniga qarab mos tarzda yoz)"
    return '\n'.join(f'- {t}' for t in content_types)


def _emoji_block(emoji_legend: dict) -> str:
    if not emoji_legend:
        return "🚨 Muhim yangilik\n✅ Rasmiy tasdiqlangan xabar\n📊 Statistika/raqamlar"
    return '\n'.join(f'{emoji} {meaning}' for emoji, meaning in emoji_legend.items())


def _nicknames_block(nicknames: dict) -> str:
    if not nicknames:
        return "(taxalluslar berilmagan — nomlarni asl holida qoldir)"
    return '\n'.join(f'{eng} = {uzb}' for eng, uzb in nicknames.items())


# ── Gemini API — kvota tejash uchun retry o'chirilgan ─────
def groq_call(system_prompt: str, user_prompt: str,
              temperature: float = 0.4, max_tokens: int = 700,
              client: genai.Client | None = None) -> str:
    """
    Gemini ga so'rov.
    RPD (kunlik) limit juda kichik bo'lgani uchun 429/RESOURCE_EXHAUSTED
    kelsa DARHOL xato ko'taradi — qayta urinish yo'q. Qayta urinish RPD
    tugagan holatda befoyda, faqat vaqtni yo'qotadi va process'ni bloklaydi.
    Faqat vaqtinchalik server xatosida (5xx) 1 marta 15s dan keyin
    qayta urinadi, chunki bu kvotaga aloqasi yo'q, tarmoq/server muammosi.

    client — chaqiruvchi (generate_post) loyihaning o'z Gemini kalitidan
    yasagan client. Berilmasa, global (asosiy) kalit ishlatiladi.
    """
    client = client or gemini_client
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return (resp.text or '').strip()

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
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return (resp.text or '').strip()
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


def ensure_channel_tag(post: str, tag: str) -> str:
    if tag not in post:
        post = post.rstrip() + f'\n\n{tag}'
    return post


# ── Agent 1: Researcher (STATIC qism — prompt tuzilishi, til qoidasi.
# DINAMIK qism — {domain_description} va {jargon_rules_block}, DB'dan
# keladi, loyihadan-loyihaga farq qiladi) ──────────────────────────
RESEARCHER_PROMPT_TEMPLATE = """You are a {domain_description} news analyst. Extract ONLY real facts from the article.

Extract exactly:
1. MAIN: One sentence — who did what (subject, action, result)
2. STATS: Numbers, metrics, or key figures mentioned — or NONE
3. QUOTE: Exact quote with speaker name — or NONE
4. CONTEXT: Background, history, upcoming events, related facts — or NONE
5. BREAKING: YES only for major, urgent, or unusually significant news. Otherwise NO

STRICT RULES:
- Only facts from the article. Zero invented content.
{jargon_rules_block}

LANGUAGE RULE (CRITICAL):
- Write MAIN, STATS, and CONTEXT entirely in Uzbek (Latin script), even though the source article is in English.
- Do NOT copy English sentences or phrases from the article into these fields.
- Proper names (people, organizations, products, places) may stay in their original form (they will be converted separately) — but all other words must be Uzbek.
- QUOTE may keep the original quoted words if translating would risk changing their meaning, but the speaker attribution should still read naturally.

Respond EXACTLY in this format:
MAIN: [fact, in Uzbek]
STATS: [numbers or NONE]
QUOTE: [quote — Name or NONE]
CONTEXT: [context or NONE, in Uzbek]
BREAKING: [YES or NO]"""


def researcher_agent(article: dict, domain_description: str, jargon: dict,
                      prompt_template: str | None = None,
                      client: genai.Client | None = None) -> str:
    content = fetch_article_text(article['url']) or ''
    if len(content) < 100:
        content = f"{article['title']}\n{article['description']}"

    template = prompt_template or RESEARCHER_PROMPT_TEMPLATE
    try:
        prompt = template.format(
            domain_description=domain_description,
            jargon_rules_block=_jargon_block(jargon),
        )
    except (KeyError, IndexError) as e:
        log.warning(f'[Researcher] Custom prompt formatlashda xato ({e}) — standart promptga qaytildi')
        prompt = RESEARCHER_PROMPT_TEMPLATE.format(
            domain_description=domain_description,
            jargon_rules_block=_jargon_block(jargon),
        )
    result = groq_call(
        prompt,
        f"Analyze this {domain_description} news:\n\nHEADLINE: {article['title']}\nCONTENT: {content[:2200]}",
        temperature=0.2, max_tokens=450,
        client=client,
    )
    log.info(f'[Researcher] ✓ {article["title"][:50]}')
    return result


# ── Agent 2: Writer (STATIC qism — format/uslub qoidalari. DINAMIK
# qism — soha, kontent turlari, emoji, taxalluslar, atamalar, kanal,
# uslub — barchasi DB'dan {placeholder} orqali quyiladi) ───────────
WRITER_PROMPT_TEMPLATE = """Sen {channel_tag} Telegram kanali uchun professional {domain_description} muharriri va jurnalistisan.

VAZIFA

Berilgan ma'lumotlardan qisqa, aniq va ishonchli yangilik yarat.
Uslub: {tone}.

ASOSIY QOIDALAR

- Faqat berilgan faktlardan foydalan.
- Hech qachon ma'lumot to'qib chiqma.
- Taxminni fakt sifatida yozma.
- Mish-mishni rasmiy yangilik sifatida ko'rsatma.
- Sonlar, sanalar va statistikalarni o'zgartirma.
- Eng muhim ma'lumot birinchi paragrafda bo'lsin.
- Professional jurnalistika uslubida yoz.
- Telegram uchun o'qilishi qulay format ishlat.
- Sun'iy iboralar va ortiqcha gaplardan qoch.
- Agar eng muhim faktni 15 ta so'z ichida aytish mumkin bo'lsa, uni birinchi jumlada ayt.

YANGILIK TURLARI

{content_types_block}

BREAKING

Faqat juda muhim, kutilmagan yoki og'irligi yuqori yangiliklarda ishlat.

EMOJI

{emoji_block}

SARLAVHA

- Maksimum 8 so'z
- Qisqa va kuchli
- Clickbait yo'q
- Faktga asoslangan
- Senga "SARLAVHA:" nomi bilan berilgan matn — bu manbaning ASL (ko'pincha ingliz tilidagi) sarlavhasi, faqat mazmunni tushunish uchun berilgan
- Uni SO'ZMA-SO'Z yoki QISMAN ko'chirish QATʼIYAN TAQIQLANADI
- O'zing FAKTLAR asosida to'liq YANGI, original o'zbekcha sarlavha yoz
- Sarlavhada bitta ham ingliz so'zi yoki iborasi bo'lmasligi kerak (nomlardan tashqari)

TAXALLUSLAR

{nicknames_block}

MAXSUS ATAMALAR

{jargon_block}

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

{channel_tag}

FORMAT TALABLARI

- Sarlavhadan keyin bitta bo'sh qator.
- Har bir paragraf orasida bitta bo'sh qator.
- Har bir paragraf 1–2 jumladan iborat bo'lsin.
- Uzun matn bloklari yaratma.
- O'qilishi oson bo'lsin.

Natijada faqat tayyor Telegram post qaytar.
Hech qanday izoh yozma.
Hech qanday markdown ishlatma."""


def writer_agent(article: dict, facts: str, nicknames: dict, channel_tag: str, tone: str,
                  domain_description: str, content_types: list, emoji_legend: dict,
                  jargon: dict, prompt_template: str | None = None,
                  client: genai.Client | None = None) -> str:
    template = prompt_template or WRITER_PROMPT_TEMPLATE
    fmt_kwargs = dict(
        channel_tag=channel_tag,
        tone=tone,
        domain_description=domain_description,
        nicknames_block=_nicknames_block(nicknames),
        content_types_block=_content_types_block(content_types),
        emoji_block=_emoji_block(emoji_legend),
        jargon_block=_jargon_block(jargon, empty_text="(maxsus atamalar berilmagan)"),
    )
    try:
        prompt = template.format(**fmt_kwargs)
    except (KeyError, IndexError) as e:
        log.warning(f'[Writer] Custom prompt formatlashda xato ({e}) — standart promptga qaytildi')
        prompt = WRITER_PROMPT_TEMPLATE.format(**fmt_kwargs)
    result = groq_call(
        prompt,
        f"Yangilik yoz:\n\nSARLAVHA: {article['title']}\nFAKTLAR:\n{facts}\n\nFaqat postni yoz:",
        temperature=0.5, max_tokens=700,
        client=client,
    )
    log.info(f'[Writer] ✓ {len(result)} belgi')
    return result


# ── Agent 3: Editor (to'liq STATIC — sifat nazorati qoidalari hech
# qachon loyihadan-loyihaga o'zgarmaydi, faqat kanal nomi quyiladi) ──
EDITOR_PROMPT_TEMPLATE = """Sen qattiq o'zbek muharrirsan. Postni tekshir:

1. Sarlavha VA matn 100% o'zbek tilidami? (Nomlardan tashqari BITTA HAM ingliz so'z yoki ibora bo'lmasligi kerak — bo'lsa, bu jiddiy xato, REJECTED qil)
2. Sarlavhadan keyin bo'sh qator bormi?
3. Har paragraf orasida bo'sh qator bormi?
4. Har paragraf 1-2 jumladan iborat?
5. Markdown belgilari yo'qmi (* _ [ ] **)?
6. O'ylab topilgan fakt yo'qmi?
7. {channel_tag} bilan tugadimi?
8. Sarlavha 8 so'zdan oshmaydimi?

Agar HAMMA tekshiruvdan o'tsa: APPROVED yoz
Agar muammo bo'lsa: REJECTED: [sabab] yoz, keyin tuzatilgan versiyani FIXED: dan keyin yoz"""


def editor_agent(post: str, title: str, channel_tag: str,
                  prompt_template: str | None = None,
                  client: genai.Client | None = None) -> str:
    template = prompt_template or EDITOR_PROMPT_TEMPLATE
    try:
        prompt = template.format(channel_tag=channel_tag)
    except (KeyError, IndexError) as e:
        log.warning(f'[Editor] Custom prompt formatlashda xato ({e}) — standart promptga qaytildi')
        prompt = EDITOR_PROMPT_TEMPLATE.format(channel_tag=channel_tag)
    result = groq_call(
        prompt,
        f"Review this Uzbek post about: {title}\n\nPOST:\n{post}",
        temperature=0.2, max_tokens=800,
        client=client,
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


# ── Pipeline ──────────────────────────────────────────────
def generate_post(article: dict, project_id: int) -> str:
    """Berilgan loyiha (project_id) uchun DB'dagi joriy workflow config'ni
    o'qib, shu asosda post yaratadi. Config topilmasa (masalan hali
    seed qilinmagan yoki hali sozlanmagan bo'lsa), DEFAULT_* qiymatlarga
    (Ingliz Futboli uchun) qaytadi — bu faqat oraliq fallback, yangi
    loyiha uchun Dashboard'dan o'ziga xos qiymatlar kiritilishi kerak."""
    config = database.get_workflow_config(project_id)
    terminology = config.get('terminology') or DEFAULT_TERMINOLOGY
    nicknames = config.get('nicknames') or DEFAULT_NICKNAMES
    channel_tag = config.get('channel_tag') or DEFAULT_CHANNEL_TAG
    tone = config.get('tone') or DEFAULT_TONE
    domain_description = config.get('domain_description') or DEFAULT_DOMAIN_DESCRIPTION
    content_types = config.get('content_types') or DEFAULT_CONTENT_TYPES
    jargon = config.get('jargon') or DEFAULT_JARGON
    emoji_legend = config.get('emoji_legend') or DEFAULT_EMOJI_LEGEND

    # Dashboard'dagi "Prompts" bo'limidan tahrirlangan bo'lsa, shu custom
    # promptlar ishlatiladi (har biri mustaqil — faqat bittasi tahrirlangan
    # bo'lishi ham mumkin). Bo'lmasa standart (kod ichidagi) promptga qaytadi.
    prompts = config.get('prompts') or {}
    researcher_prompt = prompts.get('researcher') or None
    writer_prompt = prompts.get('writer') or None
    editor_prompt = prompts.get('editor') or None

    # Loyihaning o'z Gemini API kaliti bo'lsa, shu ishlatiladi (boshqa
    # loyihalarning kunlik RPD kvotasiga umuman ta'sir qilmaydi). Bo'lmasa
    # global (asosiy) kalitga qaytadi.
    client = get_gemini_client(config.get('gemini_api_key'))

    log.info(f'[Pipeline] Boshlandi (project_id={project_id}): {article["title"][:60]}')

    facts = researcher_agent(article, domain_description, jargon, researcher_prompt, client=client)
    raw_post = writer_agent(
        article, facts, nicknames, channel_tag, tone,
        domain_description, content_types, emoji_legend, jargon,
        writer_prompt, client=client,
    )
    edited = editor_agent(raw_post, article['title'], channel_tag, editor_prompt, client=client)

    post = ensure_channel_tag(edited, channel_tag)
    ok, reason = validate_post(post)
    if not ok:
        log.warning(f'[Validator] Rad: {reason} — original post qaytarildi')
        post = ensure_channel_tag(raw_post, channel_tag)

    # AI ba'zan <br> kabi HTML teglarini yozib qo'yadi (Telegram HTML
    # parse-mode uslubini "eslab qolgani" bo'lsa kerak). Buni faqat
    # kanalga yuborish paytida emas, DARHOL shu yerda tozalaymiz — shunda
    # DB'da saqlanadigan va Dashboard'da ko'rinadigan matn ham har doim
    # toza bo'ladi (<br> -> yangi qator).
    post = sanitize_telegram_html(post)

    return apply_names(post, terminology)
