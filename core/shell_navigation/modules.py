"""Builders de módulos da navegação autenticada do shell."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from core.models import Module

from .types import ModuleNavigationGroups, ModuleNavigationItem


def module_has_access(module: Module, user: Any) -> bool:
    """Resolve se o usuário atual pode acessar o módulo informado."""

    return bool(
        user.is_superuser
        or not module.full_permission
        or user.has_perm(module.full_permission)
    )


def build_modules_for_user(user: Any) -> ModuleNavigationGroups:
    """Agrupa os módulos ativos e calcula acesso para um usuário."""

    modules = Module.objects.filter(is_active=True).order_by(
        "menu_group",
        "order",
        "name",
    )
    grouped: ModuleNavigationGroups = defaultdict(list)

    for module in modules:
        grouped[module.menu_group].append(
            ModuleNavigationItem(
                name=module.name,
                slug=module.slug,
                description=module.description,
                icon=module.icon or "ti ti-layout-grid",
                url=module.get_absolute_url(),
                has_access=module_has_access(module, user),
                show_in_sidebar=module.show_in_sidebar,
                show_in_dashboard=module.show_in_dashboard,
            )
        )

    return dict(grouped)


def filter_modules_for_surface(
    modules: ModuleNavigationGroups,
    *,
    surface: Literal["sidebar", "dashboard"],
) -> ModuleNavigationGroups:
    """Filtra a navegação agrupada para uma superfície específica do shell."""

    attribute = "show_in_sidebar" if surface == "sidebar" else "show_in_dashboard"
    filtered: ModuleNavigationGroups = {}

    for group_name, group_modules in modules.items():
        visible_modules = [
            module for module in group_modules if getattr(module, attribute)
        ]
        if visible_modules:
            filtered[group_name] = visible_modules

    return filtered

