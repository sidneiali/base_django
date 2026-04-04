"""Serviços compartilhados do app core."""

from ..navigation import (
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
from .rate_limit_service import (
    RateLimitConfig,
    build_rate_limit_identifier,
    consume_rate_limit_slot,
    get_rate_limit_config,
)

__all__ = [
    "ModuleNavigationGroups",
    "ModuleNavigationItem",
    "RateLimitConfig",
    "TopbarShortcutGroups",
    "TopbarShortcutItem",
    "build_modules_for_user",
    "build_rate_limit_identifier",
    "build_topbar_shortcuts_for_user",
    "consume_rate_limit_slot",
    "get_rate_limit_config",
    "get_request_dashboard_modules",
    "get_request_modules",
    "get_request_sidebar_modules",
    "get_request_topbar_shortcuts",
]
