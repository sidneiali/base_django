"""Endpoints de introspecção da conta autenticada na API do app core."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractUser
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from ..models import ApiResourcePermission
from .access import get_user_api_access_values
from .auth import require_api_permission
from .responses import api_error_response, api_success_response
from .types import ApiHttpRequest


def _serialize_group(group: Any) -> dict[str, object]:
    """Resume grupos vinculados ao usuário autenticado."""

    return {"id": group.pk, "name": group.name}


def _serialize_api_permissions(user: Any) -> list[dict[str, object]]:
    """Resume a matriz de permissões efetivas da API para o usuário."""

    values = get_user_api_access_values(user)
    matrix = values["permissions"]
    choices = dict(ApiResourcePermission.Resource.choices)

    return [
        {
            "resource": resource,
            "label": choices.get(resource, resource),
            **permissions,
        }
        for resource, permissions in matrix.items()
    ]


def _serialize_current_user(user: AbstractUser) -> dict[str, object]:
    """Converte o usuário autenticado num payload simples da API."""

    return {
        "id": user.pk,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": user.is_active,
        "groups": [_serialize_group(group) for group in user.groups.order_by("name")],
    }


@csrf_exempt
@require_api_permission("core.api_access")
def me(request: ApiHttpRequest) -> HttpResponse:
    """Expõe os dados básicos da conta autenticada na API."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
            request=request,
            extra_error={"allowed_methods": ["GET"]},
        )

    return api_success_response(request, data=_serialize_current_user(request.user))


@csrf_exempt
@require_api_permission("core.api_access")
def token_status(request: ApiHttpRequest) -> HttpResponse:
    """Exibe o status do token atual e a matriz de acesso efetiva."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
            request=request,
            extra_error={"allowed_methods": ["GET"]},
        )

    token = request.api_token
    if token is None:
        return api_error_response(
            "Token da API não encontrado na sessão autenticada.",
            code="token_not_available",
            status=404,
            request=request,
        )

    access_values = get_user_api_access_values(request.user)

    return api_success_response(
        request,
        data={
            "api_enabled": bool(access_values["api_enabled"]),
            "token": {
                "token_prefix": token.token_prefix,
                "issued_at": token.issued_at.isoformat() if token.issued_at else None,
                "last_used_at": (
                    token.last_used_at.isoformat() if token.last_used_at else None
                ),
                "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
                "is_active": token.is_active,
            },
            "permissions": _serialize_api_permissions(request.user),
        },
    )
