"""Configuracoes centrais da base Django.

Este modulo define os apps instalados, templates, banco SQLite, idioma
pt-BR, arquivos estaticos e regras de autenticacao usadas pela base com
dashboard por modulos e painel interno de usuarios e grupos.
"""

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

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-bska#4w*3i$h88)c=*xq%8ldvti1h#k!#+z5tip$+huv8l%vjk'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS: list[str] = env_list("ALLOWED_HOSTS", [])


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
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.AuditContextMiddleware',
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


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


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
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
PASSWORD_RESET_TIMEOUT = env_int("PASSWORD_RESET_TIMEOUT", 3600)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@baseapp.local")

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.resend.com")
EMAIL_PORT = env_int("EMAIL_PORT", 465)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "resend")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", True)

APP_FORCE_HTTPS = env_bool("APP_FORCE_HTTPS", False)
SESSION_COOKIE_SECURE = APP_FORCE_HTTPS
CSRF_COOKIE_SECURE = APP_FORCE_HTTPS
SECURE_SSL_REDIRECT = APP_FORCE_HTTPS
SECURE_HSTS_SECONDS = env_int(
    "SECURE_HSTS_SECONDS",
    31536000 if APP_FORCE_HTTPS else 0,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = APP_FORCE_HTTPS
SECURE_HSTS_PRELOAD = APP_FORCE_HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if APP_FORCE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
