"""Helpers compartilhados pelos sinais de auditoria."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Model

from ..audit import serialize_related_queryset

User = get_user_model()
TRACKED_MODEL_LABELS = {
    "auth.user",
    "auth.group",
    "core.apiaccessprofile",
    "core.apiresourcepermission",
    "core.apitoken",
    "core.module",
    "core.userinterfacepreference",
}


def is_tracked_model(sender: type[Model]) -> bool:
    """Indica se o model deve gerar eventos de auditoria."""

    return sender._meta.label_lower in TRACKED_MODEL_LABELS


def build_m2m_change_payload(
    instance: Model,
    relation_name: str,
    action: str,
    pk_set,
) -> dict[str, object]:
    """Resume a mudanca aplicada a um relacionamento many-to-many."""

    manager = getattr(instance, relation_name)
    related_model = manager.model
    current_items = serialize_related_queryset(manager.all())
    changed_items = []

    if pk_set:
        changed_items = serialize_related_queryset(
            related_model._default_manager.filter(pk__in=pk_set)
        )

    return {
        relation_name: {
            "operation": action,
            "changed_items": changed_items,
            "current_items": current_items,
        }
    }


def sanitize_credentials(credentials: dict[str, object]) -> dict[str, object]:
    """Remove valores sensiveis do payload recebido em falhas de login."""

    safe_credentials: dict[str, object] = {}
    for key, value in credentials.items():
        normalized_key = key.lower()
        if any(token in normalized_key for token in ("password", "token", "secret")):
            continue
        safe_credentials[key] = value
    return safe_credentials
