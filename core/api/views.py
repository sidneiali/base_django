"""Endpoints JSON protegidos do domínio transversal do app core."""

from __future__ import annotations

from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from ..models import ApiResourcePermission, AuditLog
from .access import get_user_api_access_values
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

User = get_user_model()

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


def _serialize_group(group) -> dict[str, object]:
    """Resume grupos vinculados ao usuário autenticado."""

    return {"id": group.pk, "name": group.name}


def _serialize_api_permissions(user) -> list[dict[str, object]]:
    """Resume a matriz de permissões efetivas da API para o usuário."""

    values = get_user_api_access_values(user)
    matrix = values["permissions"]
    choices = dict(ApiResourcePermission.Resource.choices)

    return [
        {
            "resource": resource,
            "label": choices.get(resource, resource),
            **permissions,
        }
        for resource, permissions in matrix.items()
    ]


def _serialize_current_user(user: User) -> dict[str, object]:
    """Converte o usuário autenticado num payload simples da API."""

    return {
        "id": user.pk,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": user.is_active,
        "groups": [_serialize_group(group) for group in user.groups.order_by("name")],
    }


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


def _filter_audit_logs(
    request: HttpRequest,
    queryset: QuerySet[AuditLog],
) -> tuple[QuerySet[AuditLog], dict[str, object], JsonResponse | None]:
    """Aplica os filtros suportados na listagem dos logs de auditoria."""

    query = request.GET.get("search", "").strip() or request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(
            Q(object_repr__icontains=query)
            | Q(object_verbose_name__icontains=query)
            | Q(actor_identifier__icontains=query)
            | Q(path__icontains=query)
        )

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
        queryset = queryset.filter(action=action)

    app_label = request.GET.get("app_label", "").strip().lower()
    if app_label:
        queryset = queryset.filter(content_type__app_label__iexact=app_label)

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

    path_filter = request.GET.get("path", "").strip()
    if path_filter:
        queryset = queryset.filter(path__icontains=path_filter)

    date_from, error_response = parse_date_filter(
        request.GET.get("date_from", "").strip(),
        field_name="date_from",
        request=request,
    )
    if error_response:
        return queryset, {}, error_response
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    date_to, error_response = parse_date_filter(
        request.GET.get("date_to", "").strip(),
        field_name="date_to",
        request=request,
    )
    if error_response:
        return queryset, {}, error_response
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    if date_from and date_to and date_from > date_to:
        return queryset, {}, api_error_response(
            "date_from não pode ser maior que date_to.",
            code="invalid_query_parameter",
            status=400,
            request=request,
            extra_error={"parameter": "date_range"},
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


def health(request: HttpRequest) -> HttpResponse:
    """Expõe um health check público e leve para observabilidade."""

    current_time = timezone.localtime(timezone.now())
    current_timezone = timezone.get_current_timezone_name()

    return api_success_response(
        request,
        data={
            "status": "ok",
            "timestamp": current_time.isoformat(),
            "timezone": current_timezone,
            "rate_limit": {
                "enabled": bool(getattr(settings, "API_RATE_LIMIT_ENABLED", True)),
                "requests": int(getattr(settings, "API_RATE_LIMIT_REQUESTS", 120)),
                "window_seconds": int(getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)),
            },
        },
    )


@csrf_exempt
@require_api_permission("core.api_access")
def me(request: HttpRequest) -> HttpResponse:
    """Expõe os dados básicos da conta autenticada na API."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
            request=request,
            extra_error={"allowed_methods": ["GET"]},
        )

    return api_success_response(request, data=_serialize_current_user(request.user))


@csrf_exempt
@require_api_permission("core.api_access")
def token_status(request: HttpRequest) -> HttpResponse:
    """Exibe o status do token atual e a matriz de acesso efetiva."""

    if request.method != "GET":
        return api_error_response(
            "Método não permitido para este endpoint.",
            code="method_not_allowed",
            status=405,
            request=request,
            extra_error={"allowed_methods": ["GET"]},
        )

    token = request.api_token
    if token is None:
        return api_error_response(
            "Token da API não encontrado na sessão autenticada.",
            code="token_not_available",
            status=404,
            request=request,
        )

    access_values = get_user_api_access_values(request.user)

    return api_success_response(
        request,
        data={
            "api_enabled": bool(access_values["api_enabled"]),
            "token": {
                "token_prefix": token.token_prefix,
                "issued_at": token.issued_at.isoformat() if token.issued_at else None,
                "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
                "is_active": token.is_active,
            },
            "permissions": _serialize_api_permissions(request.user),
        },
    )


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
        items=[
            _serialize_audit_log(audit_log)
            for audit_log in paginated_logs
        ],
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
            request=request,
        )

    return api_success_response(
        request,
        data=_serialize_audit_log(audit_log, include_payloads=True),
    )
