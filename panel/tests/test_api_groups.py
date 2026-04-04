"""Testes dos endpoints JSON de grupos do painel."""

from __future__ import annotations

import json
from typing import cast

from core.models import ApiResourcePermission
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from .api_test_support import PanelApiTokenMixin


class PanelGroupsApiTests(PanelApiTokenMixin, TestCase):
    """Valida a superfície JSON de grupos do painel."""

    def test_groups_collection_requires_read_permission(self) -> None:
        """A listagem JSON de grupos também precisa da permissão de leitura."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS
        )

        response = self.client.get(
            reverse("api_panel_groups_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_groups_collection_lists_editable_groups_and_supports_filters(self) -> None:
        """A coleção de grupos deve excluir protegidos e aceitar filtros/paginação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )
        permission = Permission.objects.get(codename="view_user")
        clientes = Group.objects.create(name="Clientes")
        clientes.permissions.add(permission)
        Group.objects.create(name="Root")
        Group.objects.create(name="Financeiro")

        response = self.client.get(
            reverse("api_panel_groups_collection"),
            cast(
                dict[str, str | int],
                {
                    "search": "clien",
                    "permission_id": permission.pk,
                    "ordering": "-name",
                    "page_size": 1,
                },
            ),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["ordering"], "-name")
        self.assertEqual(payload["meta"]["filters"]["search"], "clien")
        self.assertEqual(payload["meta"]["filters"]["permission_id"], permission.pk)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 1)
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 1)
        self.assertEqual(payload["data"][0]["name"], "Clientes")
        self.assertEqual(payload["data"][0]["permissions_count"], 1)
        self.assertEqual(payload["data"][0]["permissions"][0]["codename"], "view_user")

    def test_groups_collection_rejects_invalid_query_parameter(self) -> None:
        """Filtros inválidos da coleção de grupos devem falhar com erro padronizado."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_panel_groups_collection"),
            {"permission_id": "talvez"},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_query_parameter")

    def test_groups_collection_creates_group_with_permissions(self) -> None:
        """POST deve criar grupo editável quando o token tiver permissão de criação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_create=True,
        )
        permission = Permission.objects.get(codename="view_user")

        response = self.client.post(
            reverse("api_panel_groups_collection"),
            data=json.dumps(
                {
                    "name": "Suporte API",
                    "permissions": [permission.pk],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        group = Group.objects.get(name="Suporte API")
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
        self.assertEqual(response.json()["data"]["permissions_count"], 1)

    def test_groups_collection_rejects_protected_group_name(self) -> None:
        """A criação deve bloquear nomes reservados do painel."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_create=True,
        )

        response = self.client.post(
            reverse("api_panel_groups_collection"),
            data=json.dumps({"name": "Root"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_group_detail_reads_updates_and_deletes(self) -> None:
        """GET, PATCH e DELETE devem funcionar para grupos editáveis."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
            can_update=True,
            can_delete=True,
        )
        permission = Permission.objects.get(codename="view_user")
        group = Group.objects.create(name="Parceiros")
        detail_url = reverse("api_panel_group_detail", args=[group.pk])

        read_response = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["data"]["name"], "Parceiros")

        update_response = self.client.patch(
            detail_url,
            data=json.dumps({"name": "Parceiros VIP", "permissions": [permission.pk]}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(update_response.status_code, 200)
        group.refresh_from_db()
        self.assertEqual(group.name, "Parceiros VIP")
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())

        delete_response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(delete_response.status_code, 200)
        payload = delete_response.json()
        self.assertEqual(
            payload["data"],
            {"deleted": True, "resource": "panel.groups", "id": group.pk},
        )
        self.assertEqual(payload["meta"]["method"], "DELETE")
        self.assertEqual(payload["meta"]["path"], detail_url)
        self.assertEqual(payload["meta"]["request_id"], delete_response["X-Request-ID"])
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_group_detail_returns_404_for_protected_group(self) -> None:
        """Grupos protegidos não devem ficar expostos na API do painel."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )
        group = Group.objects.create(name="Root")

        response = self.client.get(
            reverse("api_panel_group_detail", args=[group.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_versioned_groups_collection_alias_works(self) -> None:
        """A rota versionada também deve responder para grupos do painel."""

        _api_user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_v1_panel_groups_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())
