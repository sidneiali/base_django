"""Testes dos endpoints JSON de usuários do painel."""

from __future__ import annotations

import json

from core.models import ApiToken
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .api_test_support import PanelApiTokenMixin

User = get_user_model()


class PanelUsersApiTests(PanelApiTokenMixin, TestCase):
    """Valida a superfície JSON de usuários do painel."""

    def test_users_collection_requires_bearer_token(self) -> None:
        """A listagem JSON deve rejeitar chamadas sem Authorization Bearer."""

        response = self.client.get(reverse("api_panel_users_collection"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "missing_authorization")

    def test_users_collection_requires_read_permission(self) -> None:
        """O token autenticado ainda precisa ter permissão de leitura."""

        _user, raw_token = self._issue_token()

        response = self.client.get(
            reverse("api_panel_users_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_users_collection_lists_non_superusers_and_updates_last_used(self) -> None:
        """A listagem deve autenticar via Bearer e ignorar superusuários."""

        api_user, raw_token = self._issue_token(can_read=True)
        User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.get(
            reverse("api_panel_users_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        usernames = {item["username"] for item in payload["data"]}
        self.assertIn("api-client", usernames)
        self.assertIn("maria", usernames)
        self.assertNotIn("root", usernames)
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 2)
        self.assertEqual(payload["meta"]["ordering"], "username")

        token = ApiToken.objects.get(user=api_user)
        self.assertIsNotNone(token.last_used_at)

    def test_versioned_users_collection_alias_works(self) -> None:
        """A rota versionada deve responder com o mesmo recurso de usuários."""

        _api_user, raw_token = self._issue_token(can_read=True)

        response = self.client.get(
            reverse("api_v1_panel_users_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())

    def test_users_collection_supports_filters_ordering_and_pagination(self) -> None:
        """A coleção deve aceitar filtros explícitos, ordenação e paginação."""

        _api_user, raw_token = self._issue_token(can_read=True)
        group = Group.objects.create(name="Clientes")
        ana = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="SenhaSegura@123",
            is_active=True,
        )
        ana.groups.add(group)
        User.objects.create_user(
            username="bruno",
            email="bruno@example.com",
            password="SenhaSegura@123",
            is_active=False,
        )

        response = self.client.get(
            reverse("api_panel_users_collection"),
            {
                "is_active": "true",
                "group_id": group.pk,
                "ordering": "-username",
                "page_size": 1,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["ordering"], "-username")
        self.assertEqual(payload["meta"]["filters"]["is_active"], True)
        self.assertEqual(payload["meta"]["filters"]["group_id"], group.pk)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 1)
        self.assertEqual(payload["data"][0]["username"], "ana")

    def test_users_collection_rejects_invalid_query_parameter(self) -> None:
        """Filtros inválidos devem retornar erro padronizado."""

        _api_user, raw_token = self._issue_token(can_read=True)

        response = self.client.get(
            reverse("api_panel_users_collection"),
            {"is_active": "talvez"},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"]["code"],
            "invalid_query_parameter",
        )

    def test_users_collection_creates_user_with_create_permission(self) -> None:
        """POST deve criar usuário quando o token tiver permissão de criação."""

        _user, raw_token = self._issue_token(can_create=True)

        response = self.client.post(
            reverse("api_panel_users_collection"),
            data=json.dumps(
                {
                    "username": "novo-api",
                    "email": "novo@example.com",
                    "password": "SenhaSegura@123",
                    "is_active": True,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="novo-api").exists())
        self.assertEqual(response.json()["data"]["username"], "novo-api")

    def test_user_detail_updates_and_deletes_with_crud_permissions(self) -> None:
        """PATCH e DELETE devem respeitar o token com update/delete."""

        _user, raw_token = self._issue_token(can_update=True, can_delete=True)
        target = User.objects.create_user(
            username="alvo-api",
            email="alvo@example.com",
            password="SenhaSegura@123",
        )
        detail_url = reverse("api_panel_user_detail", args=[target.pk])

        update_response = self.client.patch(
            detail_url,
            data=json.dumps({"email": "alterado@example.com"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["email"], "alterado@example.com")
        target.refresh_from_db()
        self.assertEqual(target.email, "alterado@example.com")

        delete_response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(delete_response.status_code, 200)
        payload = delete_response.json()
        self.assertEqual(
            payload["data"],
            {"deleted": True, "resource": "panel.users", "id": target.pk},
        )
        self.assertEqual(payload["meta"]["method"], "DELETE")
        self.assertEqual(payload["meta"]["path"], detail_url)
        self.assertEqual(payload["meta"]["request_id"], delete_response["X-Request-ID"])
        self.assertFalse(User.objects.filter(pk=target.pk).exists())
