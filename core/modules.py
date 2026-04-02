"""Mapa declarativo dos modulos canonicos adicionais do projeto."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ModuleDefinition(TypedDict):
    """Contrato declarativo usado para montar o catalogo canonico."""

    name: str
    description: str
    icon: str
    url_name: str
    app_label: str
    permission_codename: str
    menu_group: str
    order: int
    is_active: NotRequired[bool]
    show_in_sidebar: NotRequired[bool]
    show_in_dashboard: NotRequired[bool]


MODULES: dict[str, ModuleDefinition] = {}
