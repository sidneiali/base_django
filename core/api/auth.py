"""Autenticacao Bearer e autorizacao CRUD para os endpoints JSON da API."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any

from django.db import OperationalError, ProgrammingError

from ..audit import create_audit_log
from ..models import ApiAccessProfile, ApiResourcePermission, ApiToken, AuditLog
from .responses import api_error_response
from .types import ApiHttpRequest

API_METHOD_ACTIONS = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


@dataclass(slots=True)
class ApiAuthenticationResult:
    """Representa o resultado da autenticacao Bearer da API."""

    user: object | None = None
    token: ApiToken | None = None
    code: str = ""
    detail: str = ""

    @property
    def is_authenticated(self) -> bool:
        """Indica se a autenticacao da requisicao foi concluida com sucesso."""

        return self.user is not None and self.token is not None and not self.code


def _resolve_username(actor: object | None) -> str:
    """Extrai o username de um ator autenticado sem depender do tipo concreto."""

    if actor is None or not getattr(actor, "is_authenticated", False):
        return ""

    get_username = getattr(actor, "get_username", None)
    if not callable(get_username):
        return ""

    return str(get_username())


def extract_bearer_token(
    request: ApiHttpRequest,
) -> tuple[str | None, str | None, str | None]:
    """Extrai o token Bearer do header Authorization."""

    header = request.META.get("HTTP_AUTHORIZATION", "").strip()
    if not header:
        return None, "missing_authorization", "Cabeçalho Authorization ausente."

    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None, "invalid_authorization", "Use Authorization: Bearer <token>."

    return value.strip(), None, None


def get_api_action_for_method(method: str) -> str | None:
    """Converte o método HTTP na ação CRUD equivalente."""

    return API_METHOD_ACTIONS.get(method.upper())


def authenticate_api_request(request: ApiHttpRequest) -> ApiAuthenticationResult:
    """Valida o token Bearer da requisição e retorna o usuário autenticado."""

    cached_result = getattr(request, "api_auth_result", None)
    if cached_result is not None:
        return cached_result

    raw_token, error_code, error_detail = extract_bearer_token(request)
    if error_code:
        result = ApiAuthenticationResult(code=error_code, detail=error_detail or "")
        request.api_auth_result = result
        return result

    try:
        token = (
            ApiToken.objects.select_related("user")
            .filter(token_hash=ApiToken.hash_token(raw_token or ""))
            .first()
        )
    except (OperationalError, ProgrammingError):
        result = ApiAuthenticationResult(
            code="api_unavailable",
            detail="A autenticação da API está indisponível no momento.",
        )
        request.api_auth_result = result
        return result

    if token is None:
        result = ApiAuthenticationResult(
            code="invalid_token",
            detail="O token informado é inválido.",
        )
        request.api_auth_result = result
        return result

    if not token.is_active:
        result = ApiAuthenticationResult(
            code="revoked_token",
            detail="O token informado foi revogado.",
        )
        request.api_auth_result = result
        return result

    user = token.user
    if not getattr(user, "is_active", False):
        result = ApiAuthenticationResult(
            code="inactive_user",
            detail="O usuário vinculado ao token está inativo.",
        )
        request.api_auth_result = result
        return result

    try:
        access_profile = ApiAccessProfile.objects.filter(user=user).first()
    except (OperationalError, ProgrammingError):
        result = ApiAuthenticationResult(
            code="api_unavailable",
            detail="A autenticação da API está indisponível no momento.",
        )
        request.api_auth_result = result
        return result

    if not access_profile or not access_profile.api_enabled:
        result = ApiAuthenticationResult(
            code="api_disabled",
            detail="O acesso à API não está habilitado para este usuário.",
        )
        request.api_auth_result = result
        return result

    result = ApiAuthenticationResult(user=user, token=token)
    request.api_auth_result = result
    return result


def user_has_api_permission(user: object | None, resource: str, action: str) -> bool:
    """Indica se o usuário tem a permissão CRUD para o recurso informado."""

    if user is None or action not in {"create", "read", "update", "delete"}:
        return False

    permission_field = f"can_{action}"
    user_lookup: Any = user

    try:
        return ApiResourcePermission.objects.filter(
            access_profile__user=user_lookup,
            access_profile__api_enabled=True,
            resource=resource,
            **{permission_field: True},
        ).exists()
    except (OperationalError, ProgrammingError):
        return False


def log_api_access_denied(
    request: ApiHttpRequest,
    *,
    result: ApiAuthenticationResult | None,
    code: str,
    detail: str,
    resource: str,
    action: str | None,
    status: int,
) -> None:
    """Registra falhas de autenticação/autorização da API na auditoria."""

    actor = result.user if result and getattr(result.user, "pk", None) else None
    actor_identifier = _resolve_username(actor)

    create_audit_log(
        AuditLog.ACTION_API_ACCESS_DENIED,
        actor=actor,
        actor_identifier=actor_identifier,
        metadata={
            "event": "api_access_denied",
            "reason_code": code,
            "detail": detail,
            "resource": resource,
            "action": action or "",
            "status": status,
        },
        object_repr=resource,
    )


def require_api_permission(resource: str):
    """Protege uma view JSON via Bearer token e permissão CRUD do recurso."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: ApiHttpRequest, *args: Any, **kwargs: Any):
            result = authenticate_api_request(request)
            if not result.is_authenticated:
                request_method = request.method or ""
                log_api_access_denied(
                    request,
                    result=result,
                    code=result.code or "api_auth_failed",
                    detail=result.detail or "A autenticação da API falhou.",
                    resource=resource,
                    action=get_api_action_for_method(request_method),
                    status=401,
                )
                return api_error_response(
                    result.detail or "A autenticação da API falhou.",
                    code=result.code or "api_auth_failed",
                    status=401,
                    request=request,
                )

            action = get_api_action_for_method(request.method or "")
            if action is None:
                return api_error_response(
                    "Método não permitido para este endpoint.",
                    code="method_not_allowed",
                    status=405,
                    request=request,
                    extra_error={"allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                )

            if not user_has_api_permission(result.user, resource, action):
                log_api_access_denied(
                    request,
                    result=result,
                    code="forbidden",
                    detail="Seu token não possui permissão para esta operação.",
                    resource=resource,
                    action=action,
                    status=403,
                )
                return api_error_response(
                    "Seu token não possui permissão para esta operação.",
                    code="forbidden",
                    status=403,
                    request=request,
                )

            request.user = result.user
            request._cached_user = result.user
            request.api_token = result.token
            request.api_permission_action = action

            if result.token is not None:
                result.token.mark_used()

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
