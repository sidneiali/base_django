"""Helpers de query string, filtros, paginação e ordenação da API."""

from __future__ import annotations

from datetime import date

from django.http import JsonResponse
from django.utils.dateparse import parse_date

from .api_responses import api_error_response, build_pagination_meta

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def build_filters_meta(filters: dict[str, object]) -> dict[str, object]:
    """Remove filtros vazios e preserva apenas os valores aplicados."""

    cleaned: dict[str, object] = {}
    for key, value in filters.items():
        if value in ("", None, [], ()):
            continue
        cleaned[key] = value
    return cleaned


def parse_positive_int(
    raw_value: str,
    *,
    field_name: str,
    request,
    default: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> tuple[int, JsonResponse | None]:
    """Valida inteiros positivos usados em paginação da API."""

    if not raw_value:
        return default, None

    try:
        value = int(raw_value)
    except ValueError:
        return 0, api_error_response(
            f"O parâmetro {field_name} deve ser um número inteiro.",
            code="invalid_query_parameter",
            status=400,
            request=request,
            extra_error={"parameter": field_name},
        )

    if value < minimum:
        return 0, api_error_response(
            f"O parâmetro {field_name} deve ser maior ou igual a {minimum}.",
            code="invalid_query_parameter",
            status=400,
            request=request,
            extra_error={"parameter": field_name},
        )

    if maximum is not None and value > maximum:
        return 0, api_error_response(
            f"O parâmetro {field_name} deve ser menor ou igual a {maximum}.",
            code="invalid_query_parameter",
            status=400,
            request=request,
            extra_error={"parameter": field_name},
        )

    return value, None


def parse_date_filter(
    raw_value: str,
    *,
    field_name: str,
    request,
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
            request=request,
            extra_error={"parameter": field_name},
        )

    return parsed, None


def parse_bool_filter(
    raw_value: str,
    *,
    field_name: str,
    request,
) -> tuple[bool | None, JsonResponse | None]:
    """Converte filtros booleanos aceitando grafias comuns da web."""

    if not raw_value:
        return None, None

    normalized = raw_value.strip().lower()
    if normalized in TRUE_VALUES:
        return True, None
    if normalized in FALSE_VALUES:
        return False, None

    return None, api_error_response(
        f"O parâmetro {field_name} deve ser true ou false.",
        code="invalid_query_parameter",
        status=400,
        request=request,
        extra_error={"parameter": field_name},
    )


def parse_ordering(
    raw_value: str,
    *,
    request,
    allowed: dict[str, str],
    default: str,
    field_name: str = "ordering",
) -> tuple[str, str, JsonResponse | None]:
    """Valida o parâmetro de ordenação e devolve token e campo ORM."""

    token = raw_value.strip() if raw_value else default
    orm_ordering = allowed.get(token)
    if orm_ordering is None:
        return "", "", api_error_response(
            f"O parâmetro {field_name} é inválido para este endpoint.",
            code="invalid_query_parameter",
            status=400,
            request=request,
            extra_error={
                "parameter": field_name,
                "allowed_values": list(allowed.keys()),
            },
        )

    return token, orm_ordering, None


def paginate_queryset(
    queryset,
    *,
    request,
    page: int,
    page_size: int,
) -> tuple[object, dict[str, object], JsonResponse | None]:
    """Aplica paginação ao queryset e valida páginas fora do intervalo."""

    total_items = queryset.count()
    pagination = build_pagination_meta(
        page=page,
        page_size=page_size,
        total_items=total_items,
    )

    total_pages = pagination["total_pages"]
    if total_pages and page > total_pages:
        return queryset.none(), pagination, api_error_response(
            "O parâmetro page aponta para uma página inexistente.",
            code="page_out_of_range",
            status=400,
            request=request,
            extra_error={
                "parameter": "page",
                "total_pages": total_pages,
            },
        )

    start = (page - 1) * page_size
    end = start + page_size
    return queryset[start:end], pagination, None
