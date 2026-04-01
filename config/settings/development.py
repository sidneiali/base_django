"""Configuracoes para desenvolvimento local."""

from __future__ import annotations

from . import base as base_settings

for setting_name in dir(base_settings):
    if setting_name.isupper():
        globals()[setting_name] = getattr(base_settings, setting_name)

SECRET_KEY = base_settings.env_str(
    "SECRET_KEY",
    "django-insecure-bska#4w*3i$h88)c=*xq%8ldvti1h#k!#+z5tip$+huv8l%vjk",
)
DEBUG = base_settings.env_bool("DEBUG", True)
ALLOWED_HOSTS: list[str] = base_settings.env_list(
    "ALLOWED_HOSTS",
    ["127.0.0.1", "localhost"],
)

DATABASES = base_settings.build_database_config(base_settings.BASE_DIR / "db.sqlite3")
STATICFILES_DIRS = [base_settings.BASE_DIR / "static"]
EMAIL_BACKEND = base_settings.env_str(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

APP_FORCE_HTTPS = base_settings.env_bool("APP_FORCE_HTTPS", False)
globals().update(base_settings.build_https_settings(APP_FORCE_HTTPS))
