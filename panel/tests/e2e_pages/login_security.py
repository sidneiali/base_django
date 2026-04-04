"""Page object E2E da tela de segurança de login no painel."""

from __future__ import annotations

from django.urls import reverse
from selenium.webdriver.common.by import By

from .base import BasePageObject


class LoginSecurityPage(BasePageObject):
    """Fluxos recorrentes da página operacional do django-axes."""

    page_testid = "login-security-page"

    def open(self, query: str = "") -> None:
        self.test_case._open(reverse("panel_login_security_list") + query)
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self.wait_present(self.page_testid)

    def filter(self, query: str, *, locked: str = "") -> None:
        self.clear_and_type("login-security-query", query)
        if locked:
            select = self.find("login-security-locked-filter")
            for option in select.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == locked:
                    option.click()
                    break
        self.click("login-security-filter-submit")

    def wait_for_attempt_table_text(self, text: str) -> None:
        self.wait_text(self.locator_by_testid("login-security-attempts-table"), text)

    def attempts_table_text(self) -> str:
        return self.find("login-security-attempts-table").text

    def attempt_row(self, attempt_id: int):
        selector = (
            '[data-teste="login-security-attempt-row"]'
            f'[data-attempt-id="{attempt_id}"]'
        )
        return self.browser.find_element(By.CSS_SELECTOR, selector)

    def reset_attempt(self, attempt_id: int) -> None:
        row = self.attempt_row(attempt_id)
        button = row.find_element(
            *self.locator_by_testid("login-security-attempt-reset-submit")
        )
        button.click()
        self.pause()
        self.wait.until(
            lambda browser: not browser.find_elements(
                By.CSS_SELECTOR,
                (
                    '[data-teste="login-security-attempt-row"]'
                    f'[data-attempt-id="{attempt_id}"]'
                ),
            )
        )
