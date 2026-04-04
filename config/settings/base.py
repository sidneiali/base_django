"""Configuracoes compartilhadas entre todos os ambientes do projeto."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _


def env_bool(name: str, default: bool = False) -> bool:
    """Converte variaveis de ambiente comuns para booleano."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    """Converte variavel de ambiente numerica com fallback seguro."""

    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Converte lista CSV da variavel de ambiente em lista Python."""

    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def env_str(name: str, default: str = "") -> str:
    """Retorna uma variavel de ambiente textual com fallback simples."""

    return os.getenv(name, default)


def build_database_config(
    default_name: Path | str,
    *,
    default_engine: str = "django.db.backends.sqlite3",
    require_non_sqlite_fields: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    """Monta a configuracao do banco a partir de variaveis de ambiente."""

    engine = env_str("DATABASE_ENGINE", default_engine)
    name = env_str("DATABASE_NAME", str(default_name))
    database: dict[str, object] = {"ENGINE": engine, "NAME": name}

    if engine == "django.db.backends.sqlite3":
        return {"default": database}

    database.update(
        {
            "USER": env_str("DATABASE_USER"),
            "PASSWORD": env_str("DATABASE_PASSWORD"),
            "HOST": env_str("DATABASE_HOST"),
            "PORT": env_str("DATABASE_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DATABASE_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": env_bool("DATABASE_CONN_HEALTH_CHECKS", True),
        }
    )

    sslmode = env_str("DATABASE_SSLMODE")
    if sslmode:
        database["OPTIONS"] = {"sslmode": sslmode}

    missing_fields = [
        env_name
        for env_name in require_non_sqlite_fields
        if not str(database.get(env_name.replace("DATABASE_", ""), "")).strip()
    ]
    if missing_fields:
        missing_list = ", ".join(missing_fields)
        raise ImproperlyConfigured(
            "As seguintes variaveis devem ser definidas para banco nao-sqlite: "
            f"{missing_list}.",
        )

    return {"default": database}


def build_https_settings(force_https: bool) -> dict[str, object]:
    """Deriva as flags de seguranca com base no modo HTTPS."""

    settings: dict[str, object] = {
        "SESSION_COOKIE_SECURE": force_https,
        "CSRF_COOKIE_SECURE": force_https,
        "SECURE_SSL_REDIRECT": force_https,
        "SECURE_HSTS_SECONDS": env_int(
            "SECURE_HSTS_SECONDS",
            31536000 if force_https else 0,
        ),
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": force_https,
        "SECURE_HSTS_PRELOAD": force_https,
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        "SECURE_REFERRER_POLICY": "same-origin",
    }

    if force_https:
        settings["SECURE_PROXY_SSL_HEADER"] = (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        )

    return settings


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "axes",
    "django_bootstrap5",
    "core",
    "panel",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.RequestIdMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.ApiTokenAuthenticationMiddleware',
    'core.middleware.AuditContextMiddleware',
    'core.middleware.ApiRateLimitMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.sidebar_modules',
                'core.context_processors.user_interface_preferences',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGES = [
    ("pt-br", _("Português (Brasil)")),
]

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
PASSWORD_RESET_TIMEOUT = env_int("PASSWORD_RESET_TIMEOUT", 3600)
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL", "no-reply@baseapp.local")

EMAIL_HOST = env_str("EMAIL_HOST", "smtp.resend.com")
EMAIL_PORT = env_int("EMAIL_PORT", 465)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER", "resend")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", True)

API_RATE_LIMIT_ENABLED = env_bool("API_RATE_LIMIT_ENABLED", True)
API_RATE_LIMIT_REQUESTS = env_int("API_RATE_LIMIT_REQUESTS", 120)
API_RATE_LIMIT_WINDOW_SECONDS = env_int("API_RATE_LIMIT_WINDOW_SECONDS", 60)

AXES_ENABLED = env_bool("AXES_ENABLED", True)
AXES_FAILURE_LIMIT = env_int("AXES_FAILURE_LIMIT", 5)
AXES_COOLOFF_TIME = timedelta(minutes=env_int("AXES_COOLOFF_MINUTES", 15))
AXES_HTTP_RESPONSE_CODE = 429
AXES_LOCKOUT_PARAMETERS = ["ip_address"]
AXES_LOCKOUT_CALLABLE = "core.auth.views.axes_lockout_response"
AXES_RESET_ON_SUCCESS = env_bool("AXES_RESET_ON_SUCCESS", True)
AXES_USERNAME_FORM_FIELD = "username"
