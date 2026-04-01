"""Formulários do admin de usuários com preferências e acesso à API."""

from typing import Any, Protocol, cast

from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm as BaseAdminUserCreationForm,
)
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User

from ...api.forms import ApiAccessFormMixin
from ...models import UserInterfacePreference
from ...preferences import get_user_interface_preference


class _UserAdminFormLike(Protocol):
    """Contrato mínimo esperado pelo mixin de preferências do admin."""

    is_bound: bool
    instance: User
    fields: dict[str, forms.Field]


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Carrega os valores atuais ou usa defaults no cadastro novo."""

        super().__init__(*args, **kwargs)
        form = cast(_UserAdminFormLike, self)

        if form.is_bound:
            return

        preference = get_user_interface_preference(form.instance)
        form.fields["auto_refresh_enabled"].initial = preference.auto_refresh_enabled
        form.fields["auto_refresh_interval"].initial = preference.auto_refresh_interval


class AdminUserCreationForm(
    UserInterfacePreferenceAdminFieldsMixin,
    ApiAccessFormMixin,
    BaseAdminUserCreationForm,
):
    """Formulario de criacao do admin com interface e acesso a API."""

    auto_refresh_enabled = build_auto_refresh_enabled_field()
    auto_refresh_interval = build_auto_refresh_interval_field()


class AdminUserChangeForm(
    UserInterfacePreferenceAdminFieldsMixin,
    ApiAccessFormMixin,
    UserChangeForm,
):
    """Formulario de edicao do admin com interface e acesso a API."""

    auto_refresh_enabled = build_auto_refresh_enabled_field()
    auto_refresh_interval = build_auto_refresh_interval_field()
