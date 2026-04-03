"""Helpers de resposta JSON padronizada para a API versionada."""

from __future__ import annotations

from math import ceil

from django.http import JsonResponse

from .types import PaginationMeta

API_VERSION = "v1"


def build_api_meta(request, extra: dict[str, object] | None = None) -> dict[str, object]:
    """Monta os metadados padrão anexados a cada resposta JSON."""

    meta: dict[str, object] = {
        "request_id": getattr(request, "request_id", ""),
        "version": API_VERSION,
        "path": getattr(request, "path", ""),
        "method": getattr(request, "method", ""),
    }
    if extra:
        meta.update(extra)
    return meta


def build_pagination_meta(
    *,
    page: int,
    page_size: int,
    total_items: int,
) -> PaginationMeta:
    """Resume o estado atual da paginação da resposta."""

    total_pages = ceil(total_items / page_size) if total_items else 0
    has_previous = page > 1 and total_pages > 0
    has_next = total_pages > 0 and page < total_pages

    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_previous": has_previous,
        "has_next": has_next,
        "previous_page": page - 1 if has_previous else None,
        "next_page": page + 1 if has_next else None,
    }


def api_success_response(
    request,
    *,
    data,
    status: int = 200,
    meta: dict[str, object] | None = None,
) -> JsonResponse:
    """Retorna uma resposta JSON de sucesso com envelope padronizado."""

    return JsonResponse(
        {
            "data": data,
            "meta": build_api_meta(request, meta),
        },
        status=status,
    )


def api_collection_response(
    request,
    *,
    items,
    page: int | None = None,
    page_size: int | None = None,
    total_items: int | None = None,
    pagination: PaginationMeta | None = None,
    ordering: str | None = None,
    filters: dict[str, object] | None = None,
    status: int = 200,
) -> JsonResponse:
    """Retorna uma resposta de coleção com paginação, filtros e ordenação."""

    if pagination is None:
        if page is None or page_size is None or total_items is None:
            raise ValueError(
                "page, page_size e total_items são obrigatórios quando pagination não é informado."
            )
        pagination = build_pagination_meta(
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

    meta: dict[str, object] = {"pagination": pagination}
    if ordering:
        meta["ordering"] = ordering
    if filters:
        meta["filters"] = filters

    return api_success_response(request, data=items, status=status, meta=meta)


def api_deleted_response(
    request,
    *,
    resource: str,
    object_id: int,
) -> JsonResponse:
    """Retorna um envelope padronizado para exclusões bem-sucedidas."""

    return api_success_response(
        request,
        data={
            "deleted": True,
            "resource": resource,
            "id": object_id,
        },
    )


def api_error_response(
    detail: str,
    *,
    code: str,
    status: int,
    request=None,
    fields: dict[str, object] | None = None,
    meta: dict[str, object] | None = None,
    extra_error: dict[str, object] | None = None,
) -> JsonResponse:
    """Retorna um erro JSON padronizado para os consumidores da API."""

    error_payload: dict[str, object] = {
        "detail": detail,
        "code": code,
    }
    if fields:
        error_payload["fields"] = fields
    if extra_error:
        error_payload.update(extra_error)

    payload: dict[str, object] = {"error": error_payload}
    if request is not None:
        payload["meta"] = build_api_meta(request, meta)
    elif meta:
        payload["meta"] = meta

    return JsonResponse(payload, status=status)
