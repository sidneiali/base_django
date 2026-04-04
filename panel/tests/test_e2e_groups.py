"""Smoke tests E2E de grupos do painel."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from .e2e_pages import GroupsListPage
from .e2e_support import PanelE2EBase

pytestmark = pytest.mark.e2e


class PanelGroupsE2ESmokeTests(PanelE2EBase):
    """Valida fluxos de grupos no navegador real."""

    def test_groups_list_filter_smoke(self) -> None:
        """A listagem de grupos deve filtrar resultados reais no navegador."""

        self._grant_permissions("view_group")
        groups_page = GroupsListPage(self)
        self.factory.create_group("Grupo Financeiro E2E")
        self.factory.create_group("Grupo Comercial E2E")

        self._login()
        groups_page.open()
        groups_page.filter("Financeiro")

        groups_page.wait_for_url_fragment("q=Financeiro")
        groups_page.wait_for_table_text("Grupo Financeiro E2E")
        self.assertIn("Grupo Financeiro E2E", groups_page.table_text())
        self.assertNotIn("Grupo Comercial E2E", groups_page.table_text())

    def test_groups_list_read_only_operator_sees_disabled_actions_smoke(self) -> None:
        """O navegador real deve mostrar ações desabilitadas quando faltar gestão."""

        self._grant_permissions("view_group")
        groups_page = GroupsListPage(self)
        self.factory.create_group("Grupo Somente Leitura E2E")

        self._login()
        groups_page.open()

        self.assertTrue(groups_page.find("groups-create-disabled").is_displayed())
        row = groups_page.row("Grupo Somente Leitura E2E")
        self.assertTrue(
            row.find_element(*groups_page.locator_by_testid("group-edit-disabled")).is_displayed()
        )
        self.assertTrue(
            row.find_element(*groups_page.locator_by_testid("group-delete-disabled")).is_displayed()
        )

    def test_group_create_with_permission_smoke(self) -> None:
        """O operador deve conseguir criar grupo e associar permissão pela dual-list."""

        self._grant_permissions("view_group", "add_group", "view_user")
        groups_page = GroupsListPage(self)

        self._login()
        groups_page.open()

        group_form = groups_page.open_create_form()
        group_form.fill(name="Grupo Operação E2E")
        group_form.assign_permission(
            action_label="Pode visualizar",
            subject_label="Usuário",
        )

        groups_page = group_form.save()
        groups_page.wait_for_table_text("Grupo Operação E2E")

        created_group = Group.objects.get(name="Grupo Operação E2E")
        self.assertTrue(created_group.permissions.filter(codename="view_user").exists())
        self.assertIn("Grupo Operação E2E", self._group_row("Grupo Operação E2E").text)

    def test_group_update_permissions_smoke(self) -> None:
        """O operador deve conseguir editar um grupo e trocar suas permissões."""

        self._grant_permissions(
            "view_group",
            "change_group",
            "view_user",
            "change_user",
        )
        groups_page = GroupsListPage(self)
        group = self.factory.create_group(
            "Grupo Edição E2E",
            permission_codenames=["view_user"],
        )

        self._login()
        groups_page.open()

        group_form = groups_page.open_edit_form("Grupo Edição E2E")
        group_form.fill(name="Grupo Edição Atualizado")
        group_form.remove_permission(
            action_label="Pode visualizar",
            subject_label="Usuário",
        )
        group_form.assign_permission(
            action_label="Pode alterar",
            subject_label="Usuário",
        )

        groups_page = group_form.save()
        groups_page.wait_for_table_text("Grupo Edição Atualizado")

        group.refresh_from_db()
        self.assertEqual(group.name, "Grupo Edição Atualizado")
        self.assertTrue(group.permissions.filter(codename="change_user").exists())
        self.assertFalse(group.permissions.filter(codename="view_user").exists())
        self.assertIn("Grupo Edição Atualizado", self._group_row(group.name).text)
