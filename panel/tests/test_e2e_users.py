"""Smoke tests E2E de usuários do painel."""

from __future__ import annotations

import pytest

from .e2e_pages import UsersListPage
from .e2e_support import PanelE2EBase, User

pytestmark = pytest.mark.e2e


class PanelUsersE2ESmokeTests(PanelE2EBase):
    """Valida fluxos de usuários no navegador real."""

    def test_users_list_filter_smoke(self) -> None:
        """A listagem de usuários deve filtrar resultados reais no navegador."""

        self._grant_permissions("view_user")
        users_page = UsersListPage(self)
        self.factory.create_user("ana-e2e")
        self.factory.create_user("bruno-e2e")

        self._login()
        users_page.open()
        users_page.filter("ana-e2e")

        users_page.wait_for_url_fragment("q=ana-e2e")
        users_page.wait_for_table_text("ana-e2e")
        self.assertIn("ana-e2e", self.browser.page_source)
        self.assertNotIn("bruno-e2e", self.browser.page_source)

    def test_users_list_shows_disabled_actions_without_management_permissions(self) -> None:
        """Operador só com leitura deve ver ações desabilitadas na listagem."""

        self._grant_permissions("view_user")
        users_page = UsersListPage(self)
        self.factory.create_user("ativo-e2e")
        inactive_user = self.factory.create_user("inativo-e2e")
        inactive_user.is_active = False
        inactive_user.save(update_fields=["is_active"])

        self._login()
        users_page.open()

        self.assertIsNotNone(users_page.find("users-create-disabled").get_attribute("disabled"))

        active_edit = users_page.row_action("ativo-e2e", "user-edit-disabled")
        active_toggle = users_page.row_action("ativo-e2e", "user-toggle-disabled")
        active_delete = users_page.row_action("ativo-e2e", "user-delete-disabled")
        inactive_toggle = users_page.row_action("inativo-e2e", "user-toggle-disabled")

        self.assertEqual(active_edit.text, "Editar")
        self.assertEqual(active_toggle.text, "Inativar")
        self.assertEqual(active_delete.text, "Excluir")
        self.assertEqual(inactive_toggle.text, "Ativar")
        self.assertIsNotNone(active_edit.get_attribute("disabled"))
        self.assertIsNotNone(active_toggle.get_attribute("disabled"))
        self.assertIsNotNone(active_delete.get_attribute("disabled"))
        self.assertIsNotNone(inactive_toggle.get_attribute("disabled"))

    def test_user_create_with_group_smoke(self) -> None:
        """O operador deve conseguir criar usuário e associar grupo pela dual-list."""

        self._grant_permissions("view_user", "add_user")
        users_page = UsersListPage(self)
        self.factory.create_group("Operação E2E")

        self._login()
        users_page.open()

        user_form = users_page.open_create_form()
        user_form.fill(
            username="novo-e2e",
            email="novo-e2e@example.com",
            first_name="Novo",
            last_name="E2E",
            password="SenhaSegura@123",
            auto_refresh_interval="30",
        )
        user_form.assign_group("Operação E2E")

        users_page = user_form.save()
        users_page.wait_for_table_text("novo-e2e")

        created_user = User.objects.get(username="novo-e2e")
        self.assertEqual(created_user.email, "novo-e2e@example.com")
        self.assertTrue(created_user.groups.filter(name="Operação E2E").exists())
        self.assertIn("novo-e2e", self._user_row("novo-e2e").text)

    def test_user_update_with_group_smoke(self) -> None:
        """O operador deve conseguir editar usuário e trocar seus grupos."""

        self._grant_permissions("view_user", "change_user")
        users_page = UsersListPage(self)
        original_group = self.factory.create_group("Grupo Atual E2E")
        self.factory.create_group("Grupo Novo E2E")
        user = self.factory.create_user(
            "editar-e2e",
            first_name="Editar",
            last_name="Original",
            groups=[original_group],
        )

        self._login()
        users_page.open()

        user_form = users_page.open_edit_form("editar-e2e")
        user_form.fill(
            email="editar-atualizado@example.com",
            first_name="Editado",
            last_name="Atualizado",
        )
        user_form.remove_group("Grupo Atual E2E")
        user_form.assign_group("Grupo Novo E2E")

        users_page = user_form.save()
        users_page.wait_for_table_text("editar-e2e")

        user.refresh_from_db()
        self.assertEqual(user.email, "editar-atualizado@example.com")
        self.assertEqual(user.first_name, "Editado")
        self.assertEqual(user.last_name, "Atualizado")
        self.assertFalse(user.groups.filter(name="Grupo Atual E2E").exists())
        self.assertTrue(user.groups.filter(name="Grupo Novo E2E").exists())
        self.assertIn("editar-atualizado@example.com", self._user_row("editar-e2e").text)
