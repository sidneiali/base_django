"""Testes dos fluxos HTML de contas administrativas no painel."""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class PanelAdminAccountViewTests(TestCase):
    """Valida a superfície operacional de contas staff/superuser no painel."""

    def _login_as_superuser(self) -> Any:
        """Autentica um superusuário para operar a área administrativa."""

        user = User.objects.create_superuser(
            username="root-panel",
            email="root-panel@example.com",
            password="SenhaSegura@123",
        )
        self.client.force_login(user)
        return user

    def _login_as_staff_only(self) -> Any:
        """Autentica uma conta staff sem privilégios de superusuário."""

        user = User.objects.create_user(
            username="staff-panel",
            email="staff-panel@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )
        self.client.force_login(user)
        return user

    def test_admin_accounts_list_requires_superuser(self) -> None:
        """Contas apenas staff não podem acessar a área administrativa nova."""

        self._login_as_staff_only()

        response = self.client.get(reverse("panel_admin_accounts_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_admin_accounts_list_filters_results_and_excludes_common_users(self) -> None:
        """A listagem deve mostrar só contas administrativas e filtrar por texto."""

        self._login_as_superuser()
        User.objects.create_user(
            username="comum",
            email="comum@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_user(
            username="financeiro-admin",
            email="financeiro-admin@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )

        response = self.client.get(
            reverse("panel_admin_accounts_list"),
            {"q": "financeiro"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-page-title="Contas administrativas"',
            html=False,
        )
        self.assertContains(response, "financeiro-admin")
        self.assertNotContains(response, "comum")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_admin_accounts_list_disables_self_dangerous_actions(self) -> None:
        """A conta logada deve seguir visível, mas com ações perigosas desabilitadas."""

        current_user = self._login_as_superuser()
        other_admin = User.objects.create_user(
            username="staff-extra",
            email="staff-extra@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )

        response = self.client.get(reverse("panel_admin_accounts_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-teste="admin-accounts-create-link"',
            html=False,
        )
        self.assertContains(
            response,
            f'data-username="{current_user.username}"',
            html=False,
        )
        self.assertContains(
            response,
            'data-teste="admin-account-toggle-disabled"',
            html=False,
        )
        self.assertContains(
            response,
            'data-teste="admin-account-delete-disabled"',
            html=False,
        )
        self.assertContains(
            response,
            reverse("panel_admin_account_update", args=[other_admin.pk]),
        )
        self.assertContains(
            response,
            reverse("panel_admin_account_delete", args=[other_admin.pk]),
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_account_create_htmx_creates_staff_account_and_sends_invite(self) -> None:
        """Criar conta administrativa via HTMX deve persistir e disparar convite."""

        self._login_as_superuser()
        group = Group.objects.create(name="Infra")
        permission = Permission.objects.get(codename="view_group")

        response = self.client.post(
            reverse("panel_admin_account_create"),
            {
                "username": "novo-admin",
                "first_name": "Novo",
                "last_name": "Admin",
                "email": "novo-admin@example.com",
                "is_active": "on",
                "is_staff": "on",
                "groups": [str(group.pk)],
                "user_permissions": [str(permission.pk)],
                "auto_refresh_interval": "30",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_admin_accounts_list"))

        created_user = User.objects.get(username="novo-admin")
        self.assertTrue(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)
        self.assertTrue(created_user.groups.filter(pk=group.pk).exists())
        self.assertTrue(created_user.user_permissions.filter(pk=permission.pk).exists())
        self.assertFalse(created_user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Primeiro acesso", mail.outbox[0].subject)
        self.assertIn("novo-admin@example.com", mail.outbox[0].to)

    def test_admin_account_update_can_promote_other_account(self) -> None:
        """A edição deve permitir promover outra conta administrativa para superusuário."""

        self._login_as_superuser()
        permission = Permission.objects.get(codename="delete_group")
        admin_account = User.objects.create_user(
            username="staff-promovivel",
            email="staff-promovivel@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )

        response = self.client.post(
            reverse("panel_admin_account_update", args=[admin_account.pk]),
            {
                "username": "staff-promovivel",
                "first_name": "Staff",
                "last_name": "Promovido",
                "email": "staff-promovivel@example.com",
                "is_active": "on",
                "is_superuser": "on",
                "user_permissions": [str(permission.pk)],
                "auto_refresh_interval": "30",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        admin_account.refresh_from_db()
        self.assertTrue(admin_account.is_staff)
        self.assertTrue(admin_account.is_superuser)
        self.assertEqual(admin_account.last_name, "Promovido")
        self.assertTrue(admin_account.user_permissions.filter(pk=permission.pk).exists())

    def test_admin_account_deactivate_rejects_own_account(self) -> None:
        """A ação rápida não pode inativar a própria conta administrativa logada."""

        current_user = self._login_as_superuser()

        response = self.client.post(
            reverse("panel_admin_account_deactivate", args=[current_user.pk]),
        )

        self.assertEqual(response.status_code, 403)
        current_user.refresh_from_db()
        self.assertTrue(current_user.is_active)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_admin_account_delete_confirmation_disables_own_account_submit(self) -> None:
        """A confirmação de exclusão deve abrir, mas sem permitir apagar a própria conta."""

        current_user = self._login_as_superuser()

        response = self.client.get(
            reverse("panel_admin_account_delete", args=[current_user.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-teste="admin-account-delete-disabled-submit"',
            html=False,
        )
        self.assertContains(
            response,
            "Você não pode excluir sua própria conta administrativa pelo painel.",
        )

    def test_admin_account_delete_removes_other_staff_account(self) -> None:
        """Outra conta staff deve poder ser excluída pelo painel."""

        self._login_as_superuser()
        admin_account = User.objects.create_user(
            username="staff-removivel",
            email="staff-removivel@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )

        response = self.client.post(
            reverse("panel_admin_account_delete", args=[admin_account.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=admin_account.pk).exists())
