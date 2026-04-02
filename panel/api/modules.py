"""Endpoints JSON protegidos do domínio de módulos do painel."""

from __future__ import annotations

from core.api.auth import require_api_permission
from core.api.queries import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    build_filters_meta,
    paginate_queryset,
    parse_bool_filter,
    parse_ordering,
    parse_positive_int,
)
from core.api.responses import (
    api_collection_response,
    api_error_response,
    api_success_response,
)
from core.audit import create_audit_log
from core.models import AuditLog, Module
from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch
from django.views.decorators.csrf import csrf_exempt

from .forms import ApiModuleWriteForm
from .shared import json_form_errors, parse_json_body

MODULE_ORDERING_FIELDS = {
    "name": "name",
    "-name": "-name",
    "slug": "slug",
    "-slug": "-slug",
    "menu_group": "menu_group",
    "-menu_group": "-menu_group",
    "order": "order",
    "-order": "-order",
    "id": "id",
    "-id": "-id",
}


def _serialize_permission(permission: Permission) -> dict[str, object]:
    """Resume a permissão exigida por um módulo em payload legível."""

    return {
        "id": permission.pk,
        "codename": permission.codename,
        "name": permission.name,
        "app_label": permission.content_type.app_label,
        "model": permission.content_type.model,
    }


def _build_permission_map(modules: list[Module]) -> dict[tuple[str, str], Permission]:
    """Carrega de uma vez as permissões usadas pelos módulos serializados."""

    pairs = {
        (module.app_label, module.permission_codename)
        for module in modules
        if module.app_label and module.permission_codename
    }
    if not pairs:
        return {}

    query = Q()
    for app_label, codename in pairs:
        query |= Q(content_type__app_label=app_label, codename=codename)

    permissions = Permission.objects.select_related("content_type").filter(query)
    return {
        (permission.content_type.app_label, permission.codename): permission
        for permission in permissions
    }


def _resolve_module_url(module: Module) -> str:
    """Resolve a URL pública do módulo sem quebrar serialização por rota ruim."""

    try:
        return module.get_absolute_url()
    except NoReverseMatch:
        return ""


def _serialize_module(
    module: Module,
    *,
    permission_map: dict[tuple[str, str], Permission],
) -> dict[str, object]:
    """Resume um módulo do dashboard em formato JSON."""

    permission = permission_map.get((module.app_label, module.permission_codename))
    return {
        "id": module.pk,
        "name": module.name,
        "slug": module.slug,
        "description": module.description,
        "icon": module.icon,
        "url_name": module.url_name,
        "menu_group": module.menu_group,
        "order": module.order,
        "is_active": module.is_active,
        "uses_generic_entry": module.uses_generic_entry,
        "resolved_url": _resolve_module_url(module),
        "full_permission": module.full_permission,
        "permission_label": module.permission_label,
        "permission": _serialize_permission(permission) if permission else None,
        "is_initial_module": module.is_initial_module,
        "can_delete": not bool(module.delete_block_reason),
        "delete_block_reason": module.delete_block_reason,
    }


def _build_module_form_data(
    payload: dict[str, object],
    *,
    instance: Module | None = None,
) -> dict[str, object]:
    """Normaliza o payload JSON nos dados esperados pelo formulário do módulo."""

    permission_value: object = ""
    if instance is not None and instance.full_permission:
        permission = Permission.objects.filter(
            content_type__app_label=instance.app_label,
            codename=instance.permission_codename,
        ).first()
        if permission is not None:
            permission_value = permission.pk

    return {
        "name": payload.get("name", instance.name if instance else ""),
        "slug": payload.get("slug", instance.slug if instance else ""),
        "description": payload.get(
            "description",
            instance.description if instance else "",
        ),
        "icon": payload.get("icon", instance.icon if instance else ""),
        "url_name": payload.get("url_name", instance.url_name if instance else ""),
        "menu_group": payload.get(
            "menu_group",
            instance.menu_group if instance else "Geral",
        ),
        "order": payload.get("order", instance.order if instance else 0),
        "is_active": payload.get(
            "is_active",
            instance.is_active if instance else True,
        ),
        "permission": payload.get(
            "permission",
            payload.get("permission_id", permission_value),
        ),
    }


def _filter_modules(
    request: HttpRequest,
    queryset: QuerySet[Module],
) -> tuple[QuerySet[Module], dict[str, object], HttpResponse | None]:
    """Aplica filtros explícitos à coleção de módulos do dashboard."""

    search = request.GET.get("search", "").strip() or request.GET.get("q", "").strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(slug__icontains=search)
            | Q(description__icontains=search)
            | Q(url_name__icontains=search)
            | Q(menu_group__icontains=search)
        )

    slug = request.GET.get("slug", "").strip()
    if slug:
        queryset = queryset.filter(slug__icontains=slug)

    menu_group = request.GET.get("menu_group", "").strip()
    if menu_group:
        queryset = queryset.filter(menu_group__icontains=menu_group)

    is_active, error_response = parse_bool_filter(
        request.GET.get("is_active", "").strip(),
        field_name="is_active",
        request=request,
    )
    if error_response:
        return queryset, {}, error_response
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    permission_id_raw = request.GET.get("permission_id", "").strip()
    permission_id = None
    if permission_id_raw:
        permission_id, error_response = parse_positive_int(
            permission_id_raw,
            field_name="permission_id",
            default=0,
            request=request,
        )
        if error_response:
            return queryset, {}, error_response

        permission = Permission.objects.select_related("content_type").filter(
            pk=permission_id
        ).first()
        if permission is None:
            queryset = queryset.none()
        else:
            queryset = queryset.filter(
                app_label=permission.content_type.app_label,
                permission_codename=permission.codename,
            )

    return queryset, build_filters_meta(
        {
            "search": search,
            "slug": slug,
            "menu_group": menu_group,
            "is_active": is_active,
            "permission_id": permission_id,
        }
    ), None


def _order_modules(queryset: QuerySet[Module], ordering: str, orm_ordering: str) -> QuerySet[Module]:
    """Aplica a ordenação principal com critérios secundários estáveis."""

    if ordering in {"menu_group", "-menu_group"}:
        return queryset.order_by(orm_ordering, "order", "name", "id")
    if ordering in {"order", "-order"}:
        return queryset.order_by(orm_ordering, "menu_group", "name", "id")
    return queryset.order_by(orm_ordering, "id")


def _log_blocked_module_delete(
    request: HttpRequest,
    module: Module,
    *,
    detail: str,
) -> None:
    """Registra a tentativa bloqueada de exclusão de um módulo pela API."""

    create_audit_log(
        AuditLog.ACTION_API_ACCESS_DENIED,
        instance=module,
        actor=getattr(request, "user", None),
        metadata={
            "event": "api_resource_operation_denied",
            "reason_code": "delete_not_allowed",
            "detail": detail,
            "resource": "panel.modules",
            "action": "delete",
            "status": 400,
        },
    )


@csrf_exempt
@require_api_permission("panel.modules")
def modules_collection(request: HttpRequest) -> HttpResponse:
    """Lista e cria módulos do dashboard via token Bearer da API."""

    if request.method == "GET":
        modules = Module.objects.all()
        modules, filters, error_response = _filter_modules(request, modules)
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
            allowed=MODULE_ORDERING_FIELDS,
            default="menu_group",
        )
        if error_response:
            return error_response

        modules = _order_modules(modules, ordering, orm_ordering)
        paginated_modules, pagination, error_response = paginate_queryset(
            modules,
            request=request,
            page=page,
            page_size=page_size,
        )
        if error_response:
            return error_response

        module_list = list(paginated_modules)
        permission_map = _build_permission_map(module_list)
        return api_collection_response(
            request,
            items=[
                _serialize_module(module, permission_map=permission_map)
                for module in module_list
            ],
            pagination=pagination,
            ordering=ordering,
            filters=filters,
        )

    if request.method == "POST":
        payload, error_response = parse_json_body(request)
        if error_response:
            return error_response

        form = ApiModuleWriteForm(data=_build_module_form_data(payload))
        if not form.is_valid():
            return json_form_errors(request, form)

        module = form.save()
        permission_map = _build_permission_map([module])
        return api_success_response(
            request,
            data=_serialize_module(module, permission_map=permission_map),
            status=201,
        )

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "POST"]},
    )


@csrf_exempt
@require_api_permission("panel.modules")
def module_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Consulta, altera ou remove um módulo do dashboard pela API."""

    module = Module.objects.filter(pk=pk).first()
    if module is None:
        return api_error_response(
            "Módulo não encontrado.",
            code="not_found",
            status=404,
            request=request,
        )

    if request.method == "GET":
        permission_map = _build_permission_map([module])
        return api_success_response(
            request,
            data=_serialize_module(module, permission_map=permission_map),
        )

    if request.method in {"PUT", "PATCH"}:
        payload, error_response = parse_json_body(request)
        if error_response:
            return error_response

        form = ApiModuleWriteForm(
            data=_build_module_form_data(payload, instance=module),
            instance=module,
        )
        if not form.is_valid():
            return json_form_errors(request, form)

        updated_module = form.save()
        permission_map = _build_permission_map([updated_module])
        return api_success_response(
            request,
            data=_serialize_module(updated_module, permission_map=permission_map),
        )

    if request.method == "DELETE":
        block_reason = module.delete_block_reason
        if block_reason:
            _log_blocked_module_delete(request, module, detail=block_reason)
            return api_error_response(
                block_reason,
                code="delete_not_allowed",
                status=400,
                request=request,
            )
        module.delete()
        return HttpResponse(status=204)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "PUT", "PATCH", "DELETE"]},
    )
