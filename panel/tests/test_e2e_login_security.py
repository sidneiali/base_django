"""Smoke tests E2E da tela de segurança de login do painel."""

from __future__ import annotations

import pytest
from axes.models import AccessAttempt  # type: ignore[import-untyped]

from .e2e_pages import LoginSecurityPage, TopbarPage
from .e2e_support import PanelE2EBase

pytestmark = pytest.mark.e2e


class PanelLoginSecurityE2ESmokeTests(PanelE2EBase):
    """Valida a operação do django-axes no navegador real."""

    def test_login_security_shortcut_filter_and_reset_smoke(self) -> None:
        """O operador deve acessar a área, filtrar e desbloquear uma tentativa."""

        self._grant_permissions("view_accessattempt", "delete_accessattempt")
        topbar = TopbarPage(self)
        login_security_page = LoginSecurityPage(self)
        attempt = AccessAttempt.objects.create(
            username="travado-e2e@example.com",
            ip_address="10.1.0.10",
            user_agent="Edge E2E",
            http_accept="text/html",
            path_info="/login/",
            get_data="next=/",
            post_data="username=travado-e2e@example.com",
            failures_since_start=5,
        )
        AccessAttempt.objects.create(
            username="aberto-e2e@example.com",
            ip_address="10.1.0.11",
            user_agent="Edge E2E",
            http_accept="text/html",
            path_info="/login/",
            get_data="next=/",
            post_data="username=aberto-e2e@example.com",
            failures_since_start=1,
        )

        self._login()
        topbar.go_to_login_security()
        login_security_page.filter("travado-e2e@example.com", locked="yes")

        login_security_page.wait_for_url_fragment("q=travado-e2e%40example.com")
        login_security_page.wait_for_attempt_table_text("travado-e2e@example.com")
        self.assertIn("travado-e2e@example.com", login_security_page.attempts_table_text())
        self.assertNotIn("aberto-e2e@example.com", login_security_page.attempts_table_text())

        login_security_page.reset_attempt(attempt.pk)
        self.assertFalse(AccessAttempt.objects.filter(pk=attempt.pk).exists())
