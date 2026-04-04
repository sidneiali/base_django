"""Builders de atalhos da topbar autenticada."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Final

from django.urls import reverse

from .types import TopbarShortcutGroups, TopbarShortcutItem

ShortcutDefinition = tuple[str, str, str, str, str | None]

SHORTCUT_DEFINITIONS: Final[tuple[ShortcutDefinition, ...]] = (
    ("Configurações", "users", "Usuários", "panel_users_list", "auth.view_user"),
    ("Configurações", "modules", "Módulos", "panel_modules_list", "core.view_module"),
    ("Segurança", "groups", "Grupos", "panel_groups_list", "auth.view_group"),
    (
        "Segurança",
        "login-security",
        "Segurança de login",
        "panel_login_security_list",
        "axes.view_accessattempt",
    ),
    ("Segurança", "audit", "Auditoria", "panel_audit_logs_list", "core.view_auditlog"),
    ("Integrações", "api-docs", "Documentação da API", "api_docs", None),
)


def user_has_shortcut_access(permission: str | None, user: Any) -> bool:
    """Resolve se o usuário atual pode visualizar um atalho do topo."""

    return bool(user.is_superuser or permission is None or user.has_perm(permission))


def build_topbar_shortcuts_for_user(user: Any) -> TopbarShortcutGroups:
    """Monta atalhos operacionais do topo sem depender do seed de módulos."""

    grouped: TopbarShortcutGroups = defaultdict(list)

    for group_name, key, label, url_name, permission in SHORTCUT_DEFINITIONS:
        if not user_has_shortcut_access(permission, user):
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
                label="Contas administrativas",
                url=reverse("panel_admin_accounts_list"),
            )
        )

    return dict(grouped)
