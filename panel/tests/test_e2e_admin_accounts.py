"""Smoke tests E2E da superfície de contas administrativas do painel."""

from __future__ import annotations

from typing import Any

import pytest

from .e2e_pages import AdminAccountsListPage, TopbarPage
from .e2e_support import PanelE2EBase, User

pytestmark = pytest.mark.e2e


class PanelAdminAccountsE2ESmokeTests(PanelE2EBase):
    """Valida a trilha de contas administrativas no navegador real."""

    def _elevate_current_user_to_superuser(self) -> Any:
        """Promove o usuário principal do cenário para habilitar a área."""

        user = self._test_user()
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        return user

    def test_superuser_can_open_admin_accounts_from_topbar(self) -> None:
        """O atalho admin-users deve abrir a área nova do painel."""

        self._elevate_current_user_to_superuser()
        topbar = TopbarPage(self)
        admin_accounts_page = AdminAccountsListPage(self)

        self._login()
        topbar.go_to_admin_accounts()

        admin_accounts_page.wait_for_table_text(self.username)
        self.assertIn(self.username, admin_accounts_page.table_text())
        self.assertIsNotNone(
            admin_accounts_page.row_action(
                self.username,
                "admin-account-delete-disabled",
            ).get_attribute("disabled")
        )

    def test_superuser_can_create_staff_account_from_panel(self) -> None:
        """A criação de conta administrativa deve funcionar no shell real."""

        self._elevate_current_user_to_superuser()
        topbar = TopbarPage(self)

        self._login()
        topbar.go_to_admin_accounts()

        admin_accounts_page = AdminAccountsListPage(self)
        admin_form = admin_accounts_page.open_create_form()
        admin_form.fill(
            username="novo-admin-e2e",
            email="novo-admin-e2e@example.com",
            first_name="Novo",
            last_name="Admin",
            auto_refresh_interval="30",
        )
        admin_form.set_staff(checked=True)

        admin_accounts_page = admin_form.save()
        admin_accounts_page.wait_for_table_text("novo-admin-e2e")

        created_user = User.objects.get(username="novo-admin-e2e")
        self.assertTrue(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)
