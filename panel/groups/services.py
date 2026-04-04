"""Serviços do domínio de grupos do painel."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db.models import QuerySet

from ..autonomy import GROUP_SCOPE_BLOCK_REASON, group_within_actor_scope
from ..constants import PROTECTED_GROUP_NAMES


@dataclass(frozen=True, slots=True)
class PanelGroupListRow:
    """Estado renderizável de uma linha da listagem de grupos."""

    group: Group
    management_block_reason: str


def editable_groups_queryset() -> QuerySet[Group]:
    """Retorna apenas os grupos que o painel pode gerenciar diretamente."""

    return Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)


def get_panel_group_management_block_reason(
    group: Group,
    *,
    acting_user,
) -> str:
    """Explica por que o grupo não pode ser operado por este operador."""

    if not group_within_actor_scope(group, acting_user=acting_user):
        return GROUP_SCOPE_BLOCK_REASON
    return ""


def build_panel_group_list_rows(
    groups,
    *,
    acting_user,
) -> list[PanelGroupListRow]:
    """Monta as linhas renderizáveis da listagem de grupos."""

    rows: list[PanelGroupListRow] = []
    for group in groups:
        rows.append(
            PanelGroupListRow(
                group=group,
                management_block_reason=get_panel_group_management_block_reason(
                    group,
                    acting_user=acting_user,
                ),
            )
        )
    return rows


def delete_panel_group(group: Group) -> None:
    """Remove um grupo editável do painel."""

    group.delete()
