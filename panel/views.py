"""Fachada compatível para as views do painel."""

from .audit.views import audit_log_detail, audit_logs_list
from .groups.views import group_create, group_update, groups_list
from .modules.views import module_create, module_update, modules_list
from .users.views import user_create, user_update, users_list

__all__ = [
    "audit_log_detail",
    "audit_logs_list",
    "group_create",
    "group_update",
    "groups_list",
    "module_create",
    "module_update",
    "modules_list",
    "user_create",
    "user_update",
    "users_list",
]
