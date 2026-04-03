"""Views HTML da trilha de auditoria no painel interno."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from typing import Any

from core.audit import apply_audit_log_filters
from core.htmx import render_page
from core.models import AuditLog
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .forms import AuditLogFilterForm

AUDIT_PAGE_SIZE = 25
RELATED_AUDIT_PREVIEW_LIMIT = 5


@dataclass(frozen=True, slots=True)
class RelatedAuditPreviewItem:
    """Representa um item do preview de eventos relacionados no detalhe."""

    audit_log: AuditLog
    detail_url: str


@dataclass(frozen=True, slots=True)
class RelatedAuditSection:
    """Agrupa atalhos e previews de eventos relacionados no detalhe."""

    scope: str
    title: str
    count: int
    count_label: str
    list_url: str
    list_label: str
    empty_message: str
    items: list[RelatedAuditPreviewItem]


def _build_preserved_querystring(params: QueryDict) -> str:
    """Monta a query string preservada para paginação da listagem."""

    preserved = params.copy()
    preserved.pop("page", None)
    encoded = preserved.urlencode()
    if not encoded:
        return ""
    return f"&{encoded}"


def _build_full_querystring(params: QueryDict) -> str:
    """Monta a query string completa para navegações derivadas da lista."""

    encoded = params.urlencode()
    if not encoded:
        return ""
    return f"?{encoded}"


def _build_querystring_from_mapping(params: dict[str, str]) -> str:
    """Monta uma query string simples a partir de um dicionário limpo."""

    query = QueryDict(mutable=True)
    for key, value in params.items():
        if value:
            query[key] = value

    encoded = query.urlencode()
    if not encoded:
        return ""
    return f"?{encoded}"


def _serialize_payload(payload: Any) -> str:
    """Serializa payloads JSON do log para exibição legível no drill-down."""

    if not payload:
        return "{}"

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    )


def _build_back_url(request: HttpRequest) -> str:
    """Preserva os filtros da lista ao voltar do drill-down."""

    return reverse("panel_audit_logs_list") + _build_full_querystring(request.GET)


def _build_url_with_mapping(path: str, params: dict[str, str]) -> str:
    """Acopla uma query string simples a uma URL base."""

    return path + _build_querystring_from_mapping(params)


def _serialize_compact_payload(payload: Any) -> str:
    """Serializa payloads JSON em uma linha para exportações."""

    if not payload:
        return "{}"

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _related_base_queryset() -> QuerySet[AuditLog]:
    """Retorna a queryset base usada pelos blocos de eventos relacionados."""

    return AuditLog.objects.select_related("actor", "content_type").order_by(
        "-created_at",
        "-id",
    )


def _format_related_count_label(count: int, *, singular: str, plural: str) -> str:
    """Gera um rótulo curto para a contagem de eventos relacionados."""

    if count == 1:
        return singular
    return plural.format(count=count)


def _build_related_section(
    *,
    scope: str,
    title: str,
    queryset: QuerySet[AuditLog],
    list_url: str,
    list_label: str,
    empty_message: str,
    detail_query: dict[str, str],
    singular_count_label: str,
    plural_count_label: str,
) -> RelatedAuditSection:
    """Materializa um bloco de navegação relacionada para o detalhe."""

    count = queryset.count()
    preview_logs = list(queryset[:RELATED_AUDIT_PREVIEW_LIMIT])
    items = [
        RelatedAuditPreviewItem(
            audit_log=related_log,
            detail_url=_build_url_with_mapping(
                reverse("panel_audit_log_detail", args=[related_log.pk]),
                detail_query,
            ),
        )
        for related_log in preview_logs
    ]

    return RelatedAuditSection(
        scope=scope,
        title=title,
        count=count,
        count_label=_format_related_count_label(
            count,
            singular=singular_count_label,
            plural=plural_count_label,
        ),
        list_url=list_url,
        list_label=list_label,
        empty_message=empty_message,
        items=items,
    )


def _build_related_actor_section(
    audit_log: AuditLog,
) -> RelatedAuditSection | None:
    """Monta o bloco de eventos relacionados ao mesmo ator."""

    actor_display = audit_log.actor_display
    if actor_display == "-":
        return None

    related_logs = _related_base_queryset().exclude(pk=audit_log.pk)
    if audit_log.actor_id:
        related_logs = related_logs.filter(actor_id=audit_log.actor_id)
    elif audit_log.actor_identifier:
        related_logs = related_logs.filter(actor_identifier=audit_log.actor_identifier)
    else:
        return None

    return _build_related_section(
        scope="actor",
        title="Mesmo ator",
        queryset=related_logs,
        list_url=_build_url_with_mapping(
            reverse("panel_audit_logs_list"),
            {"actor": actor_display},
        ),
        list_label="Filtrar por ator",
        empty_message="Nenhum outro evento encontrado para este ator.",
        detail_query={"actor": actor_display},
        singular_count_label="1 outro evento recente",
        plural_count_label="{count} outros eventos recentes",
    )


def _build_related_request_section(
    audit_log: AuditLog,
) -> RelatedAuditSection | None:
    """Monta o bloco de eventos relacionados à mesma requisição."""

    request_id = audit_log.request_id
    if not request_id:
        return None

    related_logs = _related_base_queryset().exclude(pk=audit_log.pk).filter(
        metadata__request_id=request_id
    )

    return _build_related_section(
        scope="request",
        title="Mesma requisição",
        queryset=related_logs,
        list_url=_build_url_with_mapping(
            reverse("panel_audit_logs_list"),
            {"object_query": request_id},
        ),
        list_label="Filtrar por request ID",
        empty_message="Nenhum outro evento encontrado para esta requisição.",
        detail_query={"object_query": request_id},
        singular_count_label="1 outro evento recente",
        plural_count_label="{count} outros eventos recentes",
    )


def _build_filtered_audit_logs(
    request: HttpRequest,
) -> tuple[AuditLogFilterForm, QuerySet[AuditLog]]:
    """Retorna o form de filtros e a queryset correspondente."""

    form = AuditLogFilterForm(request.GET)
    audit_logs = _related_base_queryset()

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


def _build_invalid_export_response(form: AuditLogFilterForm) -> HttpResponse:
    """Retorna um erro simples quando a exportação é chamada com filtros inválidos."""

    errors = []
    for field_name, field_errors in form.errors.items():
        field = form.fields.get(field_name)
        label = field.label if field is not None else field_name
        errors.append(f"{label}: {' '.join(str(error) for error in field_errors)}")

    body = "Filtros inválidos para exportação."
    if errors:
        body += "\n" + "\n".join(errors)

    return HttpResponse(body, status=400, content_type="text/plain; charset=utf-8")


def _build_export_filename(extension: str) -> str:
    """Monta um nome de arquivo previsível para a exportação."""

    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    return f"audit-logs-{timestamp}.{extension}"


def _build_export_filters(form: AuditLogFilterForm) -> dict[str, str]:
    """Resume os filtros válidos usados na exportação atual."""

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
    """Serializa um log de auditoria em formato estável para exportação."""

    content_type = ""
    content_type_obj = audit_log.content_type
    if content_type_obj is not None:
        content_type = (
            f"{content_type_obj.app_label}.{content_type_obj.model}"
        )

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


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_logs_list(request: HttpRequest) -> HttpResponse:
    """Lista os logs de auditoria com filtros HTML e suporte a HTMX."""

    form, audit_logs = _build_filtered_audit_logs(request)

    page_obj = Paginator(audit_logs, AUDIT_PAGE_SIZE).get_page(
        request.GET.get("page") or 1
    )

    paginator = page_obj.paginator
    page_numbers = list(
        paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
    )

    return render_page(
        request,
        "panel/audit_logs_list.html",
        "panel/partials/audit_logs_list_content.html",
        {
            "page_title": "Auditoria",
            "form": form,
            "page_obj": page_obj,
            "audit_logs": page_obj.object_list,
            "page_query": _build_preserved_querystring(request.GET),
            "current_query": _build_full_querystring(request.GET),
            "page_numbers": page_numbers,
            "page_ellipsis": paginator.ELLIPSIS,
        },
    )


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_logs_export_csv(request: HttpRequest) -> HttpResponse:
    """Exporta os logs filtrados em CSV para uso operacional."""

    form, audit_logs = _build_filtered_audit_logs(request)
    if not form.is_valid():
        return _build_invalid_export_response(form)

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


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_logs_export_json(request: HttpRequest) -> HttpResponse:
    """Exporta os logs filtrados em JSON para uso operacional."""

    form, audit_logs = _build_filtered_audit_logs(request)
    if not form.is_valid():
        return _build_invalid_export_response(form)

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


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_log_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Exibe o drill-down completo de um evento de auditoria do painel."""

    audit_log = get_object_or_404(
        AuditLog.objects.select_related("actor", "content_type"),
        pk=pk,
    )
    related_actor_section = _build_related_actor_section(audit_log)
    related_request_section = _build_related_request_section(audit_log)

    return render_page(
        request,
        "panel/audit_log_detail.html",
        "panel/partials/audit_log_detail_content.html",
        {
            "page_title": "Detalhe da auditoria",
            "audit_log": audit_log,
            "back_url": _build_back_url(request),
            "metadata_json": _serialize_payload(audit_log.metadata),
            "changes_json": _serialize_payload(audit_log.changes),
            "before_json": _serialize_payload(audit_log.before),
            "after_json": _serialize_payload(audit_log.after),
            "related_actor_section": related_actor_section,
            "related_request_section": related_request_section,
        },
    )
