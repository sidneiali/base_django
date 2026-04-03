"""Exportacoes CSV e JSON da trilha HTML de auditoria do painel."""

from __future__ import annotations

import csv
import json
from typing import Any

from core.models import AuditLog
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone

from .forms import AuditLogFilterForm


def build_invalid_export_response(form: AuditLogFilterForm) -> HttpResponse:
    """Retorna um erro simples quando a exportacao recebe filtros invalidos."""

    errors = []
    for field_name, field_errors in form.errors.items():
        field = form.fields.get(field_name)
        label = field.label if field is not None else field_name
        errors.append(f"{label}: {' '.join(str(error) for error in field_errors)}")

    body = "Filtros inválidos para exportação."
    if errors:
        body += "\n" + "\n".join(errors)

    return HttpResponse(body, status=400, content_type="text/plain; charset=utf-8")


def render_csv_export_response(
    *,
    audit_logs: QuerySet[AuditLog],
) -> HttpResponse:
    """Materializa a exportacao CSV da query atual."""

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{_build_export_filename("csv")}"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "id",
            "created_at",
            "action",
            "action_label",
            "actor",
            "actor_identifier",
            "content_type",
            "object_id",
            "object_repr",
            "object_verbose_name",
            "request_method",
            "path",
            "request_id",
            "ip_address",
            "before",
            "after",
            "changes",
            "metadata",
        ]
    )

    for audit_log in audit_logs:
        serialized = _serialize_audit_log_export(audit_log)
        writer.writerow(
            [
                serialized["id"],
                serialized["created_at"],
                serialized["action"],
                serialized["action_label"],
                serialized["actor"],
                serialized["actor_identifier"],
                serialized["content_type"],
                serialized["object_id"],
                serialized["object_repr"],
                serialized["object_verbose_name"],
                serialized["request_method"],
                serialized["path"],
                serialized["request_id"],
                serialized["ip_address"],
                _serialize_compact_payload(serialized["before"]),
                _serialize_compact_payload(serialized["after"]),
                _serialize_compact_payload(serialized["changes"]),
                _serialize_compact_payload(serialized["metadata"]),
            ]
        )

    return response


def render_json_export_response(
    *,
    form: AuditLogFilterForm,
    audit_logs: QuerySet[AuditLog],
) -> HttpResponse:
    """Materializa a exportacao JSON da query atual."""

    response = HttpResponse(
        json.dumps(
            {
                "exported_at": timezone.localtime().isoformat(),
                "count": audit_logs.count(),
                "filters": _build_export_filters(form),
                "results": [
                    _serialize_audit_log_export(audit_log) for audit_log in audit_logs
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{_build_export_filename("json")}"'
    )
    return response


def _build_export_filename(extension: str) -> str:
    """Monta um nome de arquivo previsivel para a exportacao."""

    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    return f"audit-logs-{timestamp}.{extension}"


def _build_export_filters(form: AuditLogFilterForm) -> dict[str, str]:
    """Resume os filtros validos usados na exportacao atual."""

    if not form.is_valid():
        return {}

    cleaned_data = form.cleaned_data
    action = str(cleaned_data["action"] or "")
    action_label = dict(AuditLog.ACTION_CHOICES).get(action, "") if action else ""

    return {
        "actor": str(cleaned_data["actor"] or "").strip(),
        "action": action,
        "action_label": action_label,
        "object_query": str(cleaned_data["object_query"] or "").strip(),
        "date_from": cleaned_data["date_from"].isoformat()
        if cleaned_data.get("date_from")
        else "",
        "date_to": cleaned_data["date_to"].isoformat()
        if cleaned_data.get("date_to")
        else "",
    }


def _serialize_audit_log_export(audit_log: AuditLog) -> dict[str, Any]:
    """Serializa um log de auditoria em formato estavel para exportacao."""

    content_type = ""
    content_type_obj = audit_log.content_type
    if content_type_obj is not None:
        content_type = f"{content_type_obj.app_label}.{content_type_obj.model}"

    return {
        "id": audit_log.pk,
        "created_at": timezone.localtime(audit_log.created_at).isoformat(),
        "action": audit_log.action,
        "action_label": audit_log.action_label,
        "actor": audit_log.actor_display,
        "actor_identifier": audit_log.actor_identifier,
        "content_type": content_type,
        "object_id": audit_log.object_id,
        "object_repr": audit_log.object_repr,
        "object_verbose_name": audit_log.object_verbose_name,
        "request_method": audit_log.request_method,
        "path": audit_log.path,
        "request_id": audit_log.request_id,
        "ip_address": str(audit_log.ip_address or ""),
        "before": audit_log.before,
        "after": audit_log.after,
        "changes": audit_log.changes,
        "metadata": audit_log.metadata,
    }


def _serialize_compact_payload(payload: Any) -> str:
    """Serializa payloads JSON em uma linha para exportacoes."""

    if not payload:
        return "{}"

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
