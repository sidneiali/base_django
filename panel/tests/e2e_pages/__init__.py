"""Page objects leves para os smoke tests E2E do painel."""

from .audit import AuditDetailPage, AuditListPage
from .groups import GroupFormPage, GroupsListPage
from .modules import ModuleFormPage, ModulesListPage
from .shell import TopbarPage
from .users import UserFormPage, UsersListPage

__all__ = [
    "AuditDetailPage",
    "AuditListPage",
    "GroupFormPage",
    "GroupsListPage",
    "ModuleFormPage",
    "ModulesListPage",
    "TopbarPage",
    "UserFormPage",
    "UsersListPage",
]
