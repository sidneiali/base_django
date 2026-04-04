"""Helpers para limitar perfis geridos ao teto de autonomia do operador."""

from __future__ import annotations

from collections.abc import Iterable

from core.api.access import get_user_api_access_values
from core.api.forms import (
    API_ACTION_OPTIONS,
    API_RESOURCE_OPTIONS,
    build_api_permission_field_name,
)
from core.api.types import ApiAccessValues
from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.db.models import QuerySet

PROFILE_SCOPE_BLOCK_REASON = (
    "Você não pode criar ou editar um perfil com autonomia maior do que a da sua própria conta."
)
GROUP_SCOPE_BLOCK_REASON = (
    "Você não pode atribuir ao grupo permissões que a sua própria conta não possui."
)
DIRECT_PERMISSION_SCOPE_BLOCK_REASON = (
    "Você não pode atribuir permissões diretas que a sua própria conta não possui."
)
API_SCOPE_BLOCK_REASON = (
    "Você não pode liberar acesso à API acima da sua própria conta."
)


def _permission_key(permission: Permission) -> str:
    """Converte uma permissão em uma chave estável ``app_label.codename``."""

    return f"{permission.content_type.app_label}.{permission.codename}"


def _get_actor_permission_keys(
    acting_user: User | None,
) -> set[str] | None:
    """Retorna as permissões efetivas do operador ou ``None`` se irrestrito."""

    if acting_user is None or acting_user.is_superuser:
        return None
    return set(acting_user.get_all_permissions())


def _build_api_capability_scope(
    values: ApiAccessValues,
) -> tuple[bool, set[tuple[str, str]]]:
    """Resume o payload de API como um conjunto de pares recurso/ação."""

    allowed_actions: set[tuple[str, str]] = set()
    for resource, flags in values["permissions"].items():
        for action, _label, permission_key in API_ACTION_OPTIONS:
            if flags[permission_key]:
                allowed_actions.add((resource, action))
    return bool(values["api_enabled"]), allowed_actions


def get_user_effective_permission_keys(user: User) -> set[str]:
    """Calcula as permissões efetivas do alvo sem depender do backend auth."""

    permission_keys = {_permission_key(permission) for permission in user.user_permissions.all()}
    for group in user.groups.all():
        permission_keys.update(
            _permission_key(permission)
            for permission in group.permissions.all()
        )
    return permission_keys


def filter_assignable_permissions_queryset(
    queryset: QuerySet[Permission],
    *,
    acting_user: User | None,
) -> QuerySet[Permission]:
    """Filtra a queryset para permissões que o operador já possui."""

    actor_permission_keys = _get_actor_permission_keys(acting_user)
    if actor_permission_keys is None:
        return queryset

    allowed_ids = [
        permission.pk
        for permission in queryset
        if _permission_key(permission) in actor_permission_keys
    ]
    return queryset.filter(pk__in=allowed_ids)


def permissions_within_actor_scope(
    permissions: Iterable[Permission],
    *,
    acting_user: User | None,
) -> bool:
    """Indica se todas as permissões informadas cabem no teto do operador."""

    actor_permission_keys = _get_actor_permission_keys(acting_user)
    if actor_permission_keys is None:
        return True
    return all(
        _permission_key(permission) in actor_permission_keys
        for permission in permissions
    )


def filter_assignable_groups_queryset(
    queryset: QuerySet[Group],
    *,
    acting_user: User | None,
) -> QuerySet[Group]:
    """Filtra grupos para manter apenas os que não excedem o operador."""

    actor_permission_keys = _get_actor_permission_keys(acting_user)
    if actor_permission_keys is None:
        return queryset

    allowed_ids = [
        group.pk
        for group in queryset
        if all(
            _permission_key(permission) in actor_permission_keys
            for permission in group.permissions.all()
        )
    ]
    return queryset.filter(pk__in=allowed_ids)


def groups_within_actor_scope(
    groups: Iterable[Group],
    *,
    acting_user: User | None,
) -> bool:
    """Indica se todos os grupos informados cabem no teto do operador."""

    actor_permission_keys = _get_actor_permission_keys(acting_user)
    if actor_permission_keys is None:
        return True
    return all(
        all(
            _permission_key(permission) in actor_permission_keys
            for permission in group.permissions.all()
        )
        for group in groups
    )


def api_payload_within_actor_scope(
    payload: ApiAccessValues,
    *,
    acting_user: User | None,
) -> bool:
    """Valida se o payload de API não concede mais do que o operador já possui."""

    if acting_user is None or acting_user.is_superuser:
        return True

    actor_api_enabled, actor_actions = _build_api_capability_scope(
        get_user_api_access_values(acting_user)
    )
    payload_api_enabled, requested_actions = _build_api_capability_scope(payload)

    if payload_api_enabled and not actor_api_enabled:
        return False
    return requested_actions.issubset(actor_actions)


def limit_api_fields_to_actor_scope(
    fields: dict[str, forms.Field],
    *,
    acting_user: User | None,
) -> None:
    """Desabilita no formulário os controles de API acima do teto do operador."""

    if acting_user is None or acting_user.is_superuser:
        return

    actor_api_enabled, actor_actions = _build_api_capability_scope(
        get_user_api_access_values(acting_user)
    )

    if not actor_api_enabled:
        api_enabled_field = fields["api_enabled"]
        api_enabled_field.disabled = True
        api_enabled_field.widget.attrs["disabled"] = True

    for resource, _resource_label in API_RESOURCE_OPTIONS:
        for action, _label, _permission_key in API_ACTION_OPTIONS:
            field_name = build_api_permission_field_name(resource, action)
            if (resource, action) in actor_actions:
                continue
            field = fields[field_name]
            field.disabled = True
            field.widget.attrs["disabled"] = True


def user_within_actor_scope(
    user: User,
    *,
    acting_user: User | None,
) -> bool:
    """Indica se o alvo inteiro cabe no teto atual do operador."""

    if acting_user is None or acting_user.is_superuser:
        return True

    if user.is_staff or user.is_superuser:
        return False

    actor_permission_keys = _get_actor_permission_keys(acting_user)
    if actor_permission_keys is not None and not get_user_effective_permission_keys(
        user
    ).issubset(actor_permission_keys):
        return False

    return api_payload_within_actor_scope(
        get_user_api_access_values(user),
        acting_user=acting_user,
    )


def group_within_actor_scope(
    group: Group,
    *,
    acting_user: User | None,
) -> bool:
    """Indica se o grupo não carrega permissões acima do operador."""

    return permissions_within_actor_scope(
        group.permissions.all(),
        acting_user=acting_user,
    )
