"""image_search.py uchun testlar — Google Custom Search API'ga haqiqiy
tarmoq so'rovi yuborilmaydi (mock qilinadi)."""
from unittest.mock import Mock, patch

import image_search


class TestIsConfigured:
    def test_false_when_keys_missing(self):
        with patch.object(image_search, 'GOOGLE_SEARCH_API_KEY', ''), \
             patch.object(image_search, 'GOOGLE_SEARCH_CX', ''):
            assert image_search.is_configured() is False

    def test_true_when_both_keys_present(self):
        with patch.object(image_search, 'GOOGLE_SEARCH_API_KEY', 'key'), \
             patch.object(image_search, 'GOOGLE_SEARCH_CX', 'cx'):
            assert image_search.is_configured() is True


class TestSearchImages:
    def test_returns_none_when_not_configured(self):
        with patch.object(image_search, 'GOOGLE_SEARCH_API_KEY', ''), \
             patch.object(image_search, 'GOOGLE_SEARCH_CX', ''):
            assert image_search.search_images('arsenal') is None

    def test_empty_query_returns_empty_list(self):
        with patch.object(image_search, 'GOOGLE_SEARCH_API_KEY', 'key'), \
             patch.object(image_search, 'GOOGLE_SEARCH_CX', 'cx'):
            assert image_search.search_images('   ') == []

    def test_parses_google_response(self):
        fake_response = Mock()
        fake_response.raise_for_status = Mock()
        fake_response.json.return_value = {
            'items': [
                {
                    'link': 'https://example.com/photo.jpg',
                    'title': 'A photo',
                    'image': {'thumbnailLink': 'https://example.com/thumb.jpg'},
                },
                {'link': '', 'title': 'no link, skipped'},
            ]
        }
        with patch.object(image_search, 'GOOGLE_SEARCH_API_KEY', 'key'), \
             patch.object(image_search, 'GOOGLE_SEARCH_CX', 'cx'), \
             patch.object(image_search.requests, 'get', return_value=fake_response):
            results = image_search.search_images('arsenal stadium')
        assert results == [{
            'url': 'https://example.com/photo.jpg',
            'thumbnail': 'https://example.com/thumb.jpg',
            'title': 'A photo',
        }]

    def test_network_error_returns_none(self):
        with patch.object(image_search, 'GOOGLE_SEARCH_API_KEY', 'key'), \
             patch.object(image_search, 'GOOGLE_SEARCH_CX', 'cx'), \
             patch.object(image_search.requests, 'get', side_effect=RuntimeError('boom')):
            assert image_search.search_images('arsenal') is None
