"""Fachada compatível para helpers de navegação do shell autenticado."""

from .navigation import (
    ModuleNavigationGroups,
    ModuleNavigationItem,
    build_modules_for_user,
    get_request_modules,
)

__all__ = [
    "ModuleNavigationGroups",
    "ModuleNavigationItem",
    "build_modules_for_user",
    "get_request_modules",
]
