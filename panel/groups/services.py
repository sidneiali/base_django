"""Serviços do domínio de grupos do painel."""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.db.models import QuerySet

from ..constants import PROTECTED_GROUP_NAMES


def editable_groups_queryset() -> QuerySet[Group]:
    """Retorna apenas os grupos que o painel pode gerenciar diretamente."""

    return Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)


def delete_panel_group(group: Group) -> None:
    """Remove um grupo editável do painel."""

    group.delete()
