"""workflows/rss_news.py uchun testlar — asosiy e'tibor bugungi
universallashtirish ishiga: promptlar futbolga qattiq yozilmagan
ekanini, va istalgan sohaga to'g'ri moslashishini tasdiqlash."""
import workflows.rss_news as w


class TestPromptBlocks:
    def test_jargon_block_formats_dict(self):
        result = w._jargon_block({'survival': 'qolish'})
        assert '"survival" = "qolish"' in result

    def test_jargon_block_empty_returns_empty_text(self):
        assert w._jargon_block({}) == ''
        assert w._jargon_block({}, empty_text='(yo\'q)') == "(yo'q)"

    def test_content_types_block_formats_list(self):
        result = w._content_types_block(['TRANSFER', 'INJURY'])
        assert '- TRANSFER' in result
        assert '- INJURY' in result

    def test_content_types_block_empty_has_sensible_fallback(self):
        result = w._content_types_block([])
        assert 'turlar belgilanmagan' in result

    def test_emoji_block_formats_dict(self):
        result = w._emoji_block({'🚨': 'Muhim yangilik'})
        assert '🚨 Muhim yangilik' in result

    def test_emoji_block_empty_has_generic_fallback(self):
        result = w._emoji_block({})
        assert result  # bo'sh emas, umumiy standart to'plam qaytadi

    def test_nicknames_block_empty_has_sensible_fallback(self):
        result = w._nicknames_block({})
        assert 'taxalluslar berilmagan' in result


class TestFootballDefaultsBackwardCompatibility:
    """'Ingliz Futboli' loyihasi universallashtirishdan keyin ham bir
    xilda ishlashi kerak (orqaga to'liq moslik)."""

    def test_researcher_prompt_renders_with_football_defaults(self):
        prompt = w.RESEARCHER_PROMPT_TEMPLATE.format(
            domain_description=w.DEFAULT_DOMAIN_DESCRIPTION,
            jargon_rules_block=w._jargon_block(w.DEFAULT_JARGON),
        )
        assert 'Premier League football' in prompt
        assert '"survival" = "qolish"' in prompt

    def test_writer_prompt_renders_with_football_defaults(self):
        prompt = w.WRITER_PROMPT_TEMPLATE.format(
            channel_tag='@Inglizfutbol',
            tone=w.DEFAULT_TONE,
            domain_description=w.DEFAULT_DOMAIN_DESCRIPTION,
            nicknames_block=w._nicknames_block(w.DEFAULT_NICKNAMES),
            content_types_block=w._content_types_block(w.DEFAULT_CONTENT_TYPES),
            emoji_block=w._emoji_block(w.DEFAULT_EMOJI_LEGEND),
            jargon_block=w._jargon_block(w.DEFAULT_JARGON, empty_text="(yo'q)"),
        )
        assert 'TRANSFER' in prompt
        assert "to'pchilar" in prompt


class TestNonFootballDomain:
    """Universallashtirishning asosiy maqsadi: futboldan mutlaqo boshqa
    soha bilan ishlashi kerak, hech qanday futbol so'zi 'sizib
    chiqmasligi' kerak."""

    TOY_DOMAIN = "kids' toy industry"
    TOY_CONTENT_TYPES = ['PRODUCT_LAUNCH', 'SAFETY_RECALL', 'PARTNERSHIP']
    TOY_JARGON = {'recall': "chaqirib olish"}
    TOY_EMOJI = {'e1': 'Yangi mahsulot'}

    def test_researcher_prompt_has_no_football_leakage(self):
        prompt = w.RESEARCHER_PROMPT_TEMPLATE.format(
            domain_description=self.TOY_DOMAIN,
            jargon_rules_block=w._jargon_block(self.TOY_JARGON),
        )
        assert 'football' not in prompt.lower()
        assert self.TOY_DOMAIN in prompt

    def test_writer_prompt_has_no_football_leakage(self):
        prompt = w.WRITER_PROMPT_TEMPLATE.format(
            channel_tag='@ToyNewsUZ',
            tone='quvnoq va oilaviy uslubda',
            domain_description=self.TOY_DOMAIN,
            nicknames_block=w._nicknames_block({}),
            content_types_block=w._content_types_block(self.TOY_CONTENT_TYPES),
            emoji_block=w._emoji_block(self.TOY_EMOJI),
            jargon_block=w._jargon_block(self.TOY_JARGON, empty_text="(yo'q)"),
        )
        assert 'TRANSFER' not in prompt
        assert "to'pchilar" not in prompt
        assert 'PRODUCT_LAUNCH' in prompt

    def test_empty_config_does_not_crash(self):
        # Yangi loyiha hali sozlanmagan bo'lsa ham (bo'sh config),
        # promptlar xatosiz yig'ilishi kerak.
        prompt = w.WRITER_PROMPT_TEMPLATE.format(
            channel_tag='@Test', tone='neytral', domain_description='umumiy',
            nicknames_block=w._nicknames_block({}),
            content_types_block=w._content_types_block([]),
            emoji_block=w._emoji_block({}),
            jargon_block=w._jargon_block({}, empty_text="(yo'q)"),
        )
        assert prompt  # xato bermadi


class TestValidatePost:
    def test_too_short_rejected(self):
        ok, reason = w.validate_post('qisqa')
        assert not ok

    def test_too_long_rejected(self):
        ok, reason = w.validate_post('x' * 1001)
        assert not ok
        assert '1000' in reason

    def test_markdown_rejected(self):
        ok, reason = w.validate_post('Bu **muhim** yangilik ' + 'x' * 50)
        assert not ok

    def test_valid_post_accepted(self):
        ok, reason = w.validate_post('Bu oddiy, to\'g\'ri formatdagi post matni. ' * 3)
        assert ok


class TestEnsureChannelTag:
    def test_adds_tag_if_missing(self):
        result = w.ensure_channel_tag('Post matni', '@Kanal')
        assert result.endswith('@Kanal')

    def test_does_not_duplicate_existing_tag(self):
        result = w.ensure_channel_tag('Post matni\n\n@Kanal', '@Kanal')
        assert result.count('@Kanal') == 1


class TestApplyNames:
    def test_replaces_whole_words_only(self):
        result = w.apply_names('Man City won today', {'Man City': 'Manchester Siti'})
        assert result == 'Manchester Siti won today'

    def test_does_not_replace_partial_word_matches(self):
        # "Man" so'zi "Manchester" ichida qisman mos kelmasligi kerak
        result = w.apply_names('Manager spoke today', {'Man': 'ODAM'})
        assert result == 'Manager spoke today'
