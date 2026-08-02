"""feeds.py uchun testlar — DB'ga bog'liq emas (feeds.py database'ni
import qilmaydi), shuning uchun bular eng tez ishlaydigan, sof-mantiq
testlari."""
from unittest.mock import Mock, patch

import feeds


class TestNormalizeUrl:
    """Dublikat post bug'ining tuzatilishini tasdiqlovchi testlar."""

    def test_strips_query_params(self):
        assert feeds._normalize_url(
            'https://site.com/article?utm_source=rss&utm_campaign=x'
        ) == 'https://site.com/article'

    def test_strips_fragment(self):
        assert feeds._normalize_url(
            'https://site.com/article#section2'
        ) == 'https://site.com/article'

    def test_clean_url_unchanged(self):
        assert feeds._normalize_url('https://site.com/article') == 'https://site.com/article'

    def test_empty_string(self):
        assert feeds._normalize_url('') == ''

    def test_preserves_trailing_slash(self):
        assert feeds._normalize_url(
            'https://site.com/article/?ref=twitter'
        ) == 'https://site.com/article/'


class TestScoreArticle:
    def test_premier_league_signal_required(self):
        # PL_SIGNAL_KEYWORDS'dan biri bo'lmasa, generic so'zlar ko'p
        # bo'lsa ham rad etiladi.
        score = feeds.score_article('Big transfer deal confirmed', 'A million pound contract')
        assert score == -999

    def test_blacklist_overrides_everything(self):
        # Boshqa liga so'zi (bundesliga) bo'lsa, "arsenal" so'zi bo'lsa
        # ham qat'iyan rad etiladi.
        score = feeds.score_article('Arsenal transfer news', 'Bundesliga star wanted')
        assert score == -999

    def test_valid_pl_article_scores_positive(self):
        score = feeds.score_article(
            'Arsenal confirm official transfer', 'Premier League club announce new signing'
        )
        assert score > 0

    def test_breaking_words_add_bonus(self):
        base = feeds.score_article('Arsenal transfer news', 'Premier League deal')
        breaking = feeds.score_article('Arsenal transfer news breaking', 'Premier League confirmed deal')
        assert breaking > base


class TestFetchNewsDeduplication:
    """fetch_news() darajasidagi integratsion-uslubdagi testlar (tarmoq
    so'rovlari mock qilinadi, lekin fetch_news()ning o'zi haqiqiy
    ishlaydi)."""

    def test_same_article_different_tracking_params_deduplicated(self):
        import time
        now = time.gmtime()

        class FakeFeed:
            entries = [
                {
                    'link': 'https://caughtoffside.com/exit-confirmed?utm_source=rss',
                    'title': 'Exit confirmed: Star signs Chelsea deal',
                    'summary': 'Premier League transfer news confirmed official.',
                    'published_parsed': now,
                },
                {
                    'link': 'https://caughtoffside.com/exit-confirmed?utm_source=twitter&ref=share',
                    'title': 'Exit confirmed: Star signs Chelsea deal',
                    'summary': 'Premier League transfer news confirmed official.',
                    'published_parsed': now,
                },
                {
                    'link': 'https://caughtoffside.com/exit-confirmed',
                    'title': 'Exit confirmed: Star signs Chelsea deal',
                    'summary': 'Premier League transfer news confirmed official.',
                    'published_parsed': now,
                },
            ]

        with patch.object(feeds.feedparser, 'parse', return_value=FakeFeed()):
            articles = feeds.fetch_news(['fake-feed-url'])

        assert len(articles) == 1
        assert '?' not in articles[0]['url']

    def test_empty_feed_list_returns_empty(self):
        assert feeds.fetch_news([]) == []

    def test_feed_error_does_not_crash_whole_fetch(self):
        with patch.object(feeds.feedparser, 'parse', side_effect=RuntimeError('boom')):
            articles = feeds.fetch_news(['broken-feed'])
        assert articles == []


class TestFetchArticleImage:
    """Maqola matni ichidagi rasmga ustuvorlik berish mantig'i."""

    def _mock_response(self, html):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.text = html
        return resp

    def test_prefers_body_image_over_hero(self):
        html = """
        <html><head>
        <meta property="og:image" content="https://cdn.example.com/hero/banner.jpg">
        </head><body>
        <article>
        <h1>Title</h1>
        <img src="https://cdn.example.com/hero/banner.jpg" alt="hero duplicated">
        <p>Some paragraph with enough words to count as real article content here.</p>
        <img src="https://cdn.example.com/photos/player.jpg" alt="Player photo">
        <p>Another paragraph with more descriptive content about the match today.</p>
        </article>
        </body></html>
        """
        with patch.object(feeds.requests, 'get', return_value=self._mock_response(html)):
            result = feeds.fetch_article_image('https://example.com/article')
        assert result == 'https://cdn.example.com/photos/player.jpg'

    def test_falls_back_to_hero_when_no_body_image(self):
        html = """
        <html><head>
        <meta property="og:image" content="https://cdn.example.com/hero/only.jpg">
        </head><body>
        <article><h1>Title</h1><p>Just text, no other images in this article body at all.</p></article>
        </body></html>
        """
        with patch.object(feeds.requests, 'get', return_value=self._mock_response(html)):
            result = feeds.fetch_article_image('https://example.com/article')
        assert result == 'https://cdn.example.com/hero/only.jpg'

    def test_returns_none_when_hero_is_blacklisted_and_no_body_image(self):
        html = """
        <html><head>
        <meta property="og:image" content="https://cdn.example.com/badge/generic-placeholder.jpg">
        </head><body>
        <article><h1>Title</h1><p>No images anywhere in this article body content at all.</p></article>
        </body></html>
        """
        with patch.object(feeds.requests, 'get', return_value=self._mock_response(html)):
            result = feeds.fetch_article_image('https://example.com/article')
        assert result is None

    def test_no_url_returns_none(self):
        assert feeds.fetch_article_image('') is None
        assert feeds.fetch_article_image(None) is None
