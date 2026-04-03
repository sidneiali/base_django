"""Navegacao relacionada do detalhe de auditoria no painel."""

from __future__ import annotations

from dataclasses import dataclass

from core.models import AuditLog
from django.db.models import QuerySet
from django.http import QueryDict
from django.urls import reverse

from .querying import related_base_queryset

RELATED_AUDIT_PREVIEW_LIMIT = 5


@dataclass(frozen=True, slots=True)
class RelatedAuditPreviewItem:
    """Representa um item do preview de eventos relacionados no detalhe."""

    audit_log: AuditLog
    detail_url: str


@dataclass(frozen=True, slots=True)
class RelatedAuditSection:
    """Agrupa atalhos e previews de eventos relacionados no detalhe."""

    scope: str
    title: str
    count: int
    count_label: str
    list_url: str
    list_label: str
    empty_message: str
    items: list[RelatedAuditPreviewItem]


def build_related_actor_section(audit_log: AuditLog) -> RelatedAuditSection | None:
    """Monta o bloco de eventos relacionados ao mesmo ator."""

    actor_display = audit_log.actor_display
    if actor_display == "-":
        return None

    related_logs = related_base_queryset().exclude(pk=audit_log.pk)
    if audit_log.actor_id:
        related_logs = related_logs.filter(actor_id=audit_log.actor_id)
    elif audit_log.actor_identifier:
        related_logs = related_logs.filter(actor_identifier=audit_log.actor_identifier)
    else:
        return None

    return _build_related_section(
        scope="actor",
        title="Mesmo ator",
        queryset=related_logs,
        list_url=_build_url_with_mapping(
            reverse("panel_audit_logs_list"),
            {"actor": actor_display},
        ),
        list_label="Filtrar por ator",
        empty_message="Nenhum outro evento encontrado para este ator.",
        detail_query={"actor": actor_display},
        singular_count_label="1 outro evento recente",
        plural_count_label="{count} outros eventos recentes",
    )


def build_related_request_section(audit_log: AuditLog) -> RelatedAuditSection | None:
    """Monta o bloco de eventos relacionados a mesma requisicao."""

    request_id = audit_log.request_id
    if not request_id:
        return None

    related_logs = related_base_queryset().exclude(pk=audit_log.pk).filter(
        metadata__request_id=request_id
    )

    return _build_related_section(
        scope="request",
        title="Mesma requisição",
        queryset=related_logs,
        list_url=_build_url_with_mapping(
            reverse("panel_audit_logs_list"),
            {"object_query": request_id},
        ),
        list_label="Filtrar por request ID",
        empty_message="Nenhum outro evento encontrado para esta requisição.",
        detail_query={"object_query": request_id},
        singular_count_label="1 outro evento recente",
        plural_count_label="{count} outros eventos recentes",
    )


def _build_related_section(
    *,
    scope: str,
    title: str,
    queryset: QuerySet[AuditLog],
    list_url: str,
    list_label: str,
    empty_message: str,
    detail_query: dict[str, str],
    singular_count_label: str,
    plural_count_label: str,
) -> RelatedAuditSection:
    """Materializa um bloco de navegacao relacionada para o detalhe."""

    count = queryset.count()
    preview_logs = list(queryset[:RELATED_AUDIT_PREVIEW_LIMIT])
    items = [
        RelatedAuditPreviewItem(
            audit_log=related_log,
            detail_url=_build_url_with_mapping(
                reverse("panel_audit_log_detail", args=[related_log.pk]),
                detail_query,
            ),
        )
        for related_log in preview_logs
    ]

    return RelatedAuditSection(
        scope=scope,
        title=title,
        count=count,
        count_label=_format_related_count_label(
            count,
            singular=singular_count_label,
            plural=plural_count_label,
        ),
        list_url=list_url,
        list_label=list_label,
        empty_message=empty_message,
        items=items,
    )


def _format_related_count_label(count: int, *, singular: str, plural: str) -> str:
    """Gera um rotulo curto para a contagem de eventos relacionados."""

    if count == 1:
        return singular
    return plural.format(count=count)


def _build_url_with_mapping(path: str, params: dict[str, str]) -> str:
    """Acopla uma query string simples a uma URL base."""

    return path + _build_querystring_from_mapping(params)


def _build_querystring_from_mapping(params: dict[str, str]) -> str:
    """Monta uma query string simples a partir de um dicionario limpo."""

    query = QueryDict(mutable=True)
    for key, value in params.items():
        if value:
            query[key] = value

    encoded = query.urlencode()
    if not encoded:
        return ""
    return f"?{encoded}"
