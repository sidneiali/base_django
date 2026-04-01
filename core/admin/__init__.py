"""Pacote de configuracao do Django admin para o app core."""

from .audit import AuditLogAdmin
from .modules import ModuleAdmin
from .users import AdminUserChangeForm, AdminUserCreationForm, UserAdmin

__all__ = [
    "AdminUserChangeForm",
    "AdminUserCreationForm",
    "AuditLogAdmin",
    "ModuleAdmin",
    "UserAdmin",
]
