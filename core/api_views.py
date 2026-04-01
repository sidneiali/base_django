"""Endpoints JSON protegidos do domínio transversal do app core."""

from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from .api_auth import api_error_response, require_api_permission
from .models import AuditLog

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _serialize_actor(actor) -> dict[str, object] | None:
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
        "action_label": audit_log.get_action_display(),
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


def _parse_positive_int(
    raw_value: str,
    *,
    field_name: str,
    default: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> tuple[int, JsonResponse | None]:
    """Valida inteiros positivos usados na paginação da API."""

    if not raw_value:
        return default, None

    try:
        value = int(raw_value)
    except ValueError:
        return 0, api_error_response(
            f"O parâmetro {field_name} deve ser um número inteiro.",
            code="invalid_query_parameter",
            status=400,
        )

    if value < minimum:
        return 0, api_error_response(
            f"O parâmetro {field_name} deve ser maior ou igual a {minimum}.",
            code="invalid_query_parameter",
            status=400,
        )

    if maximum is not None and value > maximum:
        return maximum, None

    return value, None


def _parse_date_filter(
    raw_value: str,
    *,
    field_name: str,
) -> tuple[date | None, JsonResponse | None]:
    """Valida filtros de data em formato ISO ``YYYY-MM-DD``."""

    if not raw_value:
        return None, None

    parsed = parse_date(raw_value)
    if parsed is None:
        return None, api_error_response(
            f"O parâmetro {field_name} deve usar o formato YYYY-MM-DD.",
            code="invalid_query_parameter",
            status=400,
        )

    return parsed, None


def _filter_audit_logs(
    request: HttpRequest,
    queryset: QuerySet[AuditLog],
) -> tuple[QuerySet[AuditLog], JsonResponse | None]:
    """Aplica os filtros suportados na listagem dos logs de auditoria."""

    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(
            Q(object_repr__icontains=query)
            | Q(object_verbose_name__icontains=query)
            | Q(actor_identifier__icontains=query)
            | Q(path__icontains=query)
        )

    action = request.GET.get("action", "").strip()
    if action:
        queryset = queryset.filter(action=action)

    model = request.GET.get("model", "").strip().lower()
    if model:
        queryset = queryset.filter(
            Q(content_type__model__iexact=model)
            | Q(object_verbose_name__icontains=model)
        )

    actor = request.GET.get("actor", "").strip()
    if actor:
        queryset = queryset.filter(
            Q(actor__username__icontains=actor)
            | Q(actor_identifier__icontains=actor)
        )

    object_id = request.GET.get("object_id", "").strip()
    if object_id:
        queryset = queryset.filter(object_id=object_id)

    date_from, error_response = _parse_date_filter(
        request.GET.get("date_from", "").strip(),
        field_name="date_from",
    )
    if error_response:
        return queryset, error_response
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    date_to, error_response = _parse_date_filter(
        request.GET.get("date_to", "").strip(),
        field_name="date_to",
    )
    if error_response:
        return queryset, error_response
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset, None


@csrf_exempt
@require_api_permission("core.audit_logs")
def audit_logs_collection(request: HttpRequest) -> HttpResponse:
    """Lista os logs de auditoria com filtros e paginação simples."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
        )

    audit_logs = AuditLog.objects.select_related("actor", "content_type")
    audit_logs, error_response = _filter_audit_logs(request, audit_logs)
    if error_response:
        return error_response

    page, error_response = _parse_positive_int(
        request.GET.get("page", "").strip(),
        field_name="page",
        default=1,
    )
    if error_response:
        return error_response

    page_size, error_response = _parse_positive_int(
        request.GET.get("page_size", "").strip(),
        field_name="page_size",
        default=DEFAULT_PAGE_SIZE,
        maximum=MAX_PAGE_SIZE,
    )
    if error_response:
        return error_response

    total = audit_logs.count()
    start = (page - 1) * page_size
    end = start + page_size

    return JsonResponse(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": [
                _serialize_audit_log(audit_log)
                for audit_log in audit_logs[start:end]
            ],
        }
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
        )

    audit_log = (
        AuditLog.objects.select_related("actor", "content_type")
        .filter(pk=pk)
        .first()
    )
    if audit_log is None:
        return api_error_response(
            "Log de auditoria não encontrado.",
            code="not_found",
            status=404,
        )

    return JsonResponse(_serialize_audit_log(audit_log, include_payloads=True))
