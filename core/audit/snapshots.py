"""Serialização estável de estado e diffs para auditoria."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import PurePath
from uuid import UUID

from django.db.models import Model

AUDIT_FIELD_EXCLUSIONS = {
    "auth.user": {"last_login"},
}
SENSITIVE_FIELD_NAMES = {"password", "token_hash"}


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
        return [_normalize_value_for_comparison(item) for item in value]
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

    return [{"id": str(obj.pk), "repr": str(obj)} for obj in queryset.order_by("pk")]
