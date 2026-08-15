"""studio_api.py uchun testlar."""
from unittest.mock import patch

import database
import studio_api


class TestImageUpload:
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

    def test_upload_image_success_returns_url_from_request_base_url(self, clean_db):
        import base64
        project = database.get_or_create_project('img-up-7', 'Img Up 7')
        b64 = base64.b64encode(b'fake-png-bytes').decode()
        status, payload = studio_api.upload_image(project['id'], {
            'content_type': 'image/png', 'image_base64': b64,
            '_request_base_url': 'https://web-production-71148.up.railway.app',
        })
        assert status == 200
        assert payload['url'] == f"https://web-production-71148.up.railway.app/api/image/{payload['id']}"

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

    def test_approve_rejects_unbalanced_tag_before_sending(self, clean_db):
        # Production incident: muvozanatsiz <blockquote> tegi Telegram
        # tomonidan rad etilib, Scheduled navbatini abadiy to'xtatib
        # qo'ygan edi. Endi bu Tasdiqlashning O'ZIDA ushlanadi — hech
        # qachon Telegram'ga (yoki Scheduled navbatiga) yetib bormaydi.
        project = database.get_or_create_project('unbalanced-tag', 'Unbalanced Tag')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Matn <blockquote>ochilgan iqtibos, yopilmagan davomi shu yerda.',
            score=0,
        )
        with patch.object(studio_api.telegram_utils, 'tg_channel') as mock_tg:
            status, payload = studio_api.approve_asset({'id': asset['id']})
        mock_tg.assert_not_called()
        assert status == 400
        assert 'blockquote' in payload['error']
        # Post hali ham 'draft' holatida qolishi kerak — na chiqarilgan,
        # na navbatga qo'yilgan.
        assert database.get_asset(asset['id'])['status'] == 'draft'

    def test_approve_uses_asset_owner_project_channel(self, clean_db):
        project = database.get_or_create_project('toy-co', 'Toy Company')
        database.set_workflow_config(project['id'], {'telegram_channel_id': '@ToyCompanyChannel'})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Test post content that is long enough to pass validation checks here.',
            score=0,
        )

        captured = {}

        def fake_tg_channel(text, image_url=None, chat_id=None, bot_token=None, bold_title=True):
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

        def fake_tg_channel(text, image_url=None, chat_id=None, bot_token=None, bold_title=True):
            captured['chat_id'] = chat_id
            return {'ok': True}

        with patch.object(studio_api.telegram_utils, 'tg_channel', side_effect=fake_tg_channel):
            studio_api.approve_asset({'id': asset['id']})

        assert captured['chat_id'] is None

    def test_approve_uses_asset_owner_project_bot_token(self, clean_db):
        project = database.get_or_create_project('own-bot', 'Own Bot Co')
        database.set_workflow_config(project['id'], {
            'telegram_channel_id': '@OwnBotChannel',
            'telegram_bot_token': '111111:OWNTOKEN',
        })
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Test post content that is long enough to pass validation checks here.',
            score=0,
        )

        captured = {}

        def fake_tg_channel(text, image_url=None, chat_id=None, bot_token=None, bold_title=True):
            captured['bot_token'] = bot_token
            return {'ok': True}

        with patch.object(studio_api.telegram_utils, 'tg_channel', side_effect=fake_tg_channel):
            status, payload = studio_api.approve_asset({'id': asset['id']})

        assert status == 200
        assert captured['bot_token'] == '111111:OWNTOKEN'

    def test_approve_falls_back_to_none_bot_token_when_not_configured(self, clean_db):
        # telegram_bot_token sozlanmagan bo'lsa, tg_channel()ning o'z
        # global TOKEN fallback'iga tayanamiz (bot_token=None uzatiladi).
        project = database.get_or_create_project('no-own-bot', 'No Own Bot')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Test', content='Test post content that is long enough to pass validation checks here.',
            score=0,
        )

        captured = {}

        def fake_tg_channel(text, image_url=None, chat_id=None, bot_token=None, bold_title=True):
            captured['bot_token'] = bot_token
            return {'ok': True}

        with patch.object(studio_api.telegram_utils, 'tg_channel', side_effect=fake_tg_channel):
            studio_api.approve_asset({'id': asset['id']})

        assert captured['bot_token'] is None

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

    def test_unschedule_returns_asset_to_draft(self, clean_db):
        project = database.get_or_create_project('sched-cancel', 'Sched Cancel')
        database.update_workflow_config(project['id'], {'publish_interval_minutes': 60})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        studio_api.approve_asset({'id': asset['id']})
        assert database.get_asset(asset['id'])['status'] == 'scheduled'
        status, payload = studio_api.unschedule_asset({'id': asset['id']})
        assert status == 200
        updated = database.get_asset(asset['id'])
        assert updated['status'] == 'draft'
        assert updated['scheduled_at'] is None

    def test_unschedule_rejects_non_scheduled_asset(self, clean_db):
        project = database.get_or_create_project('sched-cancel2', 'Sched Cancel 2')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='Content long enough to pass validation checks here.',
            score=0,
        )
        status, payload = studio_api.unschedule_asset({'id': asset['id']})
        assert status == 400

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

    def test_publish_due_scheduled_unschedules_asset_on_failure(self, clean_db):
        # PRODUCTION INCIDENT REGRESSIYASI: bitta doim muvaffaqiyatsiz
        # bo'ladigan post (masalan muvozanatsiz HTML tegi yoki noto'g'ri
        # bot tokeni tufayli) undan keyingi BARCHA postlarni ham abadiy
        # to'xtatib qo'ymasligi kerak — get_next_scheduled_asset() har
        # doim navbatning eng eskisini tanlaydi, shuning uchun muvaffaqiyat-
        # siz post 'scheduled' holatida qolib ketsa, hech qachon undan
        # keyingi postlarga navbat yetib bormaydi.
        project = database.get_or_create_project('sched-jam', 'Sched Jam')
        asset1 = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Birinchi (buzuq)', content='Content long enough to pass validation checks here.',
            score=0,
        )
        asset2 = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='Ikkinchi (toza)', content='Content long enough to pass validation checks here too.',
            score=0,
        )
        database.schedule_asset(asset1['id'])
        import time as _time
        _time.sleep(0.05)
        database.schedule_asset(asset2['id'])
        database.update_workflow_config(project['id'], {'publish_interval_minutes': 60})

        with patch.object(studio_api.telegram_utils, 'tg_channel', return_value={'ok': False, 'description': "can't parse entities"}):
            studio_api.publish_due_scheduled(project['id'])

        updated1 = database.get_asset(asset1['id'])
        updated2 = database.get_asset(asset2['id'])
        assert updated1['status'] == 'draft'  # navbatdan chiqarilib, qaytarilgan
        assert updated2['status'] == 'scheduled'  # tegilmagan, navbatda qolgan

        # Keyingi tsiklda navbat endi ochilgan — ikkinchi (toza) post
        # muammosiz chiqishi kerak.
        with patch.object(studio_api.telegram_utils, 'tg_channel', return_value={'ok': True}):
            studio_api.publish_due_scheduled(project['id'])
        assert database.get_asset(asset2['id'])['status'] == 'published'

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


class TestListAssetsRangeFilter:
    """Published/Rejected sahifalaridagi 'range' query parametri —
    studio_api.list_assets() to'g'ri database.get_assets_by_range()ga
    yo'naltirishi kerak, draft/scheduled esa range'ga umuman e'tibor
    bermasligi kerak (ular har doim to'liq ro'yxat)."""

    def test_range_param_used_for_published(self, clean_db):
        project = database.get_or_create_project('range-api-1', 'Range API 1')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        database.mark_asset_published(asset['id'])
        status, payload = studio_api.list_assets(project['id'], {'status': 'published', 'range': 'today'})
        assert status == 200
        assert len(payload) == 1

    def test_range_param_used_for_rejected(self, clean_db):
        project = database.get_or_create_project('range-api-2', 'Range API 2')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        database.mark_asset_rejected(asset['id'])
        conn = database._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE assets SET rejected_at = NOW() - INTERVAL '10 days' WHERE id=%s", (asset['id'],))
            conn.commit()
        finally:
            database._put_conn(conn)
        status, payload = studio_api.list_assets(project['id'], {'status': 'rejected', 'range': 'today'})
        assert status == 200
        assert payload == []

    def test_range_param_ignored_for_draft(self, clean_db):
        project = database.get_or_create_project('range-api-3', 'Range API 3')
        database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        # draft'lar range'dan qat'i nazar har doim to'liq ko'rinishi kerak
        status, payload = studio_api.list_assets(project['id'], {'status': 'draft', 'range': 'today'})
        assert status == 200
        assert len(payload) == 1

    def test_missing_range_defaults_to_all(self, clean_db):
        project = database.get_or_create_project('range-api-4', 'Range API 4')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        database.mark_asset_published(asset['id'])
        conn = database._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE assets SET published_at = NOW() - INTERVAL '60 days' WHERE id=%s", (asset['id'],))
            conn.commit()
        finally:
            database._put_conn(conn)
        status, payload = studio_api.list_assets(project['id'], {'status': 'published'})
        assert status == 200
        assert len(payload) == 1


class TestDashboardStatsTodayCounts:
    def test_posts_today_and_rejected_today_reflect_todays_activity_only(self, clean_db):
        project = database.get_or_create_project('stats-today', 'Stats Today')
        pub_today = database.create_asset(project_id=project['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        pub_old = database.create_asset(project_id=project['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        rej_today = database.create_asset(project_id=project['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        rej_old = database.create_asset(project_id=project['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)

        database.mark_asset_published(pub_today['id'])
        database.mark_asset_published(pub_old['id'])
        database.mark_asset_rejected(rej_today['id'])
        database.mark_asset_rejected(rej_old['id'])

        conn = database._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE assets SET published_at = NOW() - INTERVAL '9 days' WHERE id=%s", (pub_old['id'],))
                cur.execute("UPDATE assets SET rejected_at = NOW() - INTERVAL '9 days' WHERE id=%s", (rej_old['id'],))
            conn.commit()
        finally:
            database._put_conn(conn)

        status, stats = studio_api.get_dashboard_stats(project['id'])
        assert status == 200
        assert stats['posts_today'] == 1
        assert stats['rejected_today'] == 1
        assert stats['published_total'] == 2
        assert stats['rejected_total'] == 2


class TestUpdateConfig:
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


class TestFormatRulesConfig:
    """bold_title/min_length/max_length — ilgari kodga qattiq yozilgan
    (har doim yoqiq bold, 50/1000 belgi) format elementlari, endi
    DB-driven (Dashboard -> Knowledge Base -> Format qoidalari)."""

    def test_saves_bold_title_false(self, clean_db):
        project = database.get_or_create_project('fmt-1', 'Fmt 1')
        status, cfg = studio_api.update_config(project['id'], {'bold_title': False})
        assert status == 200
        assert cfg['bold_title'] is False

    def test_rejects_non_bool_bold_title(self, clean_db):
        project = database.get_or_create_project('fmt-2', 'Fmt 2')
        status, payload = studio_api.update_config(project['id'], {'bold_title': 'yes'})
        assert status == 400

    def test_saves_custom_min_max_length(self, clean_db):
        project = database.get_or_create_project('fmt-3', 'Fmt 3')
        status, cfg = studio_api.update_config(project['id'], {'min_length': 20, 'max_length': 300})
        assert status == 200
        assert cfg['min_length'] == 20
        assert cfg['max_length'] == 300

    def test_rejects_max_length_over_telegram_limit(self, clean_db):
        project = database.get_or_create_project('fmt-4', 'Fmt 4')
        status, payload = studio_api.update_config(project['id'], {'max_length': 5000})
        assert status == 400

    def test_rejects_min_length_greater_than_max_length(self, clean_db):
        project = database.get_or_create_project('fmt-5', 'Fmt 5')
        status, payload = studio_api.update_config(project['id'], {'min_length': 500, 'max_length': 100})
        assert status == 400

    def test_get_config_exposes_defaults_when_unset(self, clean_db):
        project = database.get_or_create_project('fmt-6', 'Fmt 6')
        status, cfg = studio_api.get_config(project['id'])
        assert status == 200
        assert cfg['bold_title'] is True
        assert cfg['min_length'] == 50
        assert cfg['max_length'] == 1000


class TestPromptSaveValidation:
    """MUHIM: avval custom prompt saqlanganda placeholder xato bo'lsa
    (masalan admin {chanel_tag} deb yozib qo'ysa), bu xato faqat
    generatsiya paytida serverda jimgina log qilinib, standart promptga
    qaytardi — admin buni Dashboard'da sezmasdi. Endi SAQLASHNING
    O'ZIDA aniq xabar bilan rad etiladi."""

    def test_valid_writer_prompt_saves(self, clean_db):
        project = database.get_or_create_project('prompt-ok', 'Prompt OK')
        status, cfg = studio_api.update_config(project['id'], {
            'prompts': {'writer': 'Kanal: {channel_tag}, ohang: {tone}, soha: {domain_description}, '
                                   '{nicknames_block} {content_types_block} {emoji_block} {jargon_block}'},
        })
        assert status == 200
        assert 'writer' in cfg['prompts']

    def test_typo_in_placeholder_rejected_with_clear_error(self, clean_db):
        project = database.get_or_create_project('prompt-typo', 'Prompt Typo')
        status, payload = studio_api.update_config(project['id'], {
            'prompts': {'writer': 'Kanal: {chanel_tag}'},  # typo: chanel_tag
        })
        assert status == 400
        assert 'writer' in payload['error']
        assert 'chanel_tag' in payload['error']

    def test_unknown_placeholder_in_researcher_prompt_rejected(self, clean_db):
        project = database.get_or_create_project('prompt-unknown', 'Prompt Unknown')
        status, payload = studio_api.update_config(project['id'], {
            'prompts': {'researcher': 'Soha: {domain_description}, narsa: {biror_notogri_joy}'},
        })
        assert status == 400
        assert 'researcher' in payload['error']

    def test_unescaped_brace_in_editor_prompt_rejected(self, clean_db):
        project = database.get_or_create_project('prompt-brace', 'Prompt Brace')
        status, payload = studio_api.update_config(project['id'], {
            'prompts': {'editor': 'Misol JSON: {"key": "value"}, kanal: {channel_tag}'},
        })
        assert status == 400

    def test_valid_editor_prompt_with_escaped_braces_saves(self, clean_db):
        project = database.get_or_create_project('prompt-escaped', 'Prompt Escaped')
        status, cfg = studio_api.update_config(project['id'], {
            'prompts': {'editor': 'Misol JSON: {{"key": "value"}}, kanal: {channel_tag}'},
        })
        assert status == 200

    def test_prompt_not_saved_when_validation_fails(self, clean_db):
        # Xato bo'lsa, HECH QANDAY prompt (hatto boshqa to'g'ri turdagilar
        # ham) saqlanmasligi kerak — hammasi yoki hech narsa.
        project = database.get_or_create_project('prompt-atomic', 'Prompt Atomic')
        status, payload = studio_api.update_config(project['id'], {
            'prompts': {
                'researcher': 'Soha: {domain_description}, {jargon_rules_block}',
                'writer': 'Xato: {notogri_joy}',
            },
        })
        assert status == 400
        _, cfg = studio_api.get_config(project['id'])
        assert cfg.get('prompts', {}) == {}


class TestTelegramBotTokenConfig:
    """telegram_bot_token — gemini_api_key bilan bir xil naqsh: DB'da
    saqlanadi, Dashboard'ga to'liq qaytarilmaydi, bo'sh yuborilsa
    saqlangan qiymatga tegilmaydi."""

    def test_saves_and_is_hidden_from_get_config(self, clean_db):
        project = database.get_or_create_project('bot-token-1', 'Bot Token 1')
        status, _ = studio_api.update_config(project['id'], {'telegram_bot_token': '999:SECRETTOKEN'})
        assert status == 200

        status, cfg = studio_api.get_config(project['id'])
        assert status == 200
        assert 'telegram_bot_token' not in cfg
        assert cfg['telegram_bot_token_set'] is True
        assert cfg['telegram_bot_token_hint'] == 'OKEN'

    def test_not_set_reports_false(self, clean_db):
        project = database.get_or_create_project('bot-token-2', 'Bot Token 2')
        status, cfg = studio_api.get_config(project['id'])
        assert status == 200
        assert cfg['telegram_bot_token_set'] is False
        assert cfg['telegram_bot_token_hint'] == ''

    def test_empty_value_does_not_overwrite_saved_token(self, clean_db):
        project = database.get_or_create_project('bot-token-3', 'Bot Token 3')
        studio_api.update_config(project['id'], {'telegram_bot_token': '999:SECRETTOKEN'})
        status, _ = studio_api.update_config(project['id'], {
            'telegram_bot_token': '', 'domain_description': 'still saves other fields',
        })
        assert status == 200
        _, cfg = studio_api.get_config(project['id'])
        assert cfg['telegram_bot_token_set'] is True

    def test_rejects_non_string_token(self, clean_db):
        project = database.get_or_create_project('bot-token-4', 'Bot Token 4')
        status, payload = studio_api.update_config(project['id'], {'telegram_bot_token': 12345})
        assert status == 400


class TestSubmitManualContentApiCallAccounting:
    """MUHIM: create_asset() xato bersa ham, generate_post() muvaffaqiyatli
    tugagan bo'lsa, increment_api_calls() FAQAT BITTA marta chaqirilishi
    kerak — chunki haqiqatda faqat bitta Gemini chaqiruvi sodir bo'ldi."""

    def test_does_not_double_count_when_create_asset_fails_after_generate_post(self, clean_db):
        project = database.get_or_create_project('acct-test', 'Acct Test')
        with patch('workflows.rss_news.generate_post', return_value='Post matni ' * 10), \
             patch.object(database, 'create_asset', side_effect=RuntimeError('db boom')):
            status, payload = studio_api.submit_manual_content(project['id'], {'text': 'Xom matn'})
        assert status == 500
        assert database.get_today_api_calls(project['id']) == studio_api.CALLS_PER_POST

    def test_counts_once_on_generate_post_failure(self, clean_db):
        project = database.get_or_create_project('acct-test2', 'Acct Test 2')
        with patch('workflows.rss_news.generate_post', side_effect=RuntimeError('gemini boom')):
            status, payload = studio_api.submit_manual_content(project['id'], {'text': 'Xom matn'})
        assert status == 500
        assert database.get_today_api_calls(project['id']) == studio_api.CALLS_PER_POST

    def test_counts_once_on_success(self, clean_db):
        project = database.get_or_create_project('acct-test3', 'Acct Test 3')
        with patch('workflows.rss_news.generate_post', return_value='Post matni ' * 10):
            status, payload = studio_api.submit_manual_content(project['id'], {'text': 'Xom matn'})
        assert status == 200
        assert database.get_today_api_calls(project['id']) == studio_api.CALLS_PER_POST
