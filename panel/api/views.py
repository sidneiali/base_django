"""Fachada compatível para os endpoints JSON do app panel."""

from .groups import group_detail, groups_collection
from .users import user_detail, users_collection

__all__ = [
    "group_detail",
    "groups_collection",
    "user_detail",
    "users_collection",
]
