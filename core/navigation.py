"""Fachada pública da navegação autenticada do shell principal."""

from __future__ import annotations

from typing import cast

from django.http import HttpRequest

from .shell_navigation.modules import build_modules_for_user, filter_modules_for_surface
from .shell_navigation.shortcuts import build_topbar_shortcuts_for_user
from .shell_navigation.types import (
    ModuleNavigationGroups,
    ModuleNavigationItem,
    TopbarShortcutGroups,
    TopbarShortcutItem,
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


def _get_request_user(request: HttpRequest):
    """Retorna o usuário do request com fallback seguro."""

    return getattr(request, "user", None)


def get_request_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna todos os módulos ativos da navegação com cache por request."""

    user = _get_request_user(request)
    if not getattr(user, "is_authenticated", False):
        return {}

    cached_modules = cast(
        ModuleNavigationGroups | None,
        getattr(request, "_cached_navigation_modules", None),
    )
    if cached_modules is not None:
        return cached_modules

    modules = build_modules_for_user(user)
    setattr(request, "_cached_navigation_modules", modules)
    return modules


def get_request_sidebar_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna os módulos visíveis no sidebar com cache por request."""

    return filter_modules_for_surface(get_request_modules(request), surface="sidebar")


def get_request_dashboard_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna os módulos visíveis no dashboard com cache por request."""

    return filter_modules_for_surface(
        get_request_modules(request),
        surface="dashboard",
    )


def get_request_topbar_shortcuts(request: HttpRequest) -> TopbarShortcutGroups:
    """Retorna atalhos do topo com cache por request."""

    user = _get_request_user(request)
    if not getattr(user, "is_authenticated", False):
        return {}

    cached_shortcuts = cast(
        TopbarShortcutGroups | None,
        getattr(request, "_cached_topbar_shortcuts", None),
    )
    if cached_shortcuts is not None:
        return cached_shortcuts

    shortcuts = build_topbar_shortcuts_for_user(user)
    setattr(request, "_cached_topbar_shortcuts", shortcuts)
    return shortcuts
