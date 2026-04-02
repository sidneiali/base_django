"""Montagem da navegação autenticada do shell principal."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast

from django.http import HttpRequest
from django.urls import reverse

from .models import Module


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


def _module_has_access(module: Module, user: Any) -> bool:
    """Resolve se o usuário atual pode acessar o módulo informado."""

    return bool(
        user.is_superuser
        or not module.full_permission
        or user.has_perm(module.full_permission)
    )


def _user_has_shortcut_access(permission: str | None, user: Any) -> bool:
    """Resolve se o usuário atual pode visualizar um atalho do topo."""

    return bool(user.is_superuser or permission is None or user.has_perm(permission))


def build_modules_for_user(user: Any) -> ModuleNavigationGroups:
    """Agrupa os módulos ativos e calcula acesso para um usuário."""

    modules = Module.objects.filter(is_active=True).order_by("menu_group", "order", "name")
    grouped: ModuleNavigationGroups = defaultdict(list)

    for module in modules:
        grouped[module.menu_group].append(
            ModuleNavigationItem(
                name=module.name,
                slug=module.slug,
                description=module.description,
                icon=module.icon or "ti ti-layout-grid",
                url=module.get_absolute_url(),
                has_access=_module_has_access(module, user),
                show_in_sidebar=module.show_in_sidebar,
                show_in_dashboard=module.show_in_dashboard,
            )
        )

    return dict(grouped)


def _filter_modules_for_surface(
    modules: ModuleNavigationGroups,
    *,
    surface: str,
) -> ModuleNavigationGroups:
    """Filtra a navegação agrupada para uma superfície específica do shell."""

    attribute = "show_in_sidebar" if surface == "sidebar" else "show_in_dashboard"
    filtered: ModuleNavigationGroups = {}

    for group_name, group_modules in modules.items():
        visible_modules = [
            module
            for module in group_modules
            if getattr(module, attribute)
        ]
        if visible_modules:
            filtered[group_name] = visible_modules

    return filtered


def build_topbar_shortcuts_for_user(user: Any) -> TopbarShortcutGroups:
    """Monta atalhos operacionais do topo sem depender do seed de módulos."""

    shortcut_definitions = (
        ("Configurações", "users", "Usuários", "panel_users_list", "auth.view_user"),
        ("Configurações", "modules", "Módulos", "panel_modules_list", "core.view_module"),
        ("Segurança", "groups", "Grupos", "panel_groups_list", "auth.view_group"),
        ("Segurança", "audit", "Auditoria", "panel_audit_logs_list", "core.view_auditlog"),
        ("Integrações", "api-docs", "Documentação da API", "api_docs", None),
    )

    grouped: TopbarShortcutGroups = defaultdict(list)

    for group_name, key, label, url_name, permission in shortcut_definitions:
        if not _user_has_shortcut_access(permission, user):
            continue
        grouped[group_name].append(
            TopbarShortcutItem(
                key=key,
                label=label,
                url=reverse(url_name),
            )
        )

    if user.is_superuser:
        grouped["Administração"].append(
            TopbarShortcutItem(
                key="admin-users",
                label="Super Usuário",
                url=reverse("admin:auth_user_changelist"),
            )
        )

    return dict(grouped)


def get_request_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna todos os módulos ativos da navegação com cache por request."""

    if not request.user.is_authenticated:
        return {}

    cached_modules = cast(
        ModuleNavigationGroups | None,
        getattr(request, "_cached_navigation_modules", None),
    )
    if cached_modules is not None:
        return cached_modules

    modules = build_modules_for_user(request.user)
    setattr(request, "_cached_navigation_modules", modules)
    return modules


def get_request_sidebar_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna os módulos visíveis no sidebar com cache por request."""

    return _filter_modules_for_surface(get_request_modules(request), surface="sidebar")


def get_request_dashboard_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna os módulos visíveis no dashboard com cache por request."""

    return _filter_modules_for_surface(
        get_request_modules(request),
        surface="dashboard",
    )


def get_request_topbar_shortcuts(request: HttpRequest) -> TopbarShortcutGroups:
    """Retorna atalhos do topo com cache por request."""

    if not request.user.is_authenticated:
        return {}

    cached_shortcuts = cast(
        TopbarShortcutGroups | None,
        getattr(request, "_cached_topbar_shortcuts", None),
    )
    if cached_shortcuts is not None:
        return cached_shortcuts

    shortcuts = build_topbar_shortcuts_for_user(request.user)
    setattr(request, "_cached_topbar_shortcuts", shortcuts)
    return shortcuts
