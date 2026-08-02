"""Pytest umumiy sozlamalari.

Barcha modullar (config.py orqali) TOKEN/GEMINI_KEY/ADMIN_IDS/
WEBHOOK_SECRET/DASHBOARD_PASSWORD env o'zgaruvchilarini talab qiladi.
Testlarda haqiqiy qiymatlar kerak emas — shuning uchun bu fayl
har qanday test modul import qilinishidan OLDIN soxta qiymatlarni
o'rnatadi.

DATABASE_URL: database.py import vaqtida haqiqiy Postgres'ga ulanadi
(ThreadedConnectionPool). Shuning uchun testlar HAQIQIY (lekin test
uchun alohida) Postgres'ga muhtoj — mock/stub ishlatilmaydi, chunki bu
production xatti-harakatidan chetlashtiradi (aynan shu farq bugun
'workflow_type'/'data_sources' ustunlari yetishmasligi bug'ini
yashirib turgan edi). CI'da bu GitHub Actions'ning 'postgres' service
konteyneri orqali, lokal ishlab chiqishda esa DATABASE_URL env
o'zgaruvchisini qo'lda export qilib beriladi.
"""
import os
import sys

# Repo ildizini sys.path'ga qo'shamiz — bu conftest.py'ning joylashgan
# joyidan mustaqil hisoblanadi (tests/'ning bir daraja tepasi). MUHIM:
# buni ATAYLAB shu yerda, aniq yo'l bilan qilamiz, chunki pytest'ning
# "bare" chaqiruvi ('pytest tests/') va 'python -m pytest' chaqiruvi
# sys.path'ni har xil sozlaydi — birinchisida repo ildizi (database.py,
# main.py va h.k. joylashgan joy) import qilinmay qoladi.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('TOKEN', 'test-token')
os.environ.setdefault('GEMINI_KEY', 'test-gemini-key')
os.environ.setdefault('ADMIN_IDS', '123456')
os.environ.setdefault('WEBHOOK_SECRET', 'test-webhook-secret')
os.environ.setdefault('DASHBOARD_PASSWORD', 'test-dashboard-password')
os.environ.setdefault('CHANNEL', '@TestChannel')
os.environ.setdefault(
    'DATABASE_URL', 'postgresql://postgres:testpass@localhost:5432/testdb'
)

import pytest  # noqa: E402
import database  # noqa: E402


@pytest.fixture(scope='session', autouse=True)
def _init_test_db():
    """Test sessiyasi boshida jadvallarni tozalab, database.init_db()
    orqali QAYTADAN yaratadi — bu production'da server ishga tushganda
    sodir bo'ladigan aynan shu jarayon (mock emas). Shu tufayli sxema
    migratsiyalaridagi xatolar (masalan 'workflow_type' ustuni
    yetishmasligi) haqiqiy test orqali ushlanadi."""
    conn = database._get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                DROP TABLE IF EXISTS daily_api_usage, processed_articles,
                published_posts, projects, workflows, data_sources,
                assets, reviews CASCADE
            ''')
        conn.commit()
    finally:
        database._put_conn(conn)
    database.init_db()
    yield


@pytest.fixture()
def clean_db(_init_test_db):
    """Har test OLDIN barcha jadval qatorlarini tozalaydi (sxemaga
    tegmaydi) — testlar bir-biriga aralashmasligi uchun."""
    conn = database._get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                TRUNCATE daily_api_usage, processed_articles,
                published_posts, projects, workflows, data_sources,
                assets, reviews RESTART IDENTITY CASCADE
            ''')
        conn.commit()
    finally:
        database._put_conn(conn)
    yield
