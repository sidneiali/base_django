"""Page objects da trilha HTML de auditoria no navegador real."""

from __future__ import annotations

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePageObject


class AuditListPage(BasePageObject):
    """Fluxos recorrentes da lista HTML de auditoria."""

    def open(self, query: str = "") -> None:
        self.test_case._open(reverse("panel_audit_logs_list") + query)
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self.wait_present("audit-list-page")

    def filter(
        self,
        *,
        actor: str | None = None,
        object_query: str | None = None,
    ) -> None:
        if actor is not None:
            actor_input = self.wait_visible("audit-filter-actor")
            actor_input.clear()
            actor_input.send_keys(actor)

        if object_query is not None:
            object_input = self.wait_visible("audit-filter-object-query")
            object_input.clear()
            object_input.send_keys(object_query)

        submit_button = self.find("audit-filter-submit")
        submit_button.click()
        self.pause()

    def clear_filters(self) -> None:
        clear_link = self.wait_clickable("audit-filter-clear")
        clear_link.click()
        self.pause()

    def row(self, request_id: str) -> WebElement:
        return self.test_case._audit_row(request_id)

    def open_first_detail(self) -> None:
        detail_link = self.wait_clickable("audit-detail-link")
        detail_link.click()
        self.pause()
        AuditDetailPage(self.test_case).wait_until_loaded()

    def go_to_page(self, page_number: int) -> None:
        selector = (
            '[data-teste="audit-page-number"]'
            f'[data-page-number="{page_number}"]'
        )
        page_link = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        page_link.click()
        self.pause()

    def export_link(self, export_format: str) -> WebElement:
        return self.find(f"audit-export-{export_format}")

    def export_href(self, export_format: str) -> str:
        return self.export_link(export_format).get_attribute("href") or ""

    def fetch_export(self, export_format: str) -> dict[str, object]:
        return self.test_case._fetch_response_in_browser(
            self.export_href(export_format)
        )


class AuditDetailPage(BasePageObject):
    """Fluxos recorrentes do drill-down HTML de auditoria."""

    def open(self, audit_log_or_pk: object, query: str = "") -> None:
        audit_log_pk = getattr(audit_log_or_pk, "pk", audit_log_or_pk)
        self.test_case._open(
            reverse("panel_audit_log_detail", args=[audit_log_pk]) + query
        )
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self.wait_present("audit-detail-page")

    def open_actor_filtered_list(self) -> None:
        actor_link = self.wait_clickable("audit-detail-actor-link")
        actor_link.click()
        self.pause()
        AuditListPage(self.test_case).wait_until_loaded()

    def open_request_filtered_list(self) -> None:
        request_link = self.wait_clickable("audit-detail-request-link")
        request_link.click()
        self.pause()
        AuditListPage(self.test_case).wait_until_loaded()

    def related_section(self, scope: str) -> WebElement:
        selector = (
            '[data-teste="audit-related-section"]'
            f'[data-related-scope="{scope}"]'
        )
        return self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def related_detail_link(self, scope: str) -> WebElement:
        return self.related_section(scope).find_element(
            *self.locator_by_testid("audit-related-detail-link")
        )

    def open_related_detail(self, scope: str) -> None:
        detail_link = self.related_detail_link(scope)
        detail_link.click()
        self.pause()
        self.wait_until_loaded()
