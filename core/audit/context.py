"""Contexto de auditoria associado ao ciclo da requisição atual."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

from django.http import HttpRequest


@dataclass(slots=True)
class AuditContext:
    """Representa os metadados da requisicao atual usados nos logs."""

    user: object | None = None
    actor_identifier: str = ""
    request_method: str = ""
    path: str = ""
    ip_address: str | None = None
    request_id: str = ""


_audit_context: ContextVar[AuditContext] = ContextVar(
    "audit_context",
    default=AuditContext(),
)


def get_client_ip(request: HttpRequest) -> str | None:
    """Retorna o IP do cliente a partir dos headers mais comuns."""

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def set_audit_context(request: HttpRequest) -> Token[AuditContext]:
    """Armazena o contexto da requisicao atual para uso nos sinais."""

    user = request.user if getattr(request, "user", None) else None
    actor_identifier = ""
    if user is not None and getattr(user, "is_authenticated", False):
        get_username = getattr(user, "get_username", None)
        if callable(get_username):
            actor_identifier = str(get_username())

    context = AuditContext(
        user=user,
        actor_identifier=actor_identifier,
        request_method=request.method or "",
        path=request.path,
        ip_address=get_client_ip(request),
        request_id=getattr(request, "request_id", ""),
    )
    return _audit_context.set(context)


def reset_audit_context(token: Token[AuditContext]) -> None:
    """Restaura o contexto anterior ao final da requisicao."""

    _audit_context.reset(token)


def get_audit_context() -> AuditContext:
    """Retorna o contexto da requisicao corrente."""

    return _audit_context.get()
