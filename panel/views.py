"""Fachada compatível para as views do painel."""

from .audit.views import audit_logs_list
from .groups.views import group_create, group_update, groups_list
from .users.views import user_create, user_update, users_list

__all__ = [
    "audit_logs_list",
    "group_create",
    "group_update",
    "groups_list",
    "user_create",
    "user_update",
    "users_list",
]
