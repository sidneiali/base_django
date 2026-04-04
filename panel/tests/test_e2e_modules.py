"""Smoke tests E2E de módulos do painel."""

from __future__ import annotations

import pytest
from core.models import Module

from .e2e_pages import ModulesListPage
from .e2e_support import PanelE2EBase

pytestmark = pytest.mark.e2e


class PanelModulesE2ESmokeTests(PanelE2EBase):
    """Valida fluxos de módulos no navegador real."""

    def test_modules_list_filter_smoke(self) -> None:
        """A listagem de módulos deve filtrar resultados reais no navegador."""

        self._grant_permissions("view_module")
        modules_page = ModulesListPage(self)
        self.factory.create_module(
            name="E2E Financeiro",
            slug="e2e-financeiro",
            description="Fluxo financeiro",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
        )
        self.factory.create_module(
            name="E2E CRM",
            slug="e2e-crm",
            description="Fluxo comercial",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=20,
        )

        self._login()
        modules_page.open()
        modules_page.filter("financeiro")

        modules_page.wait_for_url_fragment("q=financeiro")
        modules_page.wait_for_table_text("E2E Financeiro")
        self.assertIn("E2E Financeiro", modules_page.table_text())
        self.assertNotIn("E2E CRM", modules_page.table_text())

    def test_modules_list_read_only_operator_sees_disabled_actions_smoke(self) -> None:
        """O navegador real deve mostrar ações desabilitadas quando faltar gestão."""

        self._grant_permissions("view_module")
        modules_page = ModulesListPage(self)
        self.factory.create_module(
            name="E2E Somente Leitura Ativo",
            slug="e2e-somente-leitura-ativo",
            description="Leitura",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )
        self.factory.create_module(
            name="E2E Somente Leitura Inativo",
            slug="e2e-somente-leitura-inativo",
            description="Leitura",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=20,
            is_active=False,
        )

        self._login()
        modules_page.open()

        self.assertTrue(modules_page.find("modules-create-disabled").is_displayed())
        active_row = modules_page.row("E2E Somente Leitura Ativo")
        inactive_row = modules_page.row("E2E Somente Leitura Inativo")
        self.assertTrue(
            active_row.find_element(*modules_page.locator_by_testid("module-edit-disabled")).is_displayed()
        )
        self.assertTrue(
            active_row.find_element(*modules_page.locator_by_testid("module-toggle-disabled")).is_displayed()
        )
        self.assertTrue(
            active_row.find_element(*modules_page.locator_by_testid("module-delete-disabled")).is_displayed()
        )
        self.assertTrue(
            inactive_row.find_element(*modules_page.locator_by_testid("module-toggle-disabled")).is_displayed()
        )
        self.assertIn("Inativar", active_row.text)
        self.assertIn("Ativar", inactive_row.text)

    def test_module_create_and_toggle_status_smoke(self) -> None:
        """O operador deve conseguir criar, inativar e reativar um módulo no navegador."""

        self._grant_permissions("view_module", "add_module", "change_module")
        modules_page = ModulesListPage(self)

        self._login()
        modules_page.open()

        module_form = modules_page.open_create_form()
        module_form.fill(
            name="E2E Módulo",
            slug="e2e-modulo",
            description="Criado pelo smoke test",
            icon="ti ti-layout-grid",
            menu_group="Operação",
            url_name="module_entry",
            order="25",
        )

        modules_page = module_form.save()
        modules_page.wait_for_table_text("E2E Módulo")
        self.assertTrue(Module.objects.filter(slug="e2e-modulo").exists())

        row = modules_page.row("E2E Módulo")
        self.assertIn("Ativo", row.text)

        modules_page.deactivate("E2E Módulo")
        module = Module.objects.get(slug="e2e-modulo")
        self.assertFalse(module.is_active)

        modules_page.activate("E2E Módulo")
        module.refresh_from_db()
        self.assertTrue(module.is_active)

    def test_module_update_visibility_smoke(self) -> None:
        """O operador deve conseguir editar um módulo e alterar sua visibilidade."""

        self._grant_permissions("view_module", "change_module")
        modules_page = ModulesListPage(self)
        self.factory.create_module(
            name="E2E Módulo Editável",
            slug="e2e-modulo-editavel",
            description="Descrição inicial",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=15,
            show_in_dashboard=True,
            show_in_sidebar=True,
        )

        self._login()
        modules_page.open()

        module_form = modules_page.open_edit_form("E2E Módulo Editável")
        module_form.fill(description="Descrição atualizada pelo smoke test")
        module_form.set_show_in_dashboard(enabled=False)
        module_form.set_show_in_sidebar(enabled=False)

        modules_page = module_form.save()
        modules_page.wait_for_row_text("E2E Módulo Editável", "Oculto")

        updated_module = Module.objects.get(slug="e2e-modulo-editavel")
        self.assertEqual(
            updated_module.description,
            "Descrição atualizada pelo smoke test",
        )
        self.assertFalse(updated_module.show_in_dashboard)
        self.assertFalse(updated_module.show_in_sidebar)
        self.assertIn("Oculto", modules_page.row("E2E Módulo Editável").text)
