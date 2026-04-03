"""Smoke tests E2E da trilha HTML de auditoria."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from core.models import AuditLog
from django.urls import reverse
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .e2e_pages import AuditDetailPage, AuditListPage
from .e2e_support import PanelE2EBase

pytestmark = pytest.mark.e2e


class PanelAuditE2ESmokeTests(PanelE2EBase):
    """Valida filtros, pivots e paginação da auditoria no navegador real."""

    def test_audit_list_filter_smoke(self) -> None:
        """A tela de auditoria deve filtrar eventos reais no navegador."""

        self._grant_permissions("view_auditlog")
        audit_list = AuditListPage(self)
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor_identifier=self.username,
            object_repr="Login do operador",
            request_id="req-filter-match",
        )
        old_log = self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor_identifier=self.username,
            object_repr="Atualização antiga",
            request_id="req-filter-old",
        )
        AuditLog.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )

        self._login()
        audit_list.open()
        audit_list.filter(
            actor=self.username,
            object_query="req-filter-match",
        )

        audit_list.wait_for_url_fragment("object_query=req-filter-match")
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Login do operador",
            )
        )
        self.assertIn("Login do operador", self.browser.page_source)
        self.assertNotIn("Atualização antiga", self.browser.page_source)

    def test_audit_detail_back_link_preserves_filters(self) -> None:
        """O drill-down deve abrir e o retorno deve manter os filtros atuais."""

        self._grant_permissions("view_auditlog")
        audit_list = AuditListPage(self)
        self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor_identifier=self.username,
            object_repr="Evento detalhado",
            request_id="req-detail-smoke",
        )

        self._login()
        query = "?actor=e2e-user&object_query=req-detail-smoke"
        audit_list.open(query)

        audit_list.open_first_detail()
        self.assertIn("Evento detalhado", self.browser.page_source)
        self.assertIn("req-detail-smoke", self.browser.page_source)

        back_link = self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid("audit-back-link"))
        )
        back_href = back_link.get_attribute("href") or ""
        self.assertIn(query, back_href)
        back_link.click()
        self._pause_for_demo()

        audit_list.wait_until_loaded()
        audit_list.wait_for_url_fragment("object_query=req-detail-smoke")
        self.assertIn("Evento detalhado", self.browser.page_source)

    def test_audit_quick_pivots_and_clear_filters_smoke(self) -> None:
        """A auditoria deve permitir pivot rápido por ator/request e limpar filtros."""

        self._grant_permissions("view_auditlog")
        audit_list = AuditListPage(self)
        other_user = self.audit_factory.create_actor("outro-auditor-e2e")
        self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor_identifier=self.username,
            object_repr="Evento pivô do operador",
            request_id="req-pivot-target",
        )
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor=other_user,
            actor_identifier=other_user.username,
            object_repr="Evento de outro operador",
            request_id="req-pivot-other",
        )

        self._login()
        audit_list.open()

        target_row = audit_list.row("req-pivot-target")
        actor_link = target_row.find_element(
            *self._locator_by_testid("audit-row-actor-link")
        )
        actor_link.click()
        self._pause_for_demo()

        audit_list.wait_for_url_fragment("actor=e2e-user")
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Evento pivô do operador",
            )
        )
        self.assertNotIn("Evento de outro operador", self.browser.page_source)

        audit_list.clear_filters()

        self.wait.until(
            lambda browser: browser.current_url.endswith(reverse("panel_audit_logs_list"))
        )
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Evento de outro operador",
            )
        )

        target_row = audit_list.row("req-pivot-target")
        request_link = target_row.find_element(
            *self._locator_by_testid("audit-row-request-link")
        )
        request_link.click()
        self._pause_for_demo()

        audit_list.wait_for_url_fragment("object_query=req-pivot-target")
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Evento pivô do operador",
            )
        )
        self.assertNotIn("Evento de outro operador", self.browser.page_source)

    def test_audit_pagination_preserves_filters_smoke(self) -> None:
        """A paginação da auditoria deve manter filtros aplicados no navegador."""

        self._grant_permissions("view_auditlog")
        audit_list = AuditListPage(self)
        base_time = timezone.now()
        for index in range(26):
            audit_log = self._create_audit_log(
                action=AuditLog.ACTION_UPDATE,
                actor_identifier=self.username,
                object_repr=f"Evento paginado {index}",
                request_id=f"req-page-{index}",
            )
            AuditLog.objects.filter(pk=audit_log.pk).update(
                created_at=base_time - timedelta(minutes=index)
            )

        other_user = self.audit_factory.create_actor("pagina-outro-e2e")
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor=other_user,
            actor_identifier=other_user.username,
            object_repr="Evento fora do filtro",
            request_id="req-page-other",
        )

        self._login()
        audit_list.open("?actor=e2e-user")

        audit_list.go_to_page(2)

        audit_list.wait_for_url_fragment("page=2")
        audit_list.wait_for_url_fragment("actor=e2e-user")
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Evento paginado 24",
            )
        )

        rows = self.browser.find_elements(*self._locator_by_testid("audit-row"))
        self.assertEqual(len(rows), 2)
        self.assertIn("Evento paginado 24", self.browser.page_source)
        self.assertIn("Evento paginado 25", self.browser.page_source)
        self.assertNotIn("Evento fora do filtro", self.browser.page_source)

    def test_audit_exports_download_filtered_csv_and_json_smoke(self) -> None:
        """CSV e JSON devem responder como anexos no navegador com os filtros ativos."""

        self._grant_permissions("view_auditlog")
        audit_list = AuditListPage(self)
        self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor_identifier=self.username,
            object_repr="Evento exportado no navegador",
            request_id="req-export-download",
        )
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor_identifier=self.username,
            object_repr="Evento fora do download",
            request_id="req-export-skip",
        )

        self._login()
        audit_list.open()
        audit_list.filter(
            actor=self.username,
            object_query="req-export-download",
        )
        audit_list.wait_for_url_fragment("object_query=req-export-download")

        csv_link = audit_list.export_link("csv")
        csv_href = csv_link.get_attribute("href") or ""
        self.assertEqual(csv_link.get_dom_attribute("hx-boost"), "false")
        self.assertIn("actor=e2e-user", csv_href)
        self.assertIn("object_query=req-export-download", csv_href)

        csv_response = audit_list.fetch_export("csv")
        self.assertEqual(csv_response["status"], 200)
        self.assertIn("text/csv", str(csv_response["contentType"]))
        self.assertIn("attachment; filename=", str(csv_response["contentDisposition"]))
        csv_content = str(csv_response["body"])
        self.assertIn("Evento exportado no navegador", csv_content)
        self.assertIn("req-export-download", csv_content)
        self.assertNotIn("Evento fora do download", csv_content)

        json_link = audit_list.export_link("json")
        json_href = json_link.get_attribute("href") or ""
        self.assertEqual(json_link.get_dom_attribute("hx-boost"), "false")
        self.assertIn("actor=e2e-user", json_href)
        self.assertIn("object_query=req-export-download", json_href)

        json_response = audit_list.fetch_export("json")
        self.assertEqual(json_response["status"], 200)
        self.assertIn("application/json", str(json_response["contentType"]))
        self.assertIn(
            "attachment; filename=",
            str(json_response["contentDisposition"]),
        )
        payload = json.loads(str(json_response["body"]))
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["filters"]["actor"], self.username)
        self.assertEqual(payload["filters"]["object_query"], "req-export-download")
        self.assertEqual(payload["results"][0]["object_repr"], "Evento exportado no navegador")
        self.assertEqual(payload["results"][0]["request_id"], "req-export-download")

    def test_audit_detail_related_shortcuts_smoke(self) -> None:
        """O detalhe deve permitir pivot rápido por ator e pela mesma requisição."""

        self._grant_permissions("view_auditlog")
        audit_detail = AuditDetailPage(self)
        other_user = self.audit_factory.create_actor("detalhe-outro-e2e")
        scenario = self.audit_factory.create_related_scenario(
            actor=self._test_user(),
            actor_identifier=self.username,
            other_actor=other_user,
            other_actor_identifier=other_user.username,
            target_object_repr="Evento alvo do detalhe",
            request_id="req-detail-related",
            actor_related_object_repr="Evento do mesmo ator",
            actor_related_request_id="req-detail-actor-only",
            request_related_object_repr="Evento da mesma requisição",
            request_related_action=AuditLog.ACTION_UPDATE,
            unrelated_object_repr="Evento fora do atalho",
            unrelated_action=AuditLog.ACTION_LOGIN,
        )

        self._login()
        audit_detail.open(scenario.target_log)
        audit_detail.open_actor_filtered_list()

        AuditListPage(self).wait_for_url_fragment("actor=e2e-user")
        self.assertIn("Evento do mesmo ator", self.browser.page_source)
        self.assertNotIn("Evento fora do atalho", self.browser.page_source)

        audit_detail.open(scenario.target_log)
        audit_detail.open_request_filtered_list()

        AuditListPage(self).wait_for_url_fragment("object_query=req-detail-related")
        self.assertIn("Evento da mesma requisição", self.browser.page_source)
        self.assertNotIn("Evento fora do atalho", self.browser.page_source)

    def test_audit_detail_related_preview_opens_other_event_smoke(self) -> None:
        """O detalhe deve abrir eventos relacionados sem perder o contexto derivado."""

        self._grant_permissions("view_auditlog")
        audit_detail = AuditDetailPage(self)
        other_user = self.audit_factory.create_actor("preview-outro-e2e")
        scenario = self.audit_factory.create_related_scenario(
            actor=self._test_user(),
            actor_identifier=self.username,
            other_actor=other_user,
            other_actor_identifier=other_user.username,
            target_object_repr="Evento principal da prévia",
            request_id="req-preview-related",
            actor_related_object_repr="Prévia do mesmo ator",
            actor_related_request_id="req-preview-actor-only",
            request_related_object_repr="Prévia da mesma requisição",
        )

        self._login()
        audit_detail.open(scenario.target_log)

        actor_section = audit_detail.related_section("actor")
        self.assertIn("Prévia do mesmo ator", actor_section.text)
        actor_detail_link = audit_detail.related_detail_link("actor")
        actor_href = actor_detail_link.get_attribute("href") or ""
        self.assertIn("?actor=e2e-user", actor_href)
        audit_detail.open_related_detail("actor")
        audit_detail.wait_for_url_fragment("actor=e2e-user")
        self.assertIn("Prévia do mesmo ator", self.browser.page_source)

        audit_detail.open(scenario.target_log)

        request_section = audit_detail.related_section("request")
        self.assertIn("Prévia da mesma requisição", request_section.text)
        request_detail_link = audit_detail.related_detail_link("request")
        request_href = request_detail_link.get_attribute("href") or ""
        self.assertIn("?object_query=req-preview-related", request_href)
        audit_detail.open_related_detail("request")
        audit_detail.wait_for_url_fragment("object_query=req-preview-related")
        self.assertIn("Prévia da mesma requisição", self.browser.page_source)
