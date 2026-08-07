"""studio_api.py uchun testlar."""
from unittest.mock import patch

import database
import studio_api


class TestCreateProject:
    def test_generates_slug_from_name(self, clean_db):
        status, payload = studio_api.create_project(None, {'name': "Toy Company O'zbekiston"})
        assert status == 200
        assert payload['slug'] == 'toy-company-o-zbekiston'

    def test_empty_name_rejected(self, clean_db):
        status, payload = studio_api.create_project(None, {'name': ''})
        assert status == 400

    def test_custom_slug_takes_priority(self, clean_db):
        status, payload = studio_api.create_project(None, {'name': 'Test', 'slug': 'custom-slug'})
        assert payload['slug'] == 'custom-slug'

    def test_list_projects_returns_created_ones(self, clean_db):
        studio_api.create_project(None, {'name': 'Loyiha 1'})
        studio_api.create_project(None, {'name': 'Loyiha 2'})
        status, payload = studio_api.list_projects(None, {})
        assert status == 200
        assert len(payload) == 2


class TestApproveAssetChannelRouting:
    """MUHIM: postni tasdiqlaganda, u so'rov qaysi loyihadan kelganidan
    QAT'I NAZAR, postning O'Z EGASI bo'lgan loyihaning Telegram
    kanaliga yuborilishi kerak (bitta bot — bir nechta kanal)."""

    def test_approve_uses_asset_owner_project_channel(self, clean_db):
        project = database.get_or_create_project('toy-co', 'Toy Company')
        database.set_workflow_config(project['id'], {'telegram_channel_id': '@ToyCompanyChannel'})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Test post content that is long enough to pass validation checks here.',
            score=0,
        )

        captured = {}

        def fake_tg_channel(text, image_url=None, chat_id=None):
            captured['chat_id'] = chat_id
            return {'ok': True}

        with patch.object(studio_api.telegram_utils, 'tg_channel', side_effect=fake_tg_channel):
            status, payload = studio_api.approve_asset({'id': asset['id']})

        assert status == 200
        assert captured['chat_id'] == '@ToyCompanyChannel'

    def test_approve_falls_back_to_none_when_no_channel_configured(self, clean_db):
        # telegram_channel_id sozlanmagan bo'lsa, tg_channel()ning o'z
        # global CHANNEL fallback'iga tayanamiz (chat_id=None uzatiladi).
        project = database.get_or_create_project('unconfigured', 'Sozlanmagan')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Test post content that is long enough to pass validation checks here.',
            score=0,
        )

        captured = {}

        def fake_tg_channel(text, image_url=None, chat_id=None):
            captured['chat_id'] = chat_id
            return {'ok': True}

        with patch.object(studio_api.telegram_utils, 'tg_channel', side_effect=fake_tg_channel):
            studio_api.approve_asset({'id': asset['id']})

        assert captured['chat_id'] is None

    def test_cannot_approve_already_published_asset(self, clean_db):
        project = database.get_or_create_project('dup-approve', 'Dup Test')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Content long enough to pass validation checks here for sure.',
            score=0,
        )
        database.mark_asset_published(asset['id'])
        status, payload = studio_api.approve_asset({'id': asset['id']})
        assert status == 400


class TestListAssetsSelfHeal:
    """MUHIM: sanitize_telegram_html() qo'shilishidan OLDIN yaratilgan
    eski draft'larda xom '<br>' teglari qolib ketgan bo'lishi mumkin edi.
    list_assets() endi HAR O'QISHDA buni tozalaydi va DB'ga ham qaytarib
    yozadi — Dashboard'da boshqa hech qachon xom teg ko'rinmasligi kerak."""

    def test_raw_br_tag_is_cleaned_on_read(self, clean_db):
        project = database.get_or_create_project('br-heal-test', 'Br Heal Test')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Sarlavha matni<br><br>Ikkinchi paragraf matni.',
            score=0,
        )
        status, payload = studio_api.list_assets(project['id'], {'status': 'draft'})
        assert status == 200
        cleaned = next(a for a in payload if a['id'] == asset['id'])
        assert '<br>' not in cleaned['content']
        assert 'Ikkinchi paragraf' in cleaned['content']

        persisted = database.get_asset(asset['id'])
        assert '<br>' not in persisted['content']

    def test_already_clean_content_is_left_untouched(self, clean_db):
        project = database.get_or_create_project('br-heal-test2', 'Br Heal Test 2')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Toza matn, hech qanday teg yoq.',
            score=0,
        )
        status, payload = studio_api.list_assets(project['id'], {'status': 'draft'})
        cleaned = next(a for a in payload if a['id'] == asset['id'])
        assert cleaned['content'] == 'Toza matn, hech qanday teg yoq.'
    def test_rejects_unknown_keys_only(self, clean_db):
        project = database.get_or_create_project('cfg-test', 'Config Test')
        status, payload = studio_api.update_config(project['id'], {'totally_unknown_key': 'x'})
        assert status == 400

    def test_rejects_wrong_type_for_content_types(self, clean_db):
        project = database.get_or_create_project('cfg-test2', 'Config Test 2')
        status, payload = studio_api.update_config(project['id'], {'content_types': 'should-be-a-list'})
        assert status == 400

    def test_accepts_valid_new_fields(self, clean_db):
        project = database.get_or_create_project('cfg-test3', 'Config Test 3')
        status, payload = studio_api.update_config(project['id'], {
            'domain_description': 'toys',
            'content_types': ['LAUNCH'],
            'jargon': {'a': 'b'},
            'emoji_legend': {'x': 'y'},
            'telegram_channel_id': '@Test',
        })
        assert status == 200


class TestAutoPublishConfig:
    def test_auto_publish_coerced_to_bool(self, clean_db):
        project = database.get_or_create_project('auto-pub-1', 'Auto Publish 1')
        status, payload = studio_api.update_config(project['id'], {'auto_publish': True})
        assert status == 200
        assert database.get_workflow_config(project['id'])['auto_publish'] is True

    def test_auto_publish_defaults_false_in_stats(self, clean_db):
        project = database.get_or_create_project('auto-pub-2', 'Auto Publish 2')
        status, payload = studio_api.get_dashboard_stats(project['id'])
        assert status == 200
        assert payload['auto_publish'] is False

    def test_auto_publish_reflected_in_stats_after_enabling(self, clean_db):
        project = database.get_or_create_project('auto-pub-3', 'Auto Publish 3')
        studio_api.update_config(project['id'], {'auto_publish': True})
        status, payload = studio_api.get_dashboard_stats(project['id'])
        assert payload['auto_publish'] is True
