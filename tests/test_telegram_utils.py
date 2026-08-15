"""telegram_utils.py uchun testlar — asosan sanitize_telegram_html()
regressiyasi: Gemini ba'zan '<br>' o'rniga orasida bo'shliq bilan
'< br >' kabi variant chiqarib qo'yishi kuzatildi (Dashboard'da xom
teg ko'rinib qolgan edi), shuning uchun bo'shliqli variantlar ham
qamrab olinishi SHART."""
from telegram_utils import sanitize_telegram_html, _clean_post


class TestSanitizeBrTag:
    def test_plain_br(self):
        assert sanitize_telegram_html('a<br>b') == 'a\nb'

    def test_self_closing_br(self):
        assert sanitize_telegram_html('a<br/>b') == 'a\nb'

    def test_self_closing_br_with_space(self):
        assert sanitize_telegram_html('a<br />b') == 'a\nb'

    def test_br_with_space_after_lt(self):
        assert sanitize_telegram_html('a< br >b') == 'a\nb'

    def test_br_with_space_and_self_closing(self):
        assert sanitize_telegram_html('a< br/ >b') == 'a\nb'

    def test_uppercase_br(self):
        assert sanitize_telegram_html('a<BR>b') == 'a\nb'

    def test_multiple_br_in_a_row(self):
        assert sanitize_telegram_html('a< br >< br >b') == 'a\n\nb'

    def test_real_world_reported_case(self):
        raw = "Arsenal Cristian Romero bo'yicha surishtiruv o'tkazdi< br >< br >To'pchilar gap."
        result = sanitize_telegram_html(raw)
        assert '<' not in result and '>' not in result
        assert "surishtiruv o'tkazdi" in result
        assert "To'pchilar gap." in result


class TestSanitizeDisallowedTags:
    def test_strips_div_keeps_text(self):
        assert sanitize_telegram_html('<div>matn</div>') == 'matn'

    def test_strips_disallowed_tag_with_space_after_lt(self):
        assert sanitize_telegram_html('< div >matn< /div >') == 'matn'

    def test_keeps_allowed_bold_tag(self):
        assert sanitize_telegram_html('<b>matn</b>') == '<b>matn</b>'

    def test_keeps_allowed_blockquote_tag(self):
        # MUHIM: Review Queue'dagi 'Iqtibos' (Quote) formatlash tugmasi
        # shu tegdan foydalanadi — sanitize uni olib tashlamasligi kerak.
        assert sanitize_telegram_html('<blockquote>iqtibos matni</blockquote>') == '<blockquote>iqtibos matni</blockquote>'

    def test_empty_string_returns_as_is(self):
        assert sanitize_telegram_html('') == ''


class TestTgChannelBotTokenRouting:
    """MUHIM: har loyiha o'z Telegram bot tokenini DB orqali sozlashi
    mumkin (gemini_api_key bilan bir xil naqsh) — kodga hech qanday bot
    qattiq bog'lanmasligi kerak."""

    def test_uses_project_bot_token_when_given(self, monkeypatch):
        import telegram_utils
        captured = {}

        class FakeResponse:
            def json(self):
                return {'ok': True}

        def fake_post(url, json=None, timeout=None):
            captured['url'] = url
            return FakeResponse()

        monkeypatch.setattr(telegram_utils.requests, 'post', fake_post)
        telegram_utils.tg_channel('Test post text here', chat_id='@SomeChannel', bot_token='111:CUSTOMTOKEN')
        assert '/bot111:CUSTOMTOKEN/' in captured['url']

    def test_falls_back_to_global_token_when_not_given(self, monkeypatch):
        import telegram_utils
        captured = {}

        class FakeResponse:
            def json(self):
                return {'ok': True}

        def fake_post(url, json=None, timeout=None):
            captured['url'] = url
            return FakeResponse()

        monkeypatch.setattr(telegram_utils.requests, 'post', fake_post)
        telegram_utils.tg_channel('Test post text here', chat_id='@SomeChannel')
        assert f'/bot{telegram_utils.TOKEN}/' in captured['url']


class TestCleanPostBoldTitle:
    """MUHIM: sarlavhani qalin qilish ilgari kodga qattiq yozilgan edi
    (har doim yoqiq) — endi bold_title parametri orqali (loyihaning
    workflow config'idagi 'bold_title' qiymatidan) DB-driven boshqariladi."""

    def test_bold_title_true_wraps_first_line(self):
        result = _clean_post('Sarlavha matni\n\nIkkinchi paragraf.', bold_title=True)
        assert result.startswith('<b>Sarlavha matni</b>')

    def test_bold_title_false_leaves_first_line_plain(self):
        result = _clean_post('Sarlavha matni\n\nIkkinchi paragraf.', bold_title=False)
        assert result.startswith('Sarlavha matni')
        assert '<b>' not in result

    def test_bold_title_default_is_true(self):
        # Parametr berilmasa — orqaga moslik (avvalgi xatti-harakat).
        result = _clean_post('Sarlavha matni\n\nMatn.')
        assert result.startswith('<b>Sarlavha matni</b>')

    def test_bold_title_false_still_sanitizes_html(self):
        # bold_title=False bo'lsa ham, ruxsat etilmagan teglar (masalan <br>)
        # baribir tozalanishi kerak — faqat bold-wrap o'chadi.
        result = _clean_post('Sarlavha< br >davomi', bold_title=False)
        assert '<br' not in result
        assert result == 'Sarlavha\ndavomi'

    def test_bold_title_preserves_leading_emoji_outside_bold(self):
        result = _clean_post('🚨 Muhim xabar\n\nMatn.', bold_title=True)
        assert result.startswith('🚨 <b>Muhim xabar</b>')
