"""Consultas reutilizáveis para leitura de logs de auditoria."""

from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet

from ..models import AuditLog


def apply_audit_log_filters(
    queryset: QuerySet[AuditLog],
    *,
    search: str = "",
    action: str = "",
    app_label: str = "",
    model: str = "",
    actor: str = "",
    object_id: str = "",
    path_filter: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[AuditLog]:
    """Aplica filtros canônicos sobre uma coleção de logs de auditoria."""

    if search:
        queryset = queryset.filter(
            Q(object_repr__icontains=search)
            | Q(object_verbose_name__icontains=search)
            | Q(actor_identifier__icontains=search)
            | Q(path__icontains=search)
            | Q(metadata__request_id__icontains=search)
        )

    if action:
        queryset = queryset.filter(action=action)

    if app_label:
        queryset = queryset.filter(content_type__app_label__iexact=app_label.lower())

    if model:
        normalized_model = model.lower()
        queryset = queryset.filter(
            Q(content_type__model__iexact=normalized_model)
            | Q(object_verbose_name__icontains=normalized_model)
        )

    if actor:
        queryset = queryset.filter(
            Q(actor__username__icontains=actor)
            | Q(actor_identifier__icontains=actor)
        )

    if object_id:
        queryset = queryset.filter(object_id=object_id)

    if path_filter:
        queryset = queryset.filter(path__icontains=path_filter)

    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset
