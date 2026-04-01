"""Configuracoes para producao."""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from . import base as base_settings

for setting_name in dir(base_settings):
    if setting_name.isupper():
        globals()[setting_name] = getattr(base_settings, setting_name)

SECRET_KEY = base_settings.env_str("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY deve ser definido quando APP_ENV=production.",
    )

DEBUG = base_settings.env_bool("DEBUG", False)
ALLOWED_HOSTS: list[str] = base_settings.env_list("ALLOWED_HOSTS", [])
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS deve ser definido quando APP_ENV=production.",
    )

DATABASES = base_settings.build_database_config(base_settings.BASE_DIR / "db.sqlite3")
STATIC_ROOT = base_settings.env_str(
    "STATIC_ROOT",
    str(base_settings.BASE_DIR / "staticfiles"),
)
EMAIL_BACKEND = base_settings.env_str(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)

APP_FORCE_HTTPS = base_settings.env_bool("APP_FORCE_HTTPS", True)
globals().update(base_settings.build_https_settings(APP_FORCE_HTTPS))
