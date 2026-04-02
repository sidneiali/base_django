"""Fachada compatível para helpers de navegação do shell autenticado."""

from .navigation import (
    ModuleNavigationGroups,
    ModuleNavigationItem,
    TopbarShortcutGroups,
    TopbarShortcutItem,
    build_modules_for_user,
    build_topbar_shortcuts_for_user,
    get_request_dashboard_modules,
    get_request_modules,
    get_request_sidebar_modules,
    get_request_topbar_shortcuts,
)

__all__ = [
    "ModuleNavigationGroups",
    "ModuleNavigationItem",
    "TopbarShortcutGroups",
    "TopbarShortcutItem",
    "build_modules_for_user",
    "build_topbar_shortcuts_for_user",
    "get_request_dashboard_modules",
    "get_request_modules",
    "get_request_sidebar_modules",
    "get_request_topbar_shortcuts",
]
