"""Configuracao do Django admin para o app core."""

from django.contrib import admin

from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """Admin para cadastro e organizacao dos modulos do sistema."""

    list_display = (
        "name",
        "menu_group",
        "app_label",
        "permission_codename",
        "url_name",
        "is_active",
        "order",
    )
    list_filter = ("is_active", "menu_group", "app_label")
    search_fields = ("name", "slug", "permission_codename", "url_name")
    ordering = ("menu_group", "order", "name")
