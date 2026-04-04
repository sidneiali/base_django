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

CSRF_TRUSTED_ORIGINS: list[str] = base_settings.env_list("CSRF_TRUSTED_ORIGINS", [])

DATABASES = base_settings.build_database_config(
    "app",
    default_engine="django.db.backends.postgresql",
    require_non_sqlite_fields=(
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_HOST",
    ),
)
MIDDLEWARE = base_settings.insert_middleware_after(
    list(base_settings.MIDDLEWARE),
    anchor="django.middleware.security.SecurityMiddleware",
    middleware="whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = base_settings.build_storage_settings(
    staticfiles_backend="whitenoise.storage.CompressedManifestStaticFilesStorage"
)
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
globals().update(
    base_settings.build_content_security_policy(force_https=APP_FORCE_HTTPS)
)
LOGGING = base_settings.build_logging_config(
    level=base_settings.env_str("APP_LOG_LEVEL", "INFO").upper(),
    json_logs=base_settings.env_bool("APP_LOG_JSON", True),
    log_file=base_settings.env_str("APP_LOG_FILE"),
)
base_settings.initialize_sentry(
    dsn=base_settings.env_str("SENTRY_DSN"),
    environment=base_settings.env_str("SENTRY_ENVIRONMENT", "production"),
    traces_sample_rate=base_settings.env_float("SENTRY_TRACES_SAMPLE_RATE", 0.0),
    profiles_sample_rate=base_settings.env_float("SENTRY_PROFILES_SAMPLE_RATE", 0.0),
    send_default_pii=base_settings.env_bool("SENTRY_SEND_DEFAULT_PII", True),
)
