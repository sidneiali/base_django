"""Declaracao de configuracao do app panel."""

from django.apps import AppConfig


class PanelConfig(AppConfig):
    """Configuracao basica do app de gestao interna."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "panel"
