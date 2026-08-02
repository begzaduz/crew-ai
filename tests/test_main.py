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
