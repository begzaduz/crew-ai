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
