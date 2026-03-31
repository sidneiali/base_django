"""Helpers para ler e salvar preferencias de interface com fallback seguro."""

from __future__ import annotations

from typing import Any

from django.db import OperationalError, ProgrammingError

from .models import UserInterfacePreference


def get_user_interface_preference(user: Any) -> UserInterfacePreference:
    """Retorna a preferencia do usuario ou um objeto default em memoria.

    Quando a migration ainda nao foi aplicada, o acesso ao banco pode falhar
    com erros de esquema. Nesses casos, a aplicacao continua funcionando com
    os valores padrao do model em vez de quebrar a requisicao.
    """

    if not getattr(user, "is_authenticated", False) or not getattr(user, "pk", None):
        return UserInterfacePreference()

    try:
        preference = UserInterfacePreference.objects.filter(user=user).first()
    except (OperationalError, ProgrammingError):
        return UserInterfacePreference(user=user)

    return preference or UserInterfacePreference(user=user)


def get_user_interface_preference_values(user: Any) -> dict[str, int | bool]:
    """Retorna apenas os valores usados pelo layout global da aplicacao."""

    preference = get_user_interface_preference(user)
    return {
        "auto_refresh_enabled": preference.auto_refresh_enabled,
        "auto_refresh_interval": preference.auto_refresh_interval,
    }


def save_user_interface_preference(
    user: Any,
    *,
    auto_refresh_enabled: bool,
    auto_refresh_interval: int,
) -> bool:
    """Salva as preferencias do usuario sem derrubar o fluxo principal.

    Retorna ``False`` se a tabela ainda nao existir ou se houver erro de
    esquema relacionado a migration pendente.
    """

    if not getattr(user, "pk", None):
        return False

    try:
        UserInterfacePreference.objects.update_or_create(
            user=user,
            defaults={
                "auto_refresh_enabled": auto_refresh_enabled,
                "auto_refresh_interval": auto_refresh_interval,
            },
        )
    except (OperationalError, ProgrammingError):
        return False

    return True
