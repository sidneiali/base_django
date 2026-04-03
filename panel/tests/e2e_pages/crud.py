"""Blocos CRUD compartilhados pelos page objects E2E do painel."""

from __future__ import annotations

from django.urls import reverse
from selenium.webdriver.common.by import By

from .base import BasePageObject


class CrudListPage(BasePageObject):
    """Comportamentos comuns das listagens CRUD do painel."""

    url_name: str
    page_testid: str
    query_testid: str
    filter_submit_testid: str
    create_link_testid: str
    table_testid: str | None = None

    def open(self, query: str = "") -> None:
        self.test_case._open(reverse(self.url_name) + query)
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self.wait_present(self.page_testid)

    def filter(self, query: str) -> None:
        self.clear_and_type(self.query_testid, query)
        self.click(self.filter_submit_testid)

    def wait_for_table_text(self, text: str) -> None:
        locator = (
            self.locator_by_testid(self.table_testid)
            if self.table_testid is not None
            else (By.CSS_SELECTOR, "tbody")
        )
        self.wait_text(locator, text)

    def table_text(self) -> str:
        if self.table_testid is None:
            return self.browser.find_element(By.CSS_SELECTOR, "tbody").text
        return self.find(self.table_testid).text


class CrudFormPage(BasePageObject):
    """Comportamentos comuns dos formulários CRUD do painel."""

    page_testid: str
    save_submit_testid: str

    def wait_until_loaded(self) -> None:
        self.wait_present(self.page_testid)
