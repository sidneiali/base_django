"""Helpers para ler e salvar preferencias de interface com fallback seguro."""

from __future__ import annotations

from typing import Any, Final

from django.contrib.auth.models import Group
from django.db import OperationalError, ProgrammingError

from .models import GroupInterfacePreference, UserInterfacePreference

_UNSET: Final = object()


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


def get_group_interface_preference(group: Any) -> GroupInterfacePreference:
    """Retorna a preferencia de grupo ou um objeto default em memoria."""

    if not getattr(group, "pk", None):
        return GroupInterfacePreference()

    try:
        preference = GroupInterfacePreference.objects.filter(group=group).first()
    except (OperationalError, ProgrammingError):
        return GroupInterfacePreference(group=group)

    return preference or GroupInterfacePreference(group=group)


def save_user_interface_preference(
    user: Any,
    *,
    auto_refresh_enabled: bool,
    auto_refresh_interval: int,
    session_idle_timeout_minutes: object = _UNSET,
) -> bool:
    """Salva as preferencias do usuario sem derrubar o fluxo principal.

    Retorna ``False`` se a tabela ainda nao existir ou se houver erro de
    esquema relacionado a migration pendente.
    """

    if not getattr(user, "pk", None):
        return False

    try:
        defaults: dict[str, object] = {
            "auto_refresh_enabled": auto_refresh_enabled,
            "auto_refresh_interval": auto_refresh_interval,
        }
        if session_idle_timeout_minutes is not _UNSET:
            defaults["session_idle_timeout_minutes"] = session_idle_timeout_minutes

        UserInterfacePreference.objects.update_or_create(
            user=user,
            defaults=defaults,
        )
    except (OperationalError, ProgrammingError):
        return False

    return True


def save_group_interface_preference(
    group: Group,
    *,
    session_idle_timeout_minutes: int | None,
) -> bool:
    """Salva as preferencias de grupo sem derrubar o fluxo principal."""

    if not getattr(group, "pk", None):
        return False

    try:
        GroupInterfacePreference.objects.update_or_create(
            group=group,
            defaults={
                "session_idle_timeout_minutes": session_idle_timeout_minutes,
            },
        )
    except (OperationalError, ProgrammingError):
        return False

    return True


def resolve_session_idle_timeout_minutes(user: Any) -> int | None:
    """Resolve a menor janela de sessao configurada entre usuario e grupos."""

    if not getattr(user, "is_authenticated", False) or not getattr(user, "pk", None):
        return None

    configured_timeouts: list[int] = []
    user_preference = get_user_interface_preference(user)
    if user_preference.session_idle_timeout_minutes is not None:
        configured_timeouts.append(user_preference.session_idle_timeout_minutes)

    try:
        group_timeouts = list(
            GroupInterfacePreference.objects.filter(
                group__user=user,
                session_idle_timeout_minutes__isnull=False,
            ).values_list("session_idle_timeout_minutes", flat=True)
        )
    except (OperationalError, ProgrammingError):
        group_timeouts = []

    configured_timeouts.extend(
        timeout for timeout in group_timeouts if timeout is not None
    )
    if not configured_timeouts:
        return None
    return min(configured_timeouts)
