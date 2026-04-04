"""Page objects leves para os smoke tests E2E do painel."""

from .admin_accounts import AdminAccountFormPage, AdminAccountsListPage
from .audit import AuditDetailPage, AuditListPage
from .groups import GroupFormPage, GroupsListPage
from .login_security import LoginSecurityPage
from .modules import ModuleFormPage, ModulesListPage
from .shell import TopbarPage
from .users import UserFormPage, UsersListPage

__all__ = [
    "AdminAccountFormPage",
    "AdminAccountsListPage",
    "AuditDetailPage",
    "AuditListPage",
    "GroupFormPage",
    "GroupsListPage",
    "LoginSecurityPage",
    "ModuleFormPage",
    "ModulesListPage",
    "TopbarPage",
    "UserFormPage",
    "UsersListPage",
]
