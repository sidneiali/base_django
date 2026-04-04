"""Endpoints JSON protegidos do domínio de grupos do painel."""

from __future__ import annotations

from typing import TypedDict, cast

from core.api.auth import authorize_api_request
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
    api_deleted_response,
    api_error_response,
    api_success_response,
)
from django.contrib.auth.models import Group, Permission
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI, Schema

from ..constants import PROTECTED_GROUP_NAMES
from .forms import ApiGroupWriteForm
from .shared import json_form_errors, parse_json_body

GROUP_ORDERING_FIELDS = {
    "name": "name",
    "-name": "-name",
    "id": "id",
    "-id": "-id",
}

GROUPS_TAG = ["Grupos do painel"]
GROUPS_BASE_URL = "/api/v1/panel/groups/"
GROUPS_COLLECTION_CODE_SAMPLES = [
    {
        "lang": "curl",
        "source": 'curl -H "Authorization: Bearer SEU_TOKEN" '
        "__BASE_URL__/api/v1/panel/groups/",
    },
    {
        "lang": "python",
        "source": "import requests\n"
        "\n"
        "response = requests.get(\n"
        '    "__BASE_URL__/api/v1/panel/groups/",\n'
        '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
        "    timeout=30,\n"
        ")\n"
        "\n"
        "print(response.status_code)\n"
        "print(response.json())",
    },
]
GROUPS_CREATE_CODE_SAMPLES = [
    {
        "lang": "curl",
        "source": "curl -X POST __BASE_URL__/api/v1/panel/groups/ \\\n"
        '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d "{\\"name\\":\\"Grupo API\\",\\"permissions\\":[1]}"',
    },
    {
        "lang": "python",
        "source": "import requests\n"
        "\n"
        "payload = {\n"
        '    "name": "Grupo API",\n'
        '    "permissions": [1],\n'
        "}\n"
        "\n"
        "response = requests.post(\n"
        '    "__BASE_URL__/api/v1/panel/groups/",\n'
        '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
        "    json=payload,\n"
        "    timeout=30,\n"
        ")\n"
        "\n"
        "print(response.status_code)\n"
        "print(response.json())",
    },
]
GROUPS_DETAIL_CODE_SAMPLES = [
    {
        "lang": "curl",
        "source": 'curl -H "Authorization: Bearer SEU_TOKEN" '
        "__BASE_URL__/api/v1/panel/groups/1/",
    },
    {
        "lang": "python",
        "source": "import requests\n"
        "\n"
        "response = requests.get(\n"
        '    "__BASE_URL__/api/v1/panel/groups/1/",\n'
        '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
        "    timeout=30,\n"
        ")\n"
        "\n"
        "print(response.status_code)\n"
        "print(response.json())",
    },
]
GROUPS_UPDATE_CODE_SAMPLES = [
    {
        "lang": "curl",
        "source": "curl -X PATCH __BASE_URL__/api/v1/panel/groups/1/ \\\n"
        '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d "{\\"name\\":\\"Grupo API Atualizado\\",\\"permissions\\":[1]}"',
    },
    {
        "lang": "python",
        "source": "import requests\n"
        "\n"
        "payload = {\n"
        '    "name": "Grupo API Atualizado",\n'
        '    "permissions": [1],\n'
        "}\n"
        "\n"
        "response = requests.patch(\n"
        '    "__BASE_URL__/api/v1/panel/groups/1/",\n'
        '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
        "    json=payload,\n"
        "    timeout=30,\n"
        ")\n"
        "\n"
        "print(response.status_code)\n"
        "print(response.json())",
    },
]
GROUPS_DELETE_CODE_SAMPLES = [
    {
        "lang": "curl",
        "source": "curl -X DELETE __BASE_URL__/api/v1/panel/groups/1/ \\\n"
        '  -H "Authorization: Bearer SEU_TOKEN"',
    },
    {
        "lang": "python",
        "source": "import requests\n"
        "\n"
        "response = requests.delete(\n"
        '    "__BASE_URL__/api/v1/panel/groups/1/",\n'
        '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
        "    timeout=30,\n"
        ")\n"
        "\n"
        "print(response.status_code)\n"
        "print(response.json())",
    },
]


class NinjaApiMetaSchema(Schema):
    """Metadados padrão anexados às respostas do piloto Ninja."""

    request_id: str
    version: str
    path: str
    method: str


class NinjaPanelGroupPermissionSchema(Schema):
    """Permissão serializada do grupo na superfície Ninja."""

    id: int
    codename: str
    name: str
    app_label: str
    model: str


class NinjaPanelGroupSchema(Schema):
    """Payload de um grupo editável do painel."""

    id: int
    name: str
    permissions_count: int
    permissions: list[NinjaPanelGroupPermissionSchema]


class NinjaCollectionMetaSchema(NinjaApiMetaSchema):
    """Metadados adicionais da listagem de grupos."""

    pagination: dict[str, object]
    ordering: str | None = None
    filters: dict[str, object] | None = None


class NinjaPanelGroupEnvelopeSchema(Schema):
    """Envelope de detalhe/criação/edição do grupo."""

    data: NinjaPanelGroupSchema
    meta: NinjaApiMetaSchema


class NinjaPanelGroupListEnvelopeSchema(Schema):
    """Envelope da listagem de grupos."""

    data: list[NinjaPanelGroupSchema]
    meta: NinjaCollectionMetaSchema


class NinjaDeleteDataSchema(Schema):
    """Payload de exclusão bem-sucedida."""

    deleted: bool
    resource: str
    id: int


class NinjaDeleteEnvelopeSchema(Schema):
    """Envelope de exclusão bem-sucedida."""

    data: NinjaDeleteDataSchema
    meta: NinjaApiMetaSchema


class NinjaOpenApiFragment(TypedDict):
    """Fragmento parcial da spec OpenAPI gerado pelo piloto Ninja."""

    paths: dict[str, dict[str, object]]
    components: dict[str, object]


def _build_permission_schema(permission: Permission) -> NinjaPanelGroupPermissionSchema:
    """Converte uma permissão do Django no schema tipado do endpoint."""

    return NinjaPanelGroupPermissionSchema(
        id=permission.pk,
        codename=permission.codename,
        name=permission.name,
        app_label=permission.content_type.app_label,
        model=permission.content_type.model,
    )


def _serialize_permission(permission: Permission) -> dict[str, object]:
    """Resume uma permissão em um payload legível para a API."""

    return _build_permission_schema(permission).model_dump(mode="json")


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
    return NinjaPanelGroupSchema(
        id=group.pk,
        name=group.name,
        permissions_count=len(permissions),
        permissions=[_build_permission_schema(permission) for permission in permissions],
    ).model_dump(mode="json")


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


def _groups_collection_parameters() -> list[dict[str, object]]:
    """Retorna os parâmetros OpenAPI documentados da coleção."""

    return [
        {
            "name": "search",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
        },
        {
            "name": "name",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
        },
        {
            "name": "permission_id",
            "in": "query",
            "required": False,
            "schema": {"type": "integer", "minimum": 1},
        },
        {
            "name": "ordering",
            "in": "query",
            "required": False,
            "schema": {"type": "string", "enum": ["name", "-name", "id", "-id"]},
        },
        {
            "name": "page",
            "in": "query",
            "required": False,
            "schema": {"type": "integer", "minimum": 1},
        },
        {
            "name": "page_size",
            "in": "query",
            "required": False,
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    ]


def _group_detail_parameters() -> list[dict[str, object]]:
    """Retorna o parâmetro OpenAPI documentado do detalhe."""

    return [
        {
            "name": "id",
            "in": "path",
            "required": True,
            "schema": {"type": "integer"},
        }
    ]


_GROUPS_API = NinjaAPI(urls_namespace=None, docs_url=None, openapi_url=None)


@_GROUPS_API.get(
    "/groups/",
    url_name="api_panel_groups_collection",
    operation_id="api_groups_list",
    summary="Listar grupos",
    description="Lista grupos editáveis do painel, excluindo grupos protegidos.",
    tags=GROUPS_TAG,
    response=NinjaPanelGroupListEnvelopeSchema,
    openapi_extra={
        "security": [{"BearerAuth": []}],
        "x-base-url": GROUPS_BASE_URL,
        "x-codeSamples": GROUPS_COLLECTION_CODE_SAMPLES,
        "parameters": _groups_collection_parameters(),
    },
)
def _groups_collection_get(request: HttpRequest) -> HttpResponse:
    """Lista grupos editáveis via token Bearer da API."""

    error_response = authorize_api_request(
        request,
        resource="panel.groups",
        action="read",
    )
    if error_response is not None:
        return error_response

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


@_GROUPS_API.post(
    "/groups/",
    url_name="api_panel_groups_collection",
    operation_id="api_groups_create",
    summary="Criar grupo",
    description="Cria um grupo editável do painel com permissões visíveis.",
    tags=GROUPS_TAG,
    response={201: NinjaPanelGroupEnvelopeSchema},
    openapi_extra={
        "security": [{"BearerAuth": []}],
        "x-base-url": GROUPS_BASE_URL,
        "x-codeSamples": GROUPS_CREATE_CODE_SAMPLES,
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/PanelGroupWriteInput"}
                }
            },
        },
    },
)
def _groups_collection_post(request: HttpRequest) -> HttpResponse:
    """Cria grupos editáveis via token Bearer da API."""

    error_response = authorize_api_request(
        request,
        resource="panel.groups",
        action="create",
    )
    if error_response is not None:
        return error_response

    payload, error_response = parse_json_body(request)
    if error_response:
        return error_response

    form = ApiGroupWriteForm(data=_build_group_form_data(payload))
    if not form.is_valid():
        return json_form_errors(request, form)

    group = form.save()
    group = Group.objects.prefetch_related("permissions__content_type").get(pk=group.pk)
    return api_success_response(request, data=_serialize_group(group), status=201)


@_GROUPS_API.get(
    "/groups/{id}/",
    url_name="api_panel_group_detail",
    operation_id="api_groups_detail",
    summary="Detalhar grupo",
    description="Retorna um grupo editável específico do painel.",
    tags=GROUPS_TAG,
    response=NinjaPanelGroupEnvelopeSchema,
    openapi_extra={
        "security": [{"BearerAuth": []}],
        "x-base-url": GROUPS_BASE_URL,
        "x-codeSamples": GROUPS_DETAIL_CODE_SAMPLES,
        "parameters": _group_detail_parameters(),
    },
)
def _group_detail_get(request: HttpRequest, id: int) -> HttpResponse:
    """Consulta um grupo editável pela API."""

    error_response = authorize_api_request(
        request,
        resource="panel.groups",
        action="read",
    )
    if error_response is not None:
        return error_response

    group = (
        Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)
        .filter(pk=id)
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

    return api_success_response(request, data=_serialize_group(group))


@_GROUPS_API.api_operation(
    ["PUT", "PATCH"],
    "/groups/{id}/",
    url_name="api_panel_group_detail",
    operation_id="api_groups_update",
    summary="Atualizar grupo",
    description="Atualiza um grupo editável do painel.",
    tags=GROUPS_TAG,
    response=NinjaPanelGroupEnvelopeSchema,
    openapi_extra={
        "security": [{"BearerAuth": []}],
        "x-base-url": GROUPS_BASE_URL,
        "x-codeSamples": GROUPS_UPDATE_CODE_SAMPLES,
        "parameters": _group_detail_parameters(),
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/PanelGroupWritePartialInput"
                    }
                }
            },
        },
    },
)
def _group_detail_patch(request: HttpRequest, id: int) -> HttpResponse:
    """Atualiza um grupo editável pela API."""

    error_response = authorize_api_request(
        request,
        resource="panel.groups",
        action="update",
    )
    if error_response is not None:
        return error_response

    group = (
        Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)
        .filter(pk=id)
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


@_GROUPS_API.delete(
    "/groups/{id}/",
    url_name="api_panel_group_detail",
    operation_id="api_groups_delete",
    summary="Excluir grupo",
    description="Remove um grupo editável do painel.",
    tags=GROUPS_TAG,
    response=NinjaDeleteEnvelopeSchema,
    openapi_extra={
        "security": [{"BearerAuth": []}],
        "x-base-url": GROUPS_BASE_URL,
        "x-codeSamples": GROUPS_DELETE_CODE_SAMPLES,
        "parameters": _group_detail_parameters(),
    },
)
def _group_detail_delete(request: HttpRequest, id: int) -> HttpResponse:
    """Exclui um grupo editável pela API."""

    error_response = authorize_api_request(
        request,
        resource="panel.groups",
        action="delete",
    )
    if error_response is not None:
        return error_response

    group = (
        Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)
        .filter(pk=id)
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

    group_id = group.pk
    group.delete()
    return api_deleted_response(
        request,
        resource="panel.groups",
        object_id=group_id,
    )


def _get_ninja_callback(url_name: str, occurrence: int = 0):
    """Extrai um callback do Ninja pelo nome e ordem de registro."""

    matches = [
        pattern.callback
        for pattern in _GROUPS_API.urls[0]
        if getattr(pattern, "name", None) == url_name
    ]
    if occurrence >= len(matches):
        raise RuntimeError(f"Callback Ninja não encontrado: {url_name}#{occurrence}")
    return matches[occurrence]


_GROUPS_COLLECTION_GET_CALLBACK = _get_ninja_callback(
    "api_panel_groups_collection",
    occurrence=0,
)
_GROUPS_COLLECTION_POST_CALLBACK = _get_ninja_callback(
    "api_panel_groups_collection",
    occurrence=1,
)
_GROUP_DETAIL_GET_CALLBACK = _get_ninja_callback(
    "api_panel_group_detail",
    occurrence=0,
)
_GROUP_DETAIL_PATCH_CALLBACK = _get_ninja_callback(
    "api_panel_group_detail",
    occurrence=1,
)
_GROUP_DETAIL_DELETE_CALLBACK = _get_ninja_callback(
    "api_panel_group_detail",
    occurrence=2,
)


def groups_collection(request: HttpRequest) -> HttpResponse:
    """Lista ou cria grupos editáveis do painel via callbacks Ninja."""

    if request.method == "GET":
        return _GROUPS_COLLECTION_GET_CALLBACK(request)
    if request.method == "POST":
        return _GROUPS_COLLECTION_POST_CALLBACK(request)
    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "POST"]},
    )


def group_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Consulta, atualiza ou remove um grupo editável via callbacks Ninja."""

    if request.method == "GET":
        return _GROUP_DETAIL_GET_CALLBACK(request, id=pk)
    if request.method in {"PUT", "PATCH"}:
        return _GROUP_DETAIL_PATCH_CALLBACK(request, id=pk)
    if request.method == "DELETE":
        return _GROUP_DETAIL_DELETE_CALLBACK(request, id=pk)
    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
        request=request,
        extra_error={"allowed_methods": ["GET", "PUT", "PATCH", "DELETE"]},
    )


def build_groups_ninja_openapi_fragment() -> NinjaOpenApiFragment:
    """Gera o fragmento OpenAPI do piloto Ninja para grupos."""

    schema = cast(dict[str, object], _GROUPS_API.get_openapi_schema(path_prefix="/api/v1/panel"))
    return {
        "paths": cast(dict[str, dict[str, object]], schema.get("paths", {})),
        "components": cast(dict[str, object], schema.get("components", {})),
    }
