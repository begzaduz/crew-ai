# Migratsiya ko'rsatmasi

## 1. Yangi fayllar (qo'shiladi, repo'ga shu holatda ko'chiriladi)

```
agents/__init__.py       (bo'sh)
agents/llm.py
agents/validators.py
agents/researcher.py
agents/writer.py
agents/editor.py
workflows/__init__.py    (bo'sh)
workflows/rss_news_vocab.py
workflows/rss_news.py
registry.py
```

## 2. O'chiriladigan fayl

```
agents.py   (eski, ildizdagi fayl — endi kerak emas, mantig'i yuqoridagi
             fayllarga taqsimlandi)
```

## 3. `api_football.py` da o'zgarish (1 qator)

Eski:
```python
from agents import apply_names
```

Yangi:
```python
from workflows.rss_news_vocab import apply_names
```

Boshqa hech narsa `api_football.py` da o'zgarmaydi — `_translate_club()` va
qolgan funksiyalar bir xil qoladi.

## 4. `main.py` da o'zgarish (2 joy)

Eski import:
```python
from agents import generate_post
```

Yangi import:
```python
from registry import get_workflow

news_workflow = get_workflow("rss_news")
```

### 4a. `auto_news_post()` ichida

Eski:
```python
post = generate_post(article)
```

Yangi:
```python
post = news_workflow.run(article)
```

### 4b. `handle_update()` ichida, qo'lda matn yuborish bo'limida

Eski:
```python
article = {'title': text, 'description': '', 'url': None, 'score': 100}
post = generate_post(article)
```

Yangi:
```python
article = {'title': text, 'description': '', 'url': None, 'score': 100}
post = news_workflow.run(article)
```

Boshqa hech narsa `main.py` da o'zgarmaydi — `tg_send`, `tg_channel`,
`_clean_post`, webhook handler, kvota logikasi, hammasi bir xil qoladi.

## 5. Tekshirish

Refaktordan keyin xatti-harakat 100% bir xil bo'lishi kerak:
- `/yangilik` buyrug'i xuddi shu postni yaratadi
- Qo'lda matn yuborish xuddi shu oqimdan o'tadi (Researcher→Writer→Editor→Validator→apply_names)
- RSS fetch, kvota hisoblash, Telegram'ga yuborish — hech biri tegilmagan

Bu — sof ichki qayta tashkil etish (behavior-preserving refactor).
Production'ga chiqarishdan oldin faqat import xatolari bo'lmasligini
tekshirish kifoya (masalan `python -c "import main"`).
