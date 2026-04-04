"""Page objects ligados à topbar e aos atalhos do shell autenticado."""

from __future__ import annotations

from django.urls import reverse
from selenium.webdriver.remote.webelement import WebElement

from .audit import AuditListPage
from .base import BasePageObject
from .login_security import LoginSecurityPage


class TopbarPage(BasePageObject):
    """Interações estáveis da topbar do shell autenticado."""

    def open_user_menu(self) -> None:
        self.test_case._open_user_menu()

    def open_shortcuts(self) -> None:
        self.test_case._open_topbar_shortcuts()

    def logout(self) -> None:
        self.open_user_menu()
        logout_button = self.wait_clickable("topbar-logout-submit")
        logout_button.click()
        self.pause()
        self.wait_visible("login-title")

    def go_to_my_password(self) -> None:
        self.open_user_menu()
        password_link = self.wait_clickable("topbar-my-password-link")
        password_link.click()
        self.pause()
        self.wait.until(
            lambda browser: browser.current_url.endswith(
                reverse("account_password_change")
            )
        )
        self.wait_present("account-password-page")

    def shortcut(self, shortcut_key: str) -> WebElement:
        return self.test_case._topbar_shortcut(shortcut_key)

    def go_to_audit(self) -> None:
        self.open_shortcuts()
        audit_link = self.shortcut("audit")
        audit_link.click()
        self.pause()
        AuditListPage(self.test_case).wait_until_loaded()

    def go_to_login_security(self) -> None:
        self.open_shortcuts()
        login_security_link = self.shortcut("login-security")
        login_security_link.click()
        self.pause()
        LoginSecurityPage(self.test_case).wait_until_loaded()
