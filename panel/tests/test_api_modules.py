"""Testes dos endpoints JSON de módulos do painel."""

from __future__ import annotations

import json

from core.models import ApiResourcePermission, Module
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .api_test_support import PanelApiTokenMixin


class PanelModulesApiTests(PanelApiTokenMixin, TestCase):
    """Valida a superfície JSON de módulos do painel."""

    def test_modules_collection_requires_read_permission(self) -> None:
        """A listagem JSON de módulos também precisa da permissão de leitura."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES
        )

        response = self.client.get(
            reverse("api_panel_modules_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_modules_collection_lists_and_filters_modules(self) -> None:
        """A coleção de módulos deve aceitar filtros explícitos e paginação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )
        permission = Permission.objects.get(codename="view_auditlog")
        Module.objects.create(
            name="Financeiro",
            slug="financeiro",
            description="Painel financeiro",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )
        Module.objects.create(
            name="Auditoria avançada",
            slug="auditoria-avancada",
            description="Eventos detalhados",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=20,
            is_active=False,
        )

        response = self.client.get(
            reverse("api_panel_modules_collection"),
            {
                "search": "auditoria",
                "permission_id": permission.pk,
                "is_active": "false",
                "ordering": "-name",
                "page_size": 1,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["ordering"], "-name")
        self.assertEqual(payload["meta"]["filters"]["search"], "auditoria")
        self.assertEqual(payload["meta"]["filters"]["permission_id"], permission.pk)
        self.assertEqual(payload["meta"]["filters"]["is_active"], False)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 1)
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 1)
        self.assertEqual(payload["data"][0]["slug"], "auditoria-avancada")
        self.assertEqual(payload["data"][0]["permission"]["codename"], "view_auditlog")
        self.assertEqual(
            payload["data"][0]["resolved_url"],
            reverse("panel_audit_logs_list"),
        )

    def test_modules_collection_rejects_invalid_query_parameter(self) -> None:
        """Filtros inválidos da coleção de módulos devem falhar com erro padronizado."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_panel_modules_collection"),
            {"is_active": "talvez"},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_query_parameter")

    def test_modules_collection_creates_module_with_permission(self) -> None:
        """POST deve criar módulo quando o token tiver permissão de criação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_create=True,
        )
        permission = Permission.objects.get(codename="view_group")

        response = self.client.post(
            reverse("api_panel_modules_collection"),
            data=json.dumps(
                {
                    "name": "Gestão de grupos",
                    "slug": "gestao-de-grupos",
                    "description": "API de grupos no painel",
                    "icon": "ti ti-users-group",
                    "url_name": "panel_groups_list",
                    "menu_group": "Segurança",
                    "order": 25,
                    "is_active": True,
                    "show_in_dashboard": True,
                    "show_in_sidebar": False,
                    "permission": permission.pk,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        module = Module.objects.get(slug="gestao-de-grupos")
        self.assertEqual(module.app_label, "auth")
        self.assertEqual(module.permission_codename, "view_group")
        self.assertTrue(module.show_in_dashboard)
        self.assertFalse(module.show_in_sidebar)
        self.assertEqual(response.json()["data"]["permission"]["id"], permission.pk)

    def test_module_detail_reads_updates_and_deletes(self) -> None:
        """GET, PATCH e DELETE devem funcionar para módulos editáveis."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
            can_update=True,
            can_delete=True,
        )
        permission = Permission.objects.get(codename="view_auditlog")
        module = Module.objects.create(
            name="Operação legada",
            slug="operacao-legada",
            description="Área antiga",
            icon="ti ti-settings",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=15,
            is_active=False,
        )
        detail_url = reverse("api_panel_module_detail", args=[module.pk])

        read_response = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["data"]["slug"], "operacao-legada")

        update_response = self.client.patch(
            detail_url,
            data=json.dumps(
                {
                    "name": "Operação auditada",
                    "url_name": "panel_audit_logs_list",
                    "permission": permission.pk,
                    "is_active": True,
                    "show_in_dashboard": False,
                    "show_in_sidebar": True,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(update_response.status_code, 200)
        module.refresh_from_db()
        self.assertEqual(module.name, "Operação auditada")
        self.assertEqual(module.url_name, "panel_audit_logs_list")
        self.assertEqual(module.app_label, "core")
        self.assertEqual(module.permission_codename, "view_auditlog")
        self.assertTrue(module.is_active)
        self.assertFalse(module.show_in_dashboard)
        self.assertTrue(module.show_in_sidebar)

        module.is_active = False
        module.save(update_fields=["is_active"])

        delete_response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(delete_response.status_code, 200)
        payload = delete_response.json()
        self.assertEqual(
            payload["data"],
            {"deleted": True, "resource": "panel.modules", "id": module.pk},
        )
        self.assertEqual(payload["meta"]["method"], "DELETE")
        self.assertEqual(payload["meta"]["path"], detail_url)
        self.assertEqual(payload["meta"]["request_id"], delete_response["X-Request-ID"])
        self.assertFalse(Module.objects.filter(pk=module.pk).exists())

    def test_module_detail_blocks_unsafe_delete(self) -> None:
        """DELETE deve bloquear módulos ativos ou canônicos do seed."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_delete=True,
        )
        active_module = Module.objects.create(
            name="CRM legado",
            slug="crm-legado",
            description="Ainda ativo",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Comercial",
            order=10,
            is_active=True,
        )
        canonical_module = Module.objects.create(
            name="Módulos",
            slug="modulos",
            description="Catálogo canônico",
            icon="ti ti-layout-grid",
            url_name="panel_modules_list",
            app_label="core",
            permission_codename="view_module",
            menu_group="Configurações",
            order=20,
            is_active=False,
        )

        active_response = self.client.delete(
            reverse("api_panel_module_detail", args=[active_module.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        canonical_response = self.client.delete(
            reverse("api_panel_module_detail", args=[canonical_module.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(active_response.status_code, 400)
        self.assertEqual(active_response.json()["error"]["code"], "delete_not_allowed")
        self.assertEqual(canonical_response.status_code, 400)
        self.assertEqual(canonical_response.json()["error"]["code"], "delete_not_allowed")

    def test_versioned_modules_collection_alias_works(self) -> None:
        """A rota versionada também deve responder para módulos do painel."""

        _api_user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_v1_panel_modules_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())
