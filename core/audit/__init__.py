"""Helpers de auditoria para contexto, snapshots e criação de logs."""

from .context import (
    AuditContext,
    get_audit_context,
    get_client_ip,
    reset_audit_context,
    set_audit_context,
)


def create_audit_log(*args, **kwargs):
    """Importa a gravação de auditoria sob demanda durante o bootstrap."""

    from .logging import create_audit_log as _create_audit_log

    return _create_audit_log(*args, **kwargs)


def apply_audit_log_filters(*args, **kwargs):
    """Importa o builder de filtros de auditoria sob demanda."""

    from .queries import apply_audit_log_filters as _apply_audit_log_filters

    return _apply_audit_log_filters(*args, **kwargs)


def build_changes(*args, **kwargs):
    """Importa o diff de snapshots sob demanda."""

    from .snapshots import build_changes as _build_changes

    return _build_changes(*args, **kwargs)


def build_instance_snapshot(*args, **kwargs):
    """Importa a serialização de snapshot sob demanda."""

    from .snapshots import build_instance_snapshot as _build_instance_snapshot

    return _build_instance_snapshot(*args, **kwargs)


def serialize_related_queryset(*args, **kwargs):
    """Importa a serialização de relacionamentos sob demanda."""

    from .snapshots import serialize_related_queryset as _serialize_related_queryset

    return _serialize_related_queryset(*args, **kwargs)

__all__ = [
    "AuditContext",
    "apply_audit_log_filters",
    "build_changes",
    "build_instance_snapshot",
    "create_audit_log",
    "get_audit_context",
    "get_client_ip",
    "reset_audit_context",
    "serialize_related_queryset",
    "set_audit_context",
]
