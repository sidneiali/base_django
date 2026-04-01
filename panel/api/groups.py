"""Endpoints JSON protegidos do domínio de grupos do painel."""

from __future__ import annotations

from core.api.auth import require_api_permission
from core.api.queries import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    build_filters_meta,
    paginate_queryset,
    parse_ordering,
    parse_positive_int,
)
from core.api.responses import (
    api_collection_response,
    api_error_response,
    api_success_response,
)
from django.contrib.auth.models import Group, Permission
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from ..constants import PROTECTED_GROUP_NAMES
from .forms import ApiGroupWriteForm
from .shared import json_form_errors, parse_json_body

GROUP_ORDERING_FIELDS = {
    "name": "name",
    "-name": "-name",
    "id": "id",
    "-id": "-id",
}


def _serialize_permission(permission: Permission) -> dict[str, object]:
    """Resume uma permissão em um payload legível para a API."""

    return {
        "id": permission.pk,
        "codename": permission.codename,
        "name": permission.name,
        "app_label": permission.content_type.app_label,
        "model": permission.content_type.model,
    }


def _serialize_group(group: Group) -> dict[str, object]:
    """Resume um grupo editável do painel em formato JSON."""

    permissions = sorted(
        group.permissions.all(),
        key=lambda item: (
            item.content_type.app_label,
            item.content_type.model,
            item.codename,
        ),
    )
    return {
        "id": group.pk,
        "name": group.name,
        "permissions_count": len(permissions),
        "permissions": [_serialize_permission(permission) for permission in permissions],
    }


def _build_group_form_data(
    payload: dict[str, object],
    *,
    instance: Group | None = None,
) -> dict[str, object]:
    """Normaliza o payload da API em dados compatíveis com o formulário."""

    existing_permissions = []
    if instance is not None:
        existing_permissions = list(instance.permissions.values_list("pk", flat=True))

    return {
        "name": payload.get("name", instance.name if instance else ""),
        "permissions": payload.get("permissions", existing_permissions),
    }


def _filter_groups(
    request: HttpRequest,
    queryset: QuerySet[Group],
) -> tuple[QuerySet[Group], dict[str, object], HttpResponse | None]:
    """Aplica filtros explícitos à coleção de grupos do painel."""

    search = request.GET.get("search", "").strip() or request.GET.get("q", "").strip()
    if search:
        queryset = queryset.filter(name__icontains=search)

    name = request.GET.get("name", "").strip()
    if name:
        queryset = queryset.filter(name__icontains=name)

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
        queryset = queryset.filter(permissions__id=permission_id).distinct()

    return queryset, build_filters_meta(
        {
            "search": search,
            "name": name,
            "permission_id": permission_id,
        }
    ), None


@csrf_exempt
@require_api_permission("panel.groups")
def groups_collection(request: HttpRequest) -> HttpResponse:
    """Lista e cria grupos editáveis via token Bearer da API."""

    if request.method == "GET":
        groups = Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES).prefetch_related(
            "permissions__content_type"
        )
        groups, filters, error_response = _filter_groups(request, groups)
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
            allowed=GROUP_ORDERING_FIELDS,
            default="name",
        )
        if error_response:
            return error_response

        groups = groups.order_by(orm_ordering, "id")
        paginated_groups, pagination, error_response = paginate_queryset(
            groups,
            request=request,
            page=page,
            page_size=page_size,
        )
        if error_response:
            return error_response

        return api_collection_response(
            request,
            items=[_serialize_group(group) for group in paginated_groups],
            pagination=pagination,
            ordering=ordering,
            filters=filters,
        )

    if request.method == "POST":
        payload, error_response = parse_json_body(request)
        if error_response:
            return error_response

        form = ApiGroupWriteForm(data=_build_group_form_data(payload))
        if not form.is_valid():
            return json_form_errors(request, form)

        group = form.save()
        return api_success_response(request, data=_serialize_group(group), status=201)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "POST"]},
    )


@csrf_exempt
@require_api_permission("panel.groups")
def group_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Consulta, altera ou remove um grupo editável pela API."""

    group = (
        Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)
        .filter(pk=pk)
        .prefetch_related("permissions__content_type")
        .first()
    )
    if group is None:
        return api_error_response(
            "Grupo não encontrado.",
            code="not_found",
            status=404,
            request=request,
        )

    if request.method == "GET":
        return api_success_response(request, data=_serialize_group(group))

    if request.method in {"PUT", "PATCH"}:
        payload, error_response = parse_json_body(request)
        if error_response:
            return error_response

        form = ApiGroupWriteForm(
            data=_build_group_form_data(payload, instance=group),
            instance=group,
        )
        if not form.is_valid():
            return json_form_errors(request, form)

        updated_group = form.save()
        updated_group = Group.objects.prefetch_related("permissions__content_type").get(
            pk=updated_group.pk
        )
        return api_success_response(request, data=_serialize_group(updated_group))

    if request.method == "DELETE":
        group.delete()
        return HttpResponse(status=204)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "PUT", "PATCH", "DELETE"]},
    )
