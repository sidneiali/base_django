"""Fachada compatível para as views do painel."""

from .groups.views import group_create, group_update, groups_list
from .users.views import user_create, user_update, users_list

__all__ = [
    "group_create",
    "group_update",
    "groups_list",
    "user_create",
    "user_update",
    "users_list",
]
