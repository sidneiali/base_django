"""Endpoints JSON da trilha de auditoria da API do app core."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ..audit import apply_audit_log_filters
from ..models import AuditLog
from .auth import require_api_permission
from .queries import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    build_filters_meta,
    paginate_queryset,
    parse_date_filter,
    parse_ordering,
    parse_positive_int,
)
from .responses import api_collection_response, api_error_response, api_success_response

AUDIT_LOG_ORDERING_FIELDS = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "action": "action",
    "-action": "-action",
    "actor": "actor_identifier",
    "-actor": "-actor_identifier",
    "object": "object_repr",
    "-object": "-object_repr",
    "id": "id",
    "-id": "-id",
}


def _serialize_actor(actor: Any) -> dict[str, object] | None:
    """Resume o ator autenticado associado ao evento de auditoria."""

    if actor is None:
        return None

    return {
        "id": actor.pk,
        "username": actor.get_username(),
    }


def _serialize_audit_log(
    audit_log: AuditLog,
    *,
    include_payloads: bool = False,
) -> dict[str, object]:
    """Converte um log de auditoria em JSON legível para a API."""

    payload: dict[str, object] = {
        "id": audit_log.pk,
        "created_at": audit_log.created_at.isoformat(),
        "action": audit_log.action,
        "action_label": audit_log.action_label,
        "actor": _serialize_actor(audit_log.actor),
        "actor_identifier": audit_log.actor_identifier,
        "app_label": audit_log.content_type.app_label if audit_log.content_type else "",
        "model": audit_log.content_type.model if audit_log.content_type else "",
        "object_verbose_name": audit_log.object_verbose_name,
        "object_id": audit_log.object_id,
        "object_repr": audit_log.object_repr,
        "path": audit_log.path,
        "request_method": audit_log.request_method,
        "ip_address": audit_log.ip_address,
    }

    if include_payloads:
        payload.update(
            {
                "before": audit_log.before,
                "after": audit_log.after,
                "changes": audit_log.changes,
                "metadata": audit_log.metadata,
            }
        )

    return payload


def _filter_audit_logs(
    request: HttpRequest,
    queryset: QuerySet[AuditLog],
) -> tuple[QuerySet[AuditLog], dict[str, object], JsonResponse | None]:
    """Aplica os filtros suportados na listagem dos logs de auditoria."""

    query = request.GET.get("search", "").strip() or request.GET.get("q", "").strip()
    action = request.GET.get("action", "").strip()
    if action:
        valid_actions = {choice for choice, _label in AuditLog.ACTION_CHOICES}
        if action not in valid_actions:
            return queryset, {}, api_error_response(
                "O parâmetro action é inválido para este endpoint.",
                code="invalid_query_parameter",
                status=400,
                request=request,
                extra_error={
                    "parameter": "action",
                    "allowed_values": sorted(valid_actions),
                },
            )
    app_label = request.GET.get("app_label", "").strip().lower()
    model = request.GET.get("model", "").strip().lower()
    actor = request.GET.get("actor", "").strip()
    object_id = request.GET.get("object_id", "").strip()
    path_filter = request.GET.get("path", "").strip()

    date_from, error_response = parse_date_filter(
        request.GET.get("date_from", "").strip(),
        field_name="date_from",
        request=request,
    )
    if error_response:
        return queryset, {}, error_response

    date_to, error_response = parse_date_filter(
        request.GET.get("date_to", "").strip(),
        field_name="date_to",
        request=request,
    )
    if error_response:
        return queryset, {}, error_response

    if date_from and date_to and date_from > date_to:
        return queryset, {}, api_error_response(
            "date_from não pode ser maior que date_to.",
            code="invalid_query_parameter",
            status=400,
            request=request,
            extra_error={"parameter": "date_range"},
        )

    queryset = apply_audit_log_filters(
        queryset,
        search=query,
        action=action,
        app_label=app_label,
        model=model,
        actor=actor,
        object_id=object_id,
        path_filter=path_filter,
        date_from=date_from,
        date_to=date_to,
    )

    return queryset, build_filters_meta(
        {
            "search": query,
            "action": action,
            "app_label": app_label,
            "model": model,
            "actor": actor,
            "object_id": object_id,
            "path": path_filter,
            "date_from": date_from.isoformat() if isinstance(date_from, date) else None,
            "date_to": date_to.isoformat() if isinstance(date_to, date) else None,
        }
    ), None


@csrf_exempt
@require_api_permission("core.audit_logs")
def audit_logs_collection(request: HttpRequest) -> HttpResponse:
    """Lista os logs de auditoria com filtros e paginação simples."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
            request=request,
            extra_error={"allowed_methods": ["GET"]},
        )

    audit_logs = AuditLog.objects.select_related("actor", "content_type")
    audit_logs, filters, error_response = _filter_audit_logs(request, audit_logs)
    if error_response:
        return error_response

    page, error_response = parse_positive_int(
        request.GET.get("page", "").strip(),
        field_name="page",
        default=1,
        request=request,
    )
    if error_response:
        return error_response

    page_size, error_response = parse_positive_int(
        request.GET.get("page_size", "").strip(),
        field_name="page_size",
        default=DEFAULT_PAGE_SIZE,
        maximum=MAX_PAGE_SIZE,
        request=request,
    )
    if error_response:
        return error_response

    ordering, orm_ordering, error_response = parse_ordering(
        request.GET.get("ordering", "").strip(),
        request=request,
        allowed=AUDIT_LOG_ORDERING_FIELDS,
        default="-created_at",
    )
    if error_response:
        return error_response

    audit_logs = audit_logs.order_by(orm_ordering, "-id")
    paginated_logs, pagination, error_response = paginate_queryset(
        audit_logs,
        request=request,
        page=page,
        page_size=page_size,
    )
    if error_response:
        return error_response

    return api_collection_response(
        request,
        items=[_serialize_audit_log(audit_log) for audit_log in paginated_logs],
        pagination=pagination,
        ordering=ordering,
        filters=filters,
    )


@csrf_exempt
@require_api_permission("core.audit_logs")
def audit_log_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Exibe o detalhe completo de um evento individual da auditoria."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
            request=request,
            extra_error={"allowed_methods": ["GET"]},
        )

    audit_log = AuditLog.objects.select_related("actor", "content_type").filter(pk=pk).first()
    if audit_log is None:
        return api_error_response(
            "Log de auditoria não encontrado.",
            code="not_found",
            status=404,
            request=request,
        )

    return api_success_response(
        request,
        data=_serialize_audit_log(audit_log, include_payloads=True),
    )
