"""Helpers para ler e salvar a configuracao de acesso a API por usuario."""

from __future__ import annotations

from typing import Any

from django.db import OperationalError, ProgrammingError

from .models import ApiAccessProfile, ApiResourcePermission, ApiToken

API_CRUD_FLAGS = (
    ("create", "can_create"),
    ("read", "can_read"),
    ("update", "can_update"),
    ("delete", "can_delete"),
)


def build_default_api_permission_matrix() -> dict[str, dict[str, bool]]:
    """Retorna a matriz CRUD padrao para todos os recursos conhecidos."""

    return {
        resource: {
            "can_create": False,
            "can_read": False,
            "can_update": False,
            "can_delete": False,
        }
        for resource, _ in ApiResourcePermission.Resource.choices
    }


def get_user_api_access_profile(user: Any) -> ApiAccessProfile:
    """Retorna o perfil de API do usuario ou um objeto default em memoria."""

    if not getattr(user, "pk", None):
        return ApiAccessProfile()

    try:
        profile = ApiAccessProfile.objects.filter(user=user).first()
    except (OperationalError, ProgrammingError):
        return ApiAccessProfile(user=user)

    return profile or ApiAccessProfile(user=user)


def get_user_api_access_values(user: Any) -> dict[str, object]:
    """Retorna o estado da API do usuario com fallback seguro."""

    profile = get_user_api_access_profile(user)
    permission_matrix = build_default_api_permission_matrix()

    if not getattr(user, "pk", None):
        return {
            "api_enabled": profile.api_enabled,
            "permissions": permission_matrix,
        }

    try:
        permissions = ApiResourcePermission.objects.filter(access_profile__user=user)
    except (OperationalError, ProgrammingError):
        return {
            "api_enabled": profile.api_enabled,
            "permissions": permission_matrix,
        }

    for permission in permissions:
        permission_matrix[permission.resource] = {
            "can_create": permission.can_create,
            "can_read": permission.can_read,
            "can_update": permission.can_update,
            "can_delete": permission.can_delete,
        }

    return {
        "api_enabled": profile.api_enabled,
        "permissions": permission_matrix,
    }


def save_user_api_access(
    user: Any,
    *,
    api_enabled: bool,
    permissions: dict[str, dict[str, bool]],
) -> bool:
    """Salva o acesso a API e a matriz CRUD sem derrubar o fluxo principal."""

    if not getattr(user, "pk", None):
        return False

    try:
        profile, _ = ApiAccessProfile.objects.update_or_create(
            user=user,
            defaults={"api_enabled": api_enabled},
        )

        for resource, _ in ApiResourcePermission.Resource.choices:
            resource_values = permissions.get(resource, {})
            defaults = {
                "can_create": bool(resource_values.get("can_create", False)),
                "can_read": bool(resource_values.get("can_read", False)),
                "can_update": bool(resource_values.get("can_update", False)),
                "can_delete": bool(resource_values.get("can_delete", False)),
            }

            if any(defaults.values()):
                ApiResourcePermission.objects.update_or_create(
                    access_profile=profile,
                    resource=resource,
                    defaults=defaults,
                )
            else:
                ApiResourcePermission.objects.filter(
                    access_profile=profile,
                    resource=resource,
                ).delete()
    except (OperationalError, ProgrammingError):
        return False

    return True


def get_user_api_token(user: Any) -> ApiToken | None:
    """Retorna o token atual do usuario com fallback seguro."""

    if not getattr(user, "pk", None):
        return None

    try:
        return ApiToken.objects.filter(user=user).first()
    except (OperationalError, ProgrammingError):
        return None


def get_user_api_token_summary(user: Any) -> dict[str, object]:
    """Resume o estado atual do token da API para exibicao na conta."""

    values = get_user_api_access_values(user)
    token = get_user_api_token(user)

    return {
        "api_enabled": bool(values["api_enabled"]),
        "has_token": token is not None,
        "is_active": bool(token and token.is_active),
        "token_prefix": token.token_prefix if token else "",
        "issued_at": token.issued_at if token else None,
        "last_used_at": token.last_used_at if token else None,
        "revoked_at": token.revoked_at if token else None,
    }


def issue_user_api_token(user: Any) -> str | None:
    """Gera ou substitui o token da API de um usuario habilitado."""

    if not getattr(user, "pk", None):
        return None

    access_profile = get_user_api_access_profile(user)
    if not access_profile.api_enabled:
        return None

    try:
        _token, raw_token = ApiToken.issue_for_user(user)
    except (OperationalError, ProgrammingError):
        return None

    return raw_token


def revoke_user_api_token(user: Any) -> bool:
    """Revoga o token atual da API sem quebrar a conta do usuario."""

    token = get_user_api_token(user)
    if token is None or not token.is_active:
        return False

    try:
        token.revoke()
    except (OperationalError, ProgrammingError):
        return False

    return True
