"""telegram_utils.py uchun testlar — asosan sanitize_telegram_html()
regressiyasi: Gemini ba'zan '<br>' o'rniga orasida bo'shliq bilan
'< br >' kabi variant chiqarib qo'yishi kuzatildi (Dashboard'da xom
teg ko'rinib qolgan edi), shuning uchun bo'shliqli variantlar ham
qamrab olinishi SHART."""
from telegram_utils import sanitize_telegram_html


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

    def test_empty_string_returns_as_is(self):
        assert sanitize_telegram_html('') == ''
