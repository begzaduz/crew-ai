"""database.py uchun testlar — HAQIQIY (test) Postgres bilan ishlaydi
(conftest.py'dagi clean_db fixture orqali). Bu ataylab shunday: aynan
mock ishlatilmagani uchun bugun 'workflow_type' va 'data_sources'
ustunlari yetishmasligi kabi bug'lar ushlangan edi."""
import database


class TestFreshInstallSchema:
    """Bugun topilgan ikkita kritik bug uchun regressiya testlari:
    toza (yangi) bazada init_db() barcha kerakli ustunlarni yaratishi
    SHART, faqat eski studio_schema.py'dan meros ustunlarga
    tayanmasdan."""

    def test_workflow_config_works_on_fresh_db(self, clean_db):
        project = database.get_or_create_project('test-proj', 'Test Loyiha')
        # Bu chaqiruv avval 'UndefinedColumn: workflow_type' xatosi
        # bilan yiqilardi (toza bazada bu ustun yo'q edi).
        result = database.set_workflow_config(project['id'], {'tone': 'test'})
        assert result['tone'] == 'test'

    def test_data_source_works_on_fresh_db(self, clean_db):
        project = database.get_or_create_project('test-proj2', 'Test Loyiha 2')
        # Bu chaqiruv avval 'UndefinedColumn: name'/'enabled'/'config'
        # xatosi bilan yiqilardi.
        source = database.add_data_source(project['id'], 'https://example.com/rss')
        assert source['url'] == 'https://example.com/rss'
        assert source['active'] is True

    def test_init_db_is_idempotent(self, clean_db):
        # Server qayta ishga tushganda init_db() yana chaqiriladi —
        # ikkinchi marta xato bermasligi kerak.
        database.init_db()
        database.init_db()


class TestProjectIsolation:
    """CaaS: har loyiha bir-biridan to'liq mustaqil bo'lishi kerak."""

    def test_two_projects_have_independent_data_sources(self, clean_db):
        p1 = database.get_or_create_project('proj-1', 'Loyiha 1')
        p2 = database.get_or_create_project('proj-2', 'Loyiha 2')

        database.add_data_source(p1['id'], 'https://football-news.com/rss')
        database.add_data_source(p2['id'], 'https://toy-news.com/rss')

        p1_sources = database.get_data_sources(p1['id'])
        p2_sources = database.get_data_sources(p2['id'])

        assert len(p1_sources) == 1
        assert len(p2_sources) == 1
        assert p1_sources[0]['url'] == 'https://football-news.com/rss'
        assert p2_sources[0]['url'] == 'https://toy-news.com/rss'

    def test_two_projects_have_independent_workflow_config(self, clean_db):
        p1 = database.get_or_create_project('proj-a', 'Loyiha A')
        p2 = database.get_or_create_project('proj-b', 'Loyiha B')

        database.set_workflow_config(p1['id'], {'domain_description': 'football'})
        database.set_workflow_config(p2['id'], {'domain_description': 'toys'})

        assert database.get_workflow_config(p1['id'])['domain_description'] == 'football'
        assert database.get_workflow_config(p2['id'])['domain_description'] == 'toys'

    def test_two_projects_have_independent_daily_quota(self, clean_db):
        p1 = database.get_or_create_project('proj-x', 'Loyiha X')
        p2 = database.get_or_create_project('proj-y', 'Loyiha Y')

        database.increment_api_calls(p1['id'], n=5)
        database.increment_api_calls(p1['id'], n=2)
        database.increment_api_calls(p2['id'], n=9)

        assert database.get_today_api_calls(p1['id']) == 7
        assert database.get_today_api_calls(p2['id']) == 9

    def test_unused_project_has_zero_quota_used(self, clean_db):
        p = database.get_or_create_project('unused-proj', 'Ishlatilmagan')
        assert database.get_today_api_calls(p['id']) == 0

    def test_update_workflow_config_merges_not_overwrites(self, clean_db):
        p = database.get_or_create_project('merge-test', 'Merge Test')
        database.set_workflow_config(p['id'], {
            'terminology': {'a': 'b'},
            'nicknames': {'c': 'd'},
        })
        # Faqat 'terminology'ni yangilaymiz — 'nicknames' tegilmasligi kerak.
        database.update_workflow_config(p['id'], {'terminology': {'x': 'y'}})
        cfg = database.get_workflow_config(p['id'])
        assert cfg['terminology'] == {'x': 'y'}
        assert cfg['nicknames'] == {'c': 'd'}


class TestAssetLifecycle:
    """draft -> published/rejected oqimi."""

    def test_create_asset_defaults_to_draft(self, clean_db):
        p = database.get_or_create_project('asset-proj', 'Asset Loyiha')
        asset = database.create_asset(
            project_id=p['id'], source_url='https://x.com/1', asset_type='rss_news',
            title='Test', content='Test content', score=50,
        )
        assert asset['status'] == 'draft'

    def test_mark_published_updates_status_and_timestamp(self, clean_db):
        p = database.get_or_create_project('asset-proj2', 'Asset Loyiha 2')
        asset = database.create_asset(
            project_id=p['id'], source_url=None, asset_type='manual',
            title='Test', content='Test content', score=0,
        )
        database.mark_asset_published(asset['id'])
        updated = database.get_asset(asset['id'])
        assert updated['status'] == 'published'
        assert updated['published_at'] is not None

    def test_seed_project_if_empty_does_not_overwrite_existing_config(self, clean_db):
        # Admin allaqachon config'ni o'zgartirgan bo'lsa, seed uni
        # qayta yozib yubormasligi kerak (bootstrap har server
        # ishga tushishida chaqiriladi).
        database.seed_project_if_empty(
            slug='seed-test', name='Seed Test',
            default_config={'tone': 'default-tone'},
            default_sources=['https://default.com/rss'],
        )
        project = database.get_project_by_slug('seed-test')
        database.update_workflow_config(project['id'], {'tone': 'admin-changed-tone'})

        # Seed'ni QAYTA chaqiramiz (server qayta ishga tushgandek)
        database.seed_project_if_empty(
            slug='seed-test', name='Seed Test',
            default_config={'tone': 'default-tone'},
            default_sources=['https://default.com/rss'],
        )
        cfg = database.get_workflow_config(project['id'])
        assert cfg['tone'] == 'admin-changed-tone'


class TestAssetUploads:
    """Rasm yuklash — DB'da saqlash va o'qish roundtrip'i."""

    def test_save_and_get_upload_roundtrip(self, clean_db):
        p = database.get_or_create_project('upload-test', 'Upload Test')
        raw = b'\\x89PNG\\r\\n fake bytes'
        upload_id = database.save_upload(p['id'], 'image/png', raw)
        row = database.get_upload(upload_id)
        assert row['content_type'] == 'image/png'
        assert bytes(row['data']) == raw

    def test_get_upload_missing_returns_none(self, clean_db):
        assert database.get_upload(999999) is None

    def test_update_asset_image_sets_and_clears(self, clean_db):
        p = database.get_or_create_project('img-asset-test', 'Img Asset Test')
        asset = database.create_asset(
            project_id=p['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        database.update_asset_image(asset['id'], 'https://example.com/pic.jpg')
        assert database.get_asset(asset['id'])['image_url'] == 'https://example.com/pic.jpg'
        database.update_asset_image(asset['id'], None)
        assert database.get_asset(asset['id'])['image_url'] is None

    def test_delete_project_removes_uploads(self, clean_db):
        p = database.get_or_create_project('upload-del-test', 'Upload Del Test')
        database.save_upload(p['id'], 'image/png', b'x')
        assert database.delete_project(p['id']) is True


class TestDeleteProject:
    """Loyihani Dashboard'dan butunlay o'chirish — boshqa loyihalarga
    tegmasligi va bog'liq barcha ma'lumot (assets/sources/config/
    published_posts/kvota) tozalanishi kerak."""

    def test_delete_removes_project_and_related_data(self, clean_db):
        p = database.get_or_create_project('del-test', 'Delete Test')
        database.add_data_source(p['id'], 'https://x.com/rss')
        database.create_asset(
            project_id=p['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        database.save_post(p['id'], None, 'T', 'C', None)
        database.increment_api_calls(p['id'], 3)

        assert database.delete_project(p['id']) is True
        assert database.get_project_by_slug('del-test') is None
        assert database.get_data_sources(p['id']) == []
        assert database.get_assets(p['id']) == []
        assert database.get_recent_posts(p['id']) == []
        assert database.get_today_api_calls(p['id']) == 0

    def test_delete_nonexistent_returns_false(self, clean_db):
        assert database.delete_project(999999) is False

    def test_delete_does_not_affect_other_projects(self, clean_db):
        p1 = database.get_or_create_project('keep-proj', 'Keep')
        p2 = database.get_or_create_project('drop-proj', 'Drop')
        database.add_data_source(p1['id'], 'https://keep.com/rss')
        database.add_data_source(p2['id'], 'https://drop.com/rss')

        database.delete_project(p2['id'])

        assert database.get_project_by_slug('keep-proj') is not None
        assert len(database.get_data_sources(p1['id'])) == 1


class TestPublishedPostsProjectIsolation:
    """Mini App (/api/posts) endi loyihaga xos — bitta loyihaning
    tasdiqlangan posti boshqa loyihaning Mini App'ida ko'rinmasligi
    kerak."""

    def test_get_recent_posts_is_scoped_to_project(self, clean_db):
        p1 = database.get_or_create_project('feed-a', 'Feed A')
        p2 = database.get_or_create_project('feed-b', 'Feed B')
        database.save_post(p1['id'], None, 'A xabari', 'Matn A', None)
        database.save_post(p2['id'], None, 'B xabari', 'Matn B', None)

        posts_a = database.get_recent_posts(p1['id'])
        posts_b = database.get_recent_posts(p2['id'])

        assert len(posts_a) == 1 and posts_a[0]['title'] == 'A xabari'
        assert len(posts_b) == 1 and posts_b[0]['title'] == 'B xabari'


def _set_timestamp(asset_id: int, column: str, days_ago: int) -> None:
    """Test yordamchisi — asset'ning berilgan sana ustunini N kun oldingi
    vaqtga o'zgartiradi (range-filtr testlari uchun, chunki
    mark_asset_published()/mark_asset_rejected() faqat NOW()ni yozadi)."""
    conn = database._get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE assets SET {column} = NOW() - (INTERVAL '1 day' * %s) WHERE id=%s",
                (days_ago, asset_id),
            )
        conn.commit()
    finally:
        database._put_conn(conn)


class TestMarkAssetRejected:
    def test_sets_status_and_rejected_at(self, clean_db):
        p = database.get_or_create_project('reject-proj', 'Reject Loyiha')
        asset = database.create_asset(
            project_id=p['id'], source_url=None, asset_type='manual',
            title='Test', content='Test content', score=0,
        )
        database.mark_asset_rejected(asset['id'])
        updated = database.get_asset(asset['id'])
        assert updated['status'] == 'rejected'
        assert updated['rejected_at'] is not None


class TestCountAssets:
    """count_assets()/count_assets_today() — sidebar badge'lar shu bilan
    ishlaydi, to'liq qatorlarni yuklamasdan."""

    def test_count_assets_matches_actual_number(self, clean_db):
        p = database.get_or_create_project('count-proj', 'Count Loyiha')
        for _ in range(3):
            database.create_asset(
                project_id=p['id'], source_url=None, asset_type='manual',
                title='T', content='C' * 60, score=0,
            )
        assert database.count_assets(p['id'], 'draft') == 3
        assert database.count_assets(p['id'], 'published') == 0

    def test_count_assets_scoped_to_project(self, clean_db):
        p1 = database.get_or_create_project('count-p1', 'Count P1')
        p2 = database.get_or_create_project('count-p2', 'Count P2')
        database.create_asset(project_id=p1['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        database.create_asset(project_id=p2['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        database.create_asset(project_id=p2['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        assert database.count_assets(p1['id'], 'draft') == 1
        assert database.count_assets(p2['id'], 'draft') == 2

    def test_count_assets_today_excludes_older_published(self, clean_db):
        p = database.get_or_create_project('count-today-proj', 'Count Today')
        a1 = database.create_asset(project_id=p['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        a2 = database.create_asset(project_id=p['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        database.mark_asset_published(a1['id'])  # bugun
        database.mark_asset_published(a2['id'])
        _set_timestamp(a2['id'], 'published_at', days_ago=5)  # 5 kun oldin
        assert database.count_assets_today(p['id'], 'published') == 1
        assert database.count_assets(p['id'], 'published') == 2

    def test_count_assets_today_excludes_older_rejected(self, clean_db):
        p = database.get_or_create_project('count-today-rej', 'Count Today Rej')
        a1 = database.create_asset(project_id=p['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        a2 = database.create_asset(project_id=p['id'], source_url=None, asset_type='manual', title='T', content='C' * 60, score=0)
        database.mark_asset_rejected(a1['id'])
        database.mark_asset_rejected(a2['id'])
        _set_timestamp(a2['id'], 'rejected_at', days_ago=3)
        assert database.count_assets_today(p['id'], 'rejected') == 1
        assert database.count_assets(p['id'], 'rejected') == 2


class TestGetAssetsByRange:
    """Published/Rejected sahifalaridagi Bugun/Kecha/7 kun/30 kun/Barchasi
    filtr-tab'lari uchun to'g'ridan-to'g'ri database qatlamini sinaydi."""

    def _make_rejected_at(self, project, days_ago):
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title=f'rejected-{days_ago}d', content='C' * 60, score=0,
        )
        database.mark_asset_rejected(asset['id'])
        if days_ago:
            _set_timestamp(asset['id'], 'rejected_at', days_ago=days_ago)
        return asset

    def test_today_only_returns_todays_items(self, clean_db):
        p = database.get_or_create_project('range-proj1', 'Range Loyiha 1')
        today_asset = self._make_rejected_at(p, days_ago=0)
        self._make_rejected_at(p, days_ago=2)
        result = database.get_assets_by_range(p['id'], 'rejected', 'today')
        assert [r['id'] for r in result] == [today_asset['id']]

    def test_yesterday_excludes_today_and_older(self, clean_db):
        p = database.get_or_create_project('range-proj2', 'Range Loyiha 2')
        self._make_rejected_at(p, days_ago=0)
        yesterday_asset = self._make_rejected_at(p, days_ago=1)
        self._make_rejected_at(p, days_ago=3)
        result = database.get_assets_by_range(p['id'], 'rejected', 'yesterday')
        assert [r['id'] for r in result] == [yesterday_asset['id']]

    def test_7d_includes_today_and_within_window_excludes_older(self, clean_db):
        p = database.get_or_create_project('range-proj3', 'Range Loyiha 3')
        recent = self._make_rejected_at(p, days_ago=0)
        within_window = self._make_rejected_at(p, days_ago=5)
        outside_window = self._make_rejected_at(p, days_ago=10)
        result_ids = {r['id'] for r in database.get_assets_by_range(p['id'], 'rejected', '7d')}
        assert recent['id'] in result_ids
        assert within_window['id'] in result_ids
        assert outside_window['id'] not in result_ids

    def test_all_returns_everything_regardless_of_age(self, clean_db):
        p = database.get_or_create_project('range-proj4', 'Range Loyiha 4')
        old = self._make_rejected_at(p, days_ago=60)
        new = self._make_rejected_at(p, days_ago=0)
        result_ids = {r['id'] for r in database.get_assets_by_range(p['id'], 'rejected', 'all')}
        assert {old['id'], new['id']} <= result_ids

    def test_published_uses_published_at_not_rejected_at(self, clean_db):
        p = database.get_or_create_project('range-proj5', 'Range Loyiha 5')
        asset = database.create_asset(
            project_id=p['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        database.mark_asset_published(asset['id'])
        result = database.get_assets_by_range(p['id'], 'published', 'today')
        assert [r['id'] for r in result] == [asset['id']]

    def test_unknown_range_key_falls_back_to_all(self, clean_db):
        p = database.get_or_create_project('range-proj6', 'Range Loyiha 6')
        old = self._make_rejected_at(p, days_ago=200)
        result_ids = {r['id'] for r in database.get_assets_by_range(p['id'], 'rejected', 'not-a-real-range')}
        assert old['id'] in result_ids


class TestRejectedAtBackfillMigration:
    """init_db()dagi bir martalik backfill: rejected_at ustuni qo'shilishidan
    OLDIN (yoki eski kod bilan) rad etilgan yozuvlarda bu ustun NULL
    qoladi — init_db() ularni created_at bilan to'ldirishi kerak, aks
    holda ular sana-filtrli ko'rinishlarda (Bugun/Kecha/...) hech qachon
    ko'rinmay qoladi."""

    def test_backfills_null_rejected_at_from_created_at(self, clean_db):
        p = database.get_or_create_project('backfill-proj', 'Backfill Loyiha')
        asset = database.create_asset(
            project_id=p['id'], source_url=None, asset_type='manual',
            title='Eski rad etilgan', content='C' * 60, score=0,
        )
        # Eski kod xatti-harakatini simulyatsiya qilamiz: status='rejected'
        # qo'lda o'rnatiladi, lekin rejected_at NULL qoldiriladi (ya'ni
        # mark_asset_rejected() ATAYLAB chaqirilmaydi).
        conn = database._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE assets SET status='rejected', rejected_at=NULL WHERE id=%s", (asset['id'],))
            conn.commit()
        finally:
            database._put_conn(conn)

        assert database.get_asset(asset['id'])['rejected_at'] is None

        database.init_db()  # backfill shu yerda ishlaydi

        healed = database.get_asset(asset['id'])
        assert healed['rejected_at'] is not None
        assert healed['rejected_at'] == healed['created_at']
