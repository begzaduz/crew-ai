"""
Bir martalik skript — Liverpool.asia loyihasining Knowledge Base
maydonlarini (terminologiya, taxalluslar, kanal yorlig'i, uslub, soha
tavsifi) to'ldiradi. Dashboard'da qo'lda bosib yurish shart emas.

ISHGA TUSHIRISH (kompyuterda, repo papkasida turib):
    railway run python fill_liverpool_config.py

Xavfsiz: faqat 'liverpool-asia' slug'iga tegishli loyihaga yozadi,
boshqa loyihalarga (Ingliz Futboli va h.k.) tegmaydi. Agar allaqachon
to'ldirilgan maydon bo'lsa, bu skript uni USHBU qiymatlar bilan
ALMASHTIRADI (patch, to'liq o'chirish emas — boshqa kalitlarga tegmaydi).
"""
import database
from workflows.rss_news import DEFAULT_TERMINOLOGY, DEFAULT_NICKNAMES

PROJECT_SLUG = 'liverpool-asia'  # Agar Dashboard'dagi slug boshqacha bo'lsa, shu yerni o'zgartiring

# Ingliz Premier-liga uchun umumiy terminologiya (allaqachon sinovdan
# o'tgan) + Liverpool'ga tegishli qo'shimcha nomlar.
TERMINOLOGY = dict(DEFAULT_TERMINOLOGY)
TERMINOLOGY.update({
    'Anfield': 'Enfild',
    'Jurgen Klopp': 'Yurgen Klopp',
    'Klopp': 'Klopp',
    'Arne Slot': 'Arne Slot',
    'Alisson Becker': 'Alisson Beker',
    'Alisson': 'Alisson',
    'Trent Alexander-Arnold': 'Trent Aleksandr-Arnold',
    'Andy Robertson': 'Endi Robertson',
    'Darwin Nunez': 'Darvin Nunes',
    'Luis Diaz': 'Luis Diaz',
    'Dominik Szoboszlai': 'Dominik Soboslai',
})

NICKNAMES = dict(DEFAULT_NICKNAMES)  # 'Liverpool': 'qizillar' allaqachon bor

CHANNEL_TAG = '@lfctest'  # <-- Kerak bo'lsa shu yerni o'zgartiring (real kanal handle'i)

TONE = "professional sport jurnalistikasi uslubida, Liverpool muxlislariga qaratilgan, hissiy va qiziqarli"

DOMAIN_DESCRIPTION = "Liverpool FC va Premier-liga"


def main():
    database.init_db()
    project = database.get_project_by_slug(PROJECT_SLUG)
    if not project:
        print(f"XATO: '{PROJECT_SLUG}' slug'i bilan loyiha topilmadi.")
        print("Mavjud loyihalar:")
        for p in database.list_projects():
            print(f"  - {p['slug']} ({p['name']})")
        return

    pid = project['id']
    print(f"Loyiha topildi: {project['name']} (id={pid})")

    result = database.update_workflow_config(pid, {
        'terminology': TERMINOLOGY,
        'nicknames': NICKNAMES,
        'channel_tag': CHANNEL_TAG,
        'tone': TONE,
        'domain_description': DOMAIN_DESCRIPTION,
    })

    print("Saqlandi. Yangi config kalitlari:", list(result.keys()))
    print(f"  terminology: {len(result.get('terminology', {}))} ta atama")
    print(f"  nicknames: {len(result.get('nicknames', {}))} ta taxallus")
    print(f"  channel_tag: {result.get('channel_tag')}")
    print(f"  tone: {result.get('tone')}")
    print(f"  domain_description: {result.get('domain_description')}")


if __name__ == '__main__':
    main()
