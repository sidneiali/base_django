"""Registro do admin de usuários com preferências e acesso à API."""

from typing import Any, TypeAlias, cast

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from ...api.forms import API_PERMISSION_FIELD_ROWS
from ...preferences import save_user_interface_preference
from .forms import AdminUserChangeForm, AdminUserCreationForm

AdminFieldset: TypeAlias = tuple[str | None, dict[str, Any]]


def _normalize_fieldsets(fieldsets: object | None) -> tuple[AdminFieldset, ...]:
    """Converte fieldsets herdados em uma tupla estável para extensão local."""

    if not fieldsets:
        return ()

    return tuple(
        cast(list[AdminFieldset] | tuple[AdminFieldset, ...], fieldsets)
    )


admin_registry = cast(dict[object, object], getattr(admin.site, "_registry", {}))
if User in admin_registry:
    admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin do usuario com preferencias globais e acesso controlado a API."""

    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    fieldsets = cast(
        Any,
        _normalize_fieldsets(BaseUserAdmin.fieldsets) + (
            (
                "Experiência da interface",
                {
                    "fields": (
                        "auto_refresh_enabled",
                        "auto_refresh_interval",
                    )
                },
            ),
            (
                "Acesso à API",
                {
                    "fields": ("api_enabled",) + API_PERMISSION_FIELD_ROWS,
                },
            ),
        ),
    )
    add_fieldsets = cast(
        Any,
        _normalize_fieldsets(BaseUserAdmin.add_fieldsets) + (
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
            (
                "Acesso à API",
                {
                    "classes": ("wide",),
                    "fields": ("api_enabled",) + API_PERMISSION_FIELD_ROWS,
                },
            ),
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
        form.save_api_access_settings(obj)
