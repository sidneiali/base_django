"""Declaracao de configuracao do app core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuracao basica do app principal do projeto."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
