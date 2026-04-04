"""Smoke tests E2E de autenticação e topbar do shell."""

from __future__ import annotations

import pytest
from django.urls import reverse

from .e2e_pages import AuditListPage, TopbarPage
from .e2e_support import PanelE2EBase

pytestmark = pytest.mark.e2e


class PanelAuthE2ESmokeTests(PanelE2EBase):
    """Valida login, logout e navegação básica da topbar."""

    def test_login_and_logout_smoke(self) -> None:
        """O usuário deve conseguir entrar no dashboard e sair pela topbar."""

        self._login()
        self.assertTrue(self.browser.current_url.endswith(reverse("dashboard")))

        topbar = TopbarPage(self)
        topbar.logout()

        self.assertIn(reverse("login"), self.browser.current_url)
        self.assertIn("Entrar na sua conta", self.browser.page_source)

    def test_topbar_my_password_link_opens_account_page(self) -> None:
        """O link "Minha senha" deve navegar para a conta autenticada via HTMX."""

        self._login()
        topbar = TopbarPage(self)
        topbar.go_to_my_password()

        self.assertTrue(
            self.browser.current_url.endswith(reverse("account_password_change"))
        )
        self.assertIn("Alterar senha", self.browser.page_source)

    def test_topbar_audit_shortcut_opens_audit_list(self) -> None:
        """O atalho operacional de auditoria deve abrir a trilha HTML pela topbar."""

        self._grant_permissions("view_auditlog")

        self._login()
        topbar = TopbarPage(self)
        topbar.open_shortcuts()
        audit_link = topbar.shortcut("audit")
        self.assertTrue(
            (audit_link.get_attribute("href") or "").endswith(
                reverse("panel_audit_logs_list")
            )
        )
        audit_link.click()
        self._pause_for_demo()
        AuditListPage(self).wait_until_loaded()

        self.assertTrue(
            self.browser.current_url.endswith(reverse("panel_audit_logs_list"))
        )
        self.assertIn("Auditoria", self.browser.page_source)
