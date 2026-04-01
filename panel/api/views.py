"""Endpoints JSON protegidos do domínio de usuários do painel."""

from __future__ import annotations

import json
from json import JSONDecodeError

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
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .forms import ApiUserWriteForm

USER_ORDERING_FIELDS = {
    "username": "username",
    "-username": "-username",
    "email": "email",
    "-email": "-email",
    "date_joined": "date_joined",
    "-date_joined": "-date_joined",
    "id": "id",
    "-id": "-id",
}


def _parse_json_body(request: HttpRequest) -> tuple[dict, JsonResponse | None]:
    """Converte o corpo JSON da requisição em dicionário Python."""

    if not request.body:
        return {}, None

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError):
        return {}, api_error_response(
            "O corpo da requisição deve ser um JSON válido.",
            code="invalid_json",
            status=400,
            request=request,
        )

    if not isinstance(payload, dict):
        return {}, api_error_response(
            "O corpo JSON deve ser um objeto com pares chave/valor.",
            code="invalid_payload",
            status=400,
            request=request,
        )

    return payload, None


def _serialize_user(user: User) -> dict[str, object]:
    """Resume o usuário em um payload legível para os consumidores da API."""

    return {
        "id": user.pk,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": user.is_active,
        "groups": [
            {"id": group.pk, "name": group.name}
            for group in user.groups.order_by("name")
        ],
    }


def _json_form_errors(request: HttpRequest, form: ApiUserWriteForm) -> JsonResponse:
    """Retorna erros de validação do formulário em formato JSON padronizado."""

    return api_error_response(
        "Os dados enviados são inválidos.",
        code="validation_error",
        status=400,
        request=request,
        fields=form.errors.get_json_data(),
    )


def _build_user_form_data(payload: dict, *, instance: User | None = None) -> dict[str, object]:
    """Normaliza o payload da API em dados compatíveis com o formulário."""

    existing_groups = []
    if instance is not None:
        existing_groups = list(instance.groups.values_list("pk", flat=True))

    return {
        "username": payload.get("username", instance.username if instance else ""),
        "first_name": payload.get("first_name", instance.first_name if instance else ""),
        "last_name": payload.get("last_name", instance.last_name if instance else ""),
        "email": payload.get("email", instance.email if instance else ""),
        "is_active": payload.get("is_active", instance.is_active if instance else True),
        "groups": payload.get("groups", existing_groups),
        "password": payload.get("password", ""),
    }


def _filter_users(
    request: HttpRequest,
    queryset,
) -> tuple[object, dict[str, object], JsonResponse | None]:
    """Aplica filtros explícitos à coleção de usuários."""

    search = request.GET.get("search", "").strip() or request.GET.get("q", "").strip()
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    username = request.GET.get("username", "").strip()
    if username:
        queryset = queryset.filter(username__icontains=username)

    email = request.GET.get("email", "").strip()
    if email:
        queryset = queryset.filter(email__icontains=email)

    is_active, error_response = parse_bool_filter(
        request.GET.get("is_active", "").strip(),
        field_name="is_active",
        request=request,
    )
    if error_response:
        return queryset, {}, error_response
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    group_id_raw = request.GET.get("group_id", "").strip()
    group_id = None
    if group_id_raw:
        group_id, error_response = parse_positive_int(
            group_id_raw,
            field_name="group_id",
            default=0,
            request=request,
        )
        if error_response:
            return queryset, {}, error_response
        queryset = queryset.filter(groups__id=group_id).distinct()

    return queryset, build_filters_meta(
        {
            "search": search,
            "username": username,
            "email": email,
            "is_active": is_active,
            "group_id": group_id,
        }
    ), None


@csrf_exempt
@require_api_permission("panel.users")
def users_collection(request: HttpRequest) -> HttpResponse:
    """Lista e cria usuários comuns via token Bearer da API."""

    if request.method == "GET":
        users = (
            User.objects.filter(is_superuser=False)
            .prefetch_related("groups")
        )
        users, filters, error_response = _filter_users(request, users)
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
            allowed=USER_ORDERING_FIELDS,
            default="username",
        )
        if error_response:
            return error_response

        users = users.order_by(orm_ordering, "id")
        paginated_users, pagination, error_response = paginate_queryset(
            users,
            request=request,
            page=page,
            page_size=page_size,
        )
        if error_response:
            return error_response

        return api_collection_response(
            request,
            items=[_serialize_user(user) for user in paginated_users],
            pagination=pagination,
            ordering=ordering,
            filters=filters,
        )

    if request.method == "POST":
        payload, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        form = ApiUserWriteForm(
            data=_build_user_form_data(payload),
            require_password=True,
        )
        if not form.is_valid():
            return _json_form_errors(request, form)

        user = form.save()
        return api_success_response(request, data=_serialize_user(user), status=201)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "POST"]},
    )


@csrf_exempt
@require_api_permission("panel.users")
def user_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Consulta, altera ou remove um usuário comum pela API."""

    user = User.objects.filter(pk=pk, is_superuser=False).prefetch_related("groups").first()
    if user is None:
        return api_error_response(
            "Usuário não encontrado.",
            code="not_found",
            status=404,
            request=request,
        )

    if request.method == "GET":
        return api_success_response(request, data=_serialize_user(user))

    if request.method in {"PUT", "PATCH"}:
        payload, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        form = ApiUserWriteForm(
            data=_build_user_form_data(payload, instance=user),
            instance=user,
        )
        if not form.is_valid():
            return _json_form_errors(request, form)

        updated_user = form.save()
        return api_success_response(request, data=_serialize_user(updated_user))

    if request.method == "DELETE":
        user.delete()
        return HttpResponse(status=204)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "PUT", "PATCH", "DELETE"]},
    )
