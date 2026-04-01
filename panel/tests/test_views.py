"""Testes dos fluxos HTML do painel."""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PanelViewTests(TestCase):
    """Valida permissões e fluxos HTMX do painel interno."""

    def _login_with_permissions(self, *codenames: str) -> AbstractUser:
        """Autentica um operador com o conjunto informado de permissões."""

        user = User.objects.create_user(
            username="operador",
            email="operador@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(Permission.objects.filter(codename__in=codenames))
        user.user_permissions.add(*permissions)
        self.client.force_login(user)
        return user

    def test_users_list_requires_view_permission(self) -> None:
        """Usuário autenticado sem permissão não pode listar usuários."""

        self._login_with_permissions()

        response = self.client.get(reverse("panel_users_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_users_list_filters_results_and_renders_partial_for_htmx(self) -> None:
        """A listagem deve filtrar por busca e devolver partial no HTMX."""

        self._login_with_permissions("view_user")
        User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_user(
            username="bruno",
            email="bruno@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.get(
            reverse("panel_users_list"),
            {"q": "ana"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Usuários"', html=False)
        self.assertContains(response, "ana")
        self.assertNotContains(response, "bruno")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_user_create_htmx_creates_user_and_redirects(self) -> None:
        """Criar usuário via HTMX deve persistir e responder com HX-Location."""

        self._login_with_permissions("add_user")
        group = Group.objects.create(name="Operação")

        response = self.client.post(
            reverse("panel_user_create"),
            {
                "username": "novo-painel",
                "first_name": "Novo",
                "last_name": "Usuário",
                "email": "novo@example.com",
                "password": "SenhaSegura@123",
                "is_active": "on",
                "groups": [str(group.pk)],
                "auto_refresh_interval": "30",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_users_list"))

        created_user = User.objects.get(username="novo-painel")
        self.assertTrue(created_user.groups.filter(pk=group.pk).exists())

    def test_groups_list_excludes_protected_groups(self) -> None:
        """A listagem de grupos deve ocultar grupos protegidos do painel."""

        self._login_with_permissions("view_group")
        Group.objects.create(name="Root")
        Group.objects.create(name="Analistas")

        response = self.client.get(reverse("panel_groups_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analistas")
        self.assertNotContains(response, "Root")

    def test_group_create_htmx_creates_group_and_permissions(self) -> None:
        """Criar grupo via HTMX deve persistir permissões e redirecionar."""

        self._login_with_permissions("add_group")
        permission = Permission.objects.get(codename="view_user")

        response = self.client.post(
            reverse("panel_group_create"),
            {
                "name": "Suporte",
                "permissions": [str(permission.pk)],
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_groups_list"))

        group = Group.objects.get(name="Suporte")
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
