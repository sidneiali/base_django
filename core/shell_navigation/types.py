"""Tipos compartilhados da navegação autenticada do shell."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModuleNavigationItem:
    """Representa um módulo renderizável no dashboard e no sidebar."""

    name: str
    slug: str
    description: str
    icon: str
    url: str
    has_access: bool
    show_in_sidebar: bool
    show_in_dashboard: bool


ModuleNavigationGroups = dict[str, list[ModuleNavigationItem]]


@dataclass(frozen=True, slots=True)
class TopbarShortcutItem:
    """Representa um atalho exibido no menu superior autenticado."""

    key: str
    label: str
    url: str


TopbarShortcutGroups = dict[str, list[TopbarShortcutItem]]

