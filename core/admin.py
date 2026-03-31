"""Configuracao do Django admin para o app core."""

from django import forms
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Module, UserInterfacePreference
from .preferences import (get_user_interface_preference,
                          save_user_interface_preference)


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


def build_auto_refresh_enabled_field() -> forms.BooleanField:
    """Cria o campo booleano de autoatualizacao para formularios do admin."""

    return forms.BooleanField(
        required=False,
        label="Atualização automática habilitada",
        initial=UserInterfacePreference.DEFAULT_AUTO_REFRESH_ENABLED,
    )


def build_auto_refresh_interval_field() -> forms.IntegerField:
    """Cria o campo de intervalo de autoatualizacao para formularios do admin."""

    return forms.IntegerField(
        label="Intervalo de atualização (segundos)",
        min_value=UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL,
        max_value=UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL,
        initial=UserInterfacePreference.DEFAULT_AUTO_REFRESH_INTERVAL,
        help_text=(
            "Use um valor entre "
            f"{UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL}s e "
            f"{UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL}s."
        ),
        widget=forms.NumberInput(
            attrs={
                "min": str(UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL),
                "max": str(UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL),
                "step": "5",
            }
        ),
    )


class UserInterfacePreferenceAdminFieldsMixin:
    """Adiciona os valores iniciais das preferencias de interface ao admin."""

    def __init__(self, *args, **kwargs):
        """Carrega os valores atuais ou usa defaults no cadastro novo."""

        super().__init__(*args, **kwargs)

        if self.is_bound:
            return

        preference = get_user_interface_preference(self.instance)
        self.fields["auto_refresh_enabled"].initial = preference.auto_refresh_enabled
        self.fields["auto_refresh_interval"].initial = preference.auto_refresh_interval


class AdminUserCreationForm(UserInterfacePreferenceAdminFieldsMixin, UserCreationForm):
    """Formulario de criacao do admin com preferencias de autoatualizacao."""

    auto_refresh_enabled = build_auto_refresh_enabled_field()
    auto_refresh_interval = build_auto_refresh_interval_field()


class AdminUserChangeForm(UserInterfacePreferenceAdminFieldsMixin, UserChangeForm):
    """Formulario de edicao do admin com preferencias de autoatualizacao."""

    auto_refresh_enabled = build_auto_refresh_enabled_field()
    auto_refresh_interval = build_auto_refresh_interval_field()


try:
    admin.site.unregister(User)
except NotRegistered:
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin do usuario com preferencias globais de interface."""

    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Experiência da interface",
            {
                "fields": (
                    "auto_refresh_enabled",
                    "auto_refresh_interval",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Experiência da interface",
            {
                "classes": ("wide",),
                "fields": (
                    "auto_refresh_enabled",
                    "auto_refresh_interval",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """Persiste usuario e preferencias sem depender do painel interno."""

        super().save_model(request, obj, form, change)
        save_user_interface_preference(
            obj,
            auto_refresh_enabled=form.cleaned_data["auto_refresh_enabled"],
            auto_refresh_interval=form.cleaned_data["auto_refresh_interval"],
        )
