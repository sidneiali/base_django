"""Views HTML da trilha de auditoria no painel interno."""

from __future__ import annotations

import json
from typing import Any

from core.htmx import render_page
from core.models import AuditLog
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .exports import (
    build_invalid_export_response,
    render_csv_export_response,
    render_json_export_response,
)
from .querying import build_filtered_audit_logs
from .related import build_related_actor_section, build_related_request_section

AUDIT_PAGE_SIZE = 25


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


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_logs_list(request: HttpRequest) -> HttpResponse:
    """Lista os logs de auditoria com filtros HTML e suporte a HTMX."""

    form, audit_logs = build_filtered_audit_logs(request.GET)

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

    form, audit_logs = build_filtered_audit_logs(request.GET)
    if not form.is_valid():
        return build_invalid_export_response(form)

    return render_csv_export_response(audit_logs=audit_logs)


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_logs_export_json(request: HttpRequest) -> HttpResponse:
    """Exporta os logs filtrados em JSON para uso operacional."""

    form, audit_logs = build_filtered_audit_logs(request.GET)
    if not form.is_valid():
        return build_invalid_export_response(form)

    return render_json_export_response(form=form, audit_logs=audit_logs)


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_log_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Exibe o drill-down completo de um evento de auditoria do painel."""

    audit_log = get_object_or_404(
        AuditLog.objects.select_related("actor", "content_type"),
        pk=pk,
    )
    related_actor_section = build_related_actor_section(audit_log)
    related_request_section = build_related_request_section(audit_log)

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
