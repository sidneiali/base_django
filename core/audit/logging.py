"""Criação resiliente de registros de auditoria."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import OperationalError, ProgrammingError
from django.db.models import Model

from ..models import AuditLog
from .context import get_audit_context


def _resolve_actor_identifier(actor: object | None) -> str:
    """Extrai o identificador textual do ator quando disponível."""

    if actor is None or not getattr(actor, "is_authenticated", False):
        return ""

    get_username = getattr(actor, "get_username", None)
    if not callable(get_username):
        return ""

    return str(get_username())


def create_audit_log(
    action: str,
    *,
    instance: Model | None = None,
    actor: object | None = None,
    actor_identifier: str = "",
    object_id: str = "",
    before: Mapping[str, object] | None = None,
    after: Mapping[str, object] | None = None,
    changes: Mapping[str, object] | None = None,
    metadata: Mapping[str, object] | None = None,
    object_repr: str = "",
) -> AuditLog | None:
    """Cria um registro de auditoria sem derrubar o fluxo principal."""

    if instance is not None and instance._meta.label_lower == "core.auditlog":
        return None

    context = get_audit_context()
    actor = actor or (
        context.user if getattr(context.user, "is_authenticated", False) else None
    )
    actor_identifier = actor_identifier or _resolve_actor_identifier(actor)
    actor_identifier = actor_identifier or context.actor_identifier
    actor_for_log: Any = actor if getattr(actor, "pk", None) else None

    try:
        content_type = None
        if instance is not None:
            content_type = ContentType.objects.get_for_model(
                instance,
                for_concrete_model=False,
            )

        payload_metadata = dict(metadata or {})
        if context.request_id and "request_id" not in payload_metadata:
            payload_metadata["request_id"] = context.request_id

        return AuditLog.objects.create(
            actor=actor_for_log,
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
            before=dict(before or {}),
            after=dict(after or {}),
            changes=dict(changes or {}),
            metadata=payload_metadata,
        )
    except (OperationalError, ProgrammingError):
        return None
