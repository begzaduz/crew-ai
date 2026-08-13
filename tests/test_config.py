"""config.py'dagi _env_bool() uchun testlar — BOT_ENABLED/MINI_APP_ENABLED
kabi Railway env orqali boshqariladigan bayroqlarning noto'g'ri
parslanishi butun botni yoki Mini App'ni kutilmagan holda
o'chirib/yoqib qo'yishi mumkin, shuning uchun bu funksiya alohida
sinaladi."""
import config


class TestEnvBool:
    def test_missing_env_returns_default_true(self, monkeypatch):
        monkeypatch.delenv('SOME_FLAG', raising=False)
        assert config._env_bool('SOME_FLAG', True) is True

    def test_missing_env_returns_default_false(self, monkeypatch):
        monkeypatch.delenv('SOME_FLAG', raising=False)
        assert config._env_bool('SOME_FLAG', False) is False

    def test_true_variants(self, monkeypatch):
        for val in ('true', 'True', 'TRUE', '1', 'yes', 'on', '  true  '):
            monkeypatch.setenv('SOME_FLAG', val)
            assert config._env_bool('SOME_FLAG', False) is True, val

    def test_false_variants(self, monkeypatch):
        for val in ('false', 'False', '0', 'no', 'off', ''):
            monkeypatch.setenv('SOME_FLAG', val)
            assert config._env_bool('SOME_FLAG', True) is False, val
