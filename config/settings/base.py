"""Configuracoes compartilhadas entre todos os ambientes do projeto."""

from __future__ import annotations

import os
from pathlib import Path

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


def build_database_config(default_name: Path) -> dict[str, dict[str, str]]:
    """Monta a configuracao do banco a partir de variaveis de ambiente."""

    engine = env_str("DATABASE_ENGINE", "django.db.backends.sqlite3")
    name = env_str("DATABASE_NAME", str(default_name))
    database = {"ENGINE": engine, "NAME": name}

    if engine != "django.db.backends.sqlite3":
        database.update(
            {
                "USER": env_str("DATABASE_USER"),
                "PASSWORD": env_str("DATABASE_PASSWORD"),
                "HOST": env_str("DATABASE_HOST"),
                "PORT": env_str("DATABASE_PORT"),
            }
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
