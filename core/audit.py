"""Helpers de auditoria para contexto da requisicao e serializacao de diffs."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import PurePath
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import OperationalError, ProgrammingError
from django.db.models import Model
from django.http import HttpRequest

from .models import AuditLog

AUDIT_FIELD_EXCLUSIONS = {
    "auth.user": {"last_login"},
}
SENSITIVE_FIELD_NAMES = {"password"}


@dataclass(slots=True)
class AuditContext:
    """Representa os metadados da requisicao atual usados nos logs."""

    user: object | None = None
    actor_identifier: str = ""
    request_method: str = ""
    path: str = ""
    ip_address: str | None = None


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
    if getattr(user, "is_authenticated", False):
        actor_identifier = user.get_username()

    context = AuditContext(
        user=user,
        actor_identifier=actor_identifier,
        request_method=request.method,
        path=request.path,
        ip_address=get_client_ip(request),
    )
    return _audit_context.set(context)


def reset_audit_context(token: Token[AuditContext]) -> None:
    """Restaura o contexto anterior ao final da requisicao."""

    _audit_context.reset(token)


def get_audit_context() -> AuditContext:
    """Retorna o contexto da requisicao corrente."""

    return _audit_context.get()


def _normalize_value_for_comparison(value: object) -> object:
    """Converte valores para um formato estavel usado na comparacao."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, (list, tuple, set)):
        return [
            _normalize_value_for_comparison(item)
            for item in value
        ]
    if isinstance(value, dict):
        return {
            str(key): _normalize_value_for_comparison(item)
            for key, item in value.items()
        }
    if hasattr(value, "pk"):
        return str(getattr(value, "pk", ""))
    return str(value)


def _sanitize_value(field_name: str, value: object) -> object:
    """Converte valores do model para tipos serializaveis em JSON."""

    if field_name in SENSITIVE_FIELD_NAMES and value:
        return "[redacted]"
    return _normalize_value_for_comparison(value)


def build_instance_snapshot(instance: Model) -> tuple[dict[str, object], dict[str, object]]:
    """Monta um snapshot serializavel e outro para comparacao do model."""

    serialized: dict[str, object] = {}
    comparison: dict[str, object] = {}
    excluded_fields = AUDIT_FIELD_EXCLUSIONS.get(instance._meta.label_lower, set())

    for field in instance._meta.concrete_fields:
        if field.name in excluded_fields:
            continue

        raw_value = field.value_from_object(instance)
        serialized[field.name] = _sanitize_value(field.name, raw_value)
        comparison[field.name] = _normalize_value_for_comparison(raw_value)

    return serialized, comparison


def build_changes(
    before_state: dict[str, object],
    after_state: dict[str, object],
    before_comparison: dict[str, object] | None = None,
    after_comparison: dict[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    """Calcula um diff simples entre os estados anterior e posterior."""

    before_comparison = before_comparison or before_state
    after_comparison = after_comparison or after_state
    changes: dict[str, dict[str, object]] = {}

    for field_name in sorted(set(before_comparison) | set(after_comparison)):
        if before_comparison.get(field_name) == after_comparison.get(field_name):
            continue
        changes[field_name] = {
            "before": before_state.get(field_name),
            "after": after_state.get(field_name),
        }

    return changes


def serialize_related_queryset(queryset) -> list[dict[str, str]]:
    """Resume objetos relacionados com PK e representacao textual."""

    return [
        {"id": str(obj.pk), "repr": str(obj)}
        for obj in queryset.order_by("pk")
    ]


def create_audit_log(
    action: str,
    *,
    instance: Model | None = None,
    actor: object | None = None,
    actor_identifier: str = "",
    object_id: str = "",
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
    changes: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    object_repr: str = "",
) -> AuditLog | None:
    """Cria um registro de auditoria sem derrubar o fluxo principal."""

    if instance is not None and instance._meta.label_lower == "core.auditlog":
        return None

    context = get_audit_context()
    actor = actor or (
        context.user if getattr(context.user, "is_authenticated", False) else None
    )
    actor_identifier = actor_identifier or (
        actor.get_username() if getattr(actor, "is_authenticated", False) else ""
    )
    actor_identifier = actor_identifier or context.actor_identifier

    try:
        content_type = None
        if instance is not None:
            content_type = ContentType.objects.get_for_model(
                instance,
                for_concrete_model=False,
            )

        return AuditLog.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            actor_identifier=actor_identifier,
            action=action,
            content_type=content_type,
            object_id=object_id or (
                str(instance.pk) if instance is not None and instance.pk is not None else ""
            ),
            object_repr=object_repr or (str(instance) if instance is not None else ""),
            object_verbose_name=(
                str(instance._meta.verbose_name) if instance is not None else ""
            ),
            request_method=context.request_method,
            path=context.path,
            ip_address=context.ip_address,
            before=before or {},
            after=after or {},
            changes=changes or {},
            metadata=metadata or {},
        )
    except (OperationalError, ProgrammingError):
        return None
