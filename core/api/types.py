"""Tipos compartilhados entre autenticação, payloads e respostas da API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypedDict

from django.http import HttpRequest
from django.utils.functional import Promise

DisplayLabel: TypeAlias = str | Promise
ApiCrudAction: TypeAlias = Literal["create", "read", "update", "delete"]
ApiPermissionKey: TypeAlias = Literal[
    "can_create",
    "can_read",
    "can_update",
    "can_delete",
]
ApiActionOption: TypeAlias = tuple[ApiCrudAction, str, ApiPermissionKey]
ApiResourceOption: TypeAlias = tuple[str, DisplayLabel]


class ApiPermissionFlags(TypedDict):
    """Representa as flags CRUD persistidas por recurso da API."""

    can_create: bool
    can_read: bool
    can_update: bool
    can_delete: bool


ApiPermissionMatrix: TypeAlias = dict[str, ApiPermissionFlags]


class ApiAccessValues(TypedDict):
    """Payload tipado com o estado efetivo de acesso à API de um usuário."""

    api_enabled: bool
    permissions: ApiPermissionMatrix


class PaginationMeta(TypedDict):
    """Metadados de paginação anexados às respostas de coleção."""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool
    previous_page: int | None
    next_page: int | None


class DocsOperation(TypedDict):
    """Operação simplificada usada para renderizar a página de docs."""

    id: str
    method: str
    path: str
    summary: str
    code_samples: dict[str, str]


class DocsSection(TypedDict):
    """Seção renderizável da documentação HTML da API."""

    id: str
    label: str
    base_url: str
    operations: list[DocsOperation]


if TYPE_CHECKING:
    from ..models import ApiToken
    from .auth import ApiAuthenticationResult


class ApiHttpRequest(HttpRequest):
    """HttpRequest enriquecido pelos middlewares e decorators da API."""

    user: Any
    _cached_user: Any
    api_token: ApiToken | None
    api_auth_result: ApiAuthenticationResult | None
    api_permission_action: str
    request_id: str
