"""Querysets e filtros reutilizaveis da auditoria HTML do painel."""

from __future__ import annotations

from core.audit import apply_audit_log_filters
from core.models import AuditLog
from django.db.models import QuerySet
from django.http import QueryDict

from .forms import AuditLogFilterForm


def related_base_queryset() -> QuerySet[AuditLog]:
    """Retorna a queryset base usada na listagem e nos relacionamentos."""

    return AuditLog.objects.select_related("actor", "content_type").order_by(
        "-created_at",
        "-id",
    )


def build_filtered_audit_logs(
    params: QueryDict,
) -> tuple[AuditLogFilterForm, QuerySet[AuditLog]]:
    """Materializa o form de filtros e a queryset correspondente."""

    form = AuditLogFilterForm(params)
    audit_logs = related_base_queryset()

    if form.is_valid():
        audit_logs = apply_audit_log_filters(
            audit_logs,
            search=str(form.cleaned_data["object_query"] or "").strip(),
            action=str(form.cleaned_data["action"] or "").strip(),
            actor=str(form.cleaned_data["actor"] or "").strip(),
            date_from=form.cleaned_data.get("date_from"),
            date_to=form.cleaned_data.get("date_to"),
        )

    return form, audit_logs
