"""main.py'dagi sof mantiq funksiyalari uchun testlar (HTTP serverning
o'zi emas — u faqat __main__ blokida ishga tushadi, shuning uchun
modulni import qilish xavfsiz)."""
import base64

import main


class TestResolveProjectId:
    """Dashboard so'rovi qaysi loyihaga tegishli ekanini aniqlash."""

    def setup_method(self):
        main.PROJECT_ID = 1  # test uchun standart loyiha

    def test_valid_project_id_from_query(self):
        assert main._resolve_project_id({'project_id': '5'}) == 5

    def test_int_project_id(self):
        assert main._resolve_project_id({'project_id': 5}) == 5

    def test_missing_project_id_falls_back_to_default(self):
        assert main._resolve_project_id({}) == 1

    def test_invalid_project_id_falls_back_to_default(self):
        assert main._resolve_project_id({'project_id': 'abc'}) == 1

    def test_none_project_id_falls_back_to_default(self):
        assert main._resolve_project_id({'project_id': None}) == 1

    def test_empty_string_project_id_falls_back_to_default(self):
        assert main._resolve_project_id({'project_id': ''}) == 1


class TestDashboardAuth:
    """/studio va /api/studio/* himoyasi — Basic Auth."""

    def setup_method(self):
        # config.DASHBOARD_USER/PASSWORD conftest.py orqali
        # 'test-dashboard-password' / default 'admin'ga o'rnatilgan.
        import config
        self.user = config.DASHBOARD_USER
        self.password = config.DASHBOARD_PASSWORD

    def _headers(self, user, password):
        token = base64.b64encode(f'{user}:{password}'.encode()).decode()
        return {'Authorization': f'Basic {token}'}

    def test_correct_credentials_pass(self):
        assert main._check_dashboard_auth(self._headers(self.user, self.password)) is True

    def test_wrong_password_fails(self):
        assert main._check_dashboard_auth(self._headers(self.user, 'wrong')) is False

    def test_wrong_user_fails(self):
        assert main._check_dashboard_auth(self._headers('hacker', self.password)) is False

    def test_no_auth_header_fails(self):
        assert main._check_dashboard_auth({}) is False

    def test_non_basic_auth_scheme_fails(self):
        assert main._check_dashboard_auth({'Authorization': 'Bearer sometoken'}) is False

    def test_malformed_base64_fails(self):
        assert main._check_dashboard_auth({'Authorization': 'Basic not-valid-base64!!!'}) is False


class TestMaybeAutoPublish:
    """'Avtomatik yuborish' toggle — yoqilgan bo'lsa yangi asset darhol
    tasdiqlanishi (studio_api.approve_asset chaqirilishi), o'chirilgan
    bo'lsa (standart) hech narsa chaqirilmasligi kerak."""

    def test_calls_approve_when_enabled(self, clean_db):
        import database
        import studio_api
        from unittest.mock import patch

        project = database.get_or_create_project('auto-pub-main', 'Auto Publish Main')
        database.update_workflow_config(project['id'], {'auto_publish': True})
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        with patch.object(studio_api, 'approve_asset', return_value=(200, {'ok': True})) as mock_approve:
            main._maybe_auto_publish(project['id'], asset)
        mock_approve.assert_called_once()
        assert mock_approve.call_args[0][0]['id'] == asset['id']

    def test_skips_approve_when_disabled(self, clean_db):
        import database
        import studio_api
        from unittest.mock import patch

        project = database.get_or_create_project('auto-pub-main2', 'Auto Publish Main 2')
        asset = database.create_asset(
            project_id=project['id'], source_url=None, asset_type='manual',
            title='T', content='C' * 60, score=0,
        )
        with patch.object(studio_api, 'approve_asset') as mock_approve:
            main._maybe_auto_publish(project['id'], asset)
        mock_approve.assert_not_called()
