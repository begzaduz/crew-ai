"""config.py'dagi BOT_ENABLED/MINI_APP_ENABLED bayroqlari uchun testlar.

MUHIM: bular endi env-orqali emas, koddagi SHARTSIZ konstantalar (False)
— Ingliz Futboli boti va Mini App loyihaga hali rasman start
berilmagani uchun butunlay o'chirilgan. Bu test aynan shu holatni
qulflaydi: kimdir tasodifan qayta True qilib qo'ysa yoki .env orqali
override qilishga urinsa, regressiya sifatida ushlanadi."""
import config


class TestBotAndMiniAppHardDisabled:
    def test_bot_is_hard_disabled(self):
        assert config.BOT_ENABLED is False

    def test_mini_app_is_hard_disabled(self):
        assert config.MINI_APP_ENABLED is False

    def test_env_override_does_not_reenable(self, monkeypatch):
        # Bular endi kod ichida qattiq belgilangan konstanta — .env yoki
        # Railway env orqali qayta yoqib bo'lmasligini tasdiqlaydi
        # (aynan shu narsa oldingi env-flag yondashuvida yetarli
        # bo'lmagan edi).
        monkeypatch.setenv('BOT_ENABLED', 'true')
        monkeypatch.setenv('MINI_APP_ENABLED', 'true')
        import importlib
        importlib.reload(config)
        try:
            assert config.BOT_ENABLED is False
            assert config.MINI_APP_ENABLED is False
        finally:
            importlib.reload(config)
