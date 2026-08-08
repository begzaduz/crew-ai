"""studio_api.py uchun testlar."""
from unittest.mock import patch

import database
import studio_api


class TestImageUploadAndSearch:
    def test_upload_image_rejects_bad_content_type(self, clean_db):
        project = database.get_or_create_project('img-up-1', 'Img Up 1')
        status, payload = studio_api.upload_image(project['id'], {
            'content_type': 'application/pdf', 'image_base64': 'YQ==',
        })
        assert status == 400

    def test_upload_image_rejects_missing_base64(self, clean_db):
        project = database.get_or_create_project('img-up-2', 'Img Up 2')
        status, payload = studio_api.upload_image(project['id'], {
            'content_type': 'image/png', 'image_base64': '',
        })
        assert status == 400

    def test_upload_image_rejects_invalid_base64(self, clean_db):
        project = database.get_or_create_project('img-up-3', 'Img Up 3')
        status, payload = studio_api.upload_image(project['id'], {
            'content_type': 'image/png', 'image_base64': 'not-valid-base64!!!',
        })
        assert status == 400

    def test_upload_image_success_returns_url(self, clean_db):
        import base64
        project = database.get_or_create_project('img-up-4', 'Img Up 4')
        b64 = base64.b64encode(b'fake-png-bytes').decode()
        with patch.object(studio_api, 'PUBLIC_BASE_URL', 'https://example.up.railway.app'):
            status, payload = studio_api.upload_image(project['id'], {
                'content_type': 'image/png', 'image_base64': b64,
            })
        assert status == 200
        assert payload['url'] == f"https://example.up.railway.app/api/image/{payload['id']}"
        stored = database.get_upload(payload['id'])
        assert bytes(stored['data']) == b'fake-png-bytes'

    def test_upload_image_strips_data_url_prefix(self, clean_db):
        import base64
        project = database.get_or_create_project('img-up-5', 'Img Up 5')
        b64 = base64.b64encode(b'abc').decode()
        status, payload = studio_api.upload_image(project['id'], {
            'content_type': 'image/jpeg', 'image_base64': f'data:image/jpeg;base64,{b64}',
        })
        assert status == 200
        assert bytes(database.get_upload(payload['id'])['data']) == b'abc'

    def test_upload_image_rejects_too_large(self, clean_db):
        import base64
        project = database.get_or_create_project('img-up-6', 'Img Up 6')
        big = base64.b64encode(b'x' * (studio_api._MAX_UPLOAD_BYTES + 1)).decode()
        status, payload = studio_api.upload_image(project['id'], {
            'content_type': 'image/png', 'image_base64': big,
        })
        assert status == 400

    def test_search_images_requires_query(self, clean_db):
        status, payload = studio_api.search_images_api(None, {'query': ''})
        assert status == 400

    def test_search_images_returns_503_when_not_configured(self, clean_db):
        with patch.object(studio_api.image_search, 'is_configured', return_value=False):
            status, payload = studio_api.search_images_api(None, {'query': 'arsenal'})
        assert status == 503

    def test_search_images_returns_results(self, clean_db):
        fake_results = [{'url': 'https://x.com/a.jpg', 'thumbnail': 'https://x.com/t.jpg', 'title': 'A'}]
        with patch.object(studio_api.image_search, 'is_configured', return_value=True), \
             patch.object(studio_api.image_search, 'search_images', return_value=fake_results):
            status, payload = studio_api.search_images_api(None, {'query': 'arsenal'})
        assert status == 200
        assert payload['results'] == fake_results

    def test_set_asset_image_updates(self, clean_db):
        project = database.get_or_create_project('img-set-1', 'Img Set 1')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        status, payload = studio_api.set_asset_image({'id': asset['id'], 'image_url': 'https://x.com/pic.jpg'})
        assert status == 200
        assert database.get_asset(asset['id'])['image_url'] == 'https://x.com/pic.jpg'

    def test_submit_manual_content_accepts_image_url(self, clean_db):
        project = database.get_or_create_project('img-submit-1', 'Img Submit 1')
        with patch('workflows.rss_news.generate_post', return_value='Post matni ' * 10):
            status, payload = studio_api.submit_manual_content(project['id'], {
                'text': 'Xom matn', 'image_url': 'https://x.com/pic.jpg',
            })
        assert status == 200
        assert payload['image_url'] == 'https://x.com/pic.jpg'


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


class TestPublishScheduling:
    """MUHIM: publish_interval_minutes sozlanganda tasdiqlangan post
    DARHOL Telegram'ga ketmasligi, navbatga (status='scheduled')
    qo'yilishi kerak. Sozlanmagan (0, default) bo'lsa — eski
    xatti-harakat: darhol yuboriladi (orqaga moslik)."""

    def test_default_interval_zero_publishes_immediately(self, clean_db):
        project = database.get_or_create_project('sched-default', 'Sched Default')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        with patch.object(studio_api.telegram_utils, 'tg_channel', return_value={'ok': True}):
            status, payload = studio_api.approve_asset({'id': asset['id']})
        assert status == 200
        assert payload['scheduled'] is False
        assert database.get_asset(asset['id'])['status'] == 'published'

    def test_positive_interval_queues_instead_of_publishing(self, clean_db):
        project = database.get_or_create_project('sched-on', 'Sched On')
        database.update_workflow_config(project['id'], {'publish_interval_minutes': 60})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        with patch.object(studio_api.telegram_utils, 'tg_channel') as mock_tg:
            status, payload = studio_api.approve_asset({'id': asset['id']})
        mock_tg.assert_not_called()
        assert status == 200
        assert payload['scheduled'] is True
        updated = database.get_asset(asset['id'])
        assert updated['status'] == 'scheduled'
        assert updated['scheduled_at'] is not None

    def test_cannot_reapprove_scheduled_asset(self, clean_db):
        project = database.get_or_create_project('sched-dup', 'Sched Dup')
        database.update_workflow_config(project['id'], {'publish_interval_minutes': 30})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        studio_api.approve_asset({'id': asset['id']})
        status, payload = studio_api.approve_asset({'id': asset['id']})
        assert status == 400

    def test_publish_due_scheduled_skips_when_interval_not_elapsed(self, clean_db):
        project = database.get_or_create_project('sched-wait', 'Sched Wait')
        database.update_workflow_config(project['id'], {'publish_interval_minutes': 60})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        studio_api.approve_asset({'id': asset['id']})
        # Loyiha allaqachon bugun nashr qilgan (interval hali o'tmagan)
        database.save_post(project['id'], None, 'Oldingi', 'Oldingi matn', None)
        with patch.object(studio_api.telegram_utils, 'tg_channel') as mock_tg:
            studio_api.publish_due_scheduled(project['id'])
        mock_tg.assert_not_called()
        assert database.get_asset(asset['id'])['status'] == 'scheduled'

    def test_publish_due_scheduled_publishes_oldest_when_no_prior_post(self, clean_db):
        # Loyiha hali hech qachon nashr qilmagan bo'lsa, interval
        # to'sqinlik qilmasligi kerak (birinchi post darhol chiqadi).
        project = database.get_or_create_project('sched-first', 'Sched First')
        database.update_workflow_config(project['id'], {'publish_interval_minutes': 60})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        studio_api.approve_asset({'id': asset['id']})
        with patch.object(studio_api.telegram_utils, 'tg_channel', return_value={'ok': True}):
            studio_api.publish_due_scheduled(project['id'])
        assert database.get_asset(asset['id'])['status'] == 'published'

    def test_publish_due_scheduled_noop_when_interval_disabled(self, clean_db):
        project = database.get_or_create_project('sched-off', 'Sched Off')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        database.schedule_asset(asset['id'])  # qo'lda navbatga qo'yamiz (odatda sodir bo'lmaydi)
        with patch.object(studio_api.telegram_utils, 'tg_channel') as mock_tg:
            studio_api.publish_due_scheduled(project['id'])
        mock_tg.assert_not_called()

    def test_publish_interval_rejects_negative(self, clean_db):
        project = database.get_or_create_project('sched-neg', 'Sched Neg')
        status, payload = studio_api.update_config(project['id'], {'publish_interval_minutes': -5})
        assert status == 400

    def test_publish_interval_accepts_zero(self, clean_db):
        project = database.get_or_create_project('sched-zero', 'Sched Zero')
        status, payload = studio_api.update_config(project['id'], {'publish_interval_minutes': 0})
        assert status == 200


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
