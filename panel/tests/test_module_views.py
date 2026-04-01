"""Testes dos fluxos HTML de módulos no painel."""

from __future__ import annotations

import json

from core.models import Module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PanelModuleViewTests(TestCase):
    """Valida permissões e fluxos HTMX dos módulos no painel."""

    def _login_with_permissions(self, *codenames: str) -> None:
        """Autentica um operador com permissões de módulos do app core."""

        user = User.objects.create_user(
            username="operador-modulos",
            email="operador-modulos@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(
            Permission.objects.filter(
                content_type__app_label="core",
                codename__in=codenames,
            )
        )
        user.user_permissions.add(*permissions)
        self.client.force_login(user)

    def test_modules_list_requires_view_permission(self) -> None:
        """Usuário autenticado sem permissão não pode listar módulos."""

        self._login_with_permissions()

        response = self.client.get(reverse("panel_modules_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_modules_list_filters_results_and_renders_partial_for_htmx(self) -> None:
        """A listagem deve filtrar módulos por texto e devolver partial no HTMX."""

        self._login_with_permissions("view_module")
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
            name="CRM",
            slug="crm",
            description="Relacionamento com clientes",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=20,
            is_active=True,
        )

        response = self.client.get(
            reverse("panel_modules_list"),
            {"q": "fin"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Módulos"', html=False)
        self.assertContains(response, "Financeiro")
        self.assertNotContains(response, "CRM")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_module_create_htmx_creates_module_and_redirects(self) -> None:
        """Criar módulo via HTMX deve persistir e responder com HX-Location."""

        self._login_with_permissions("add_module")
        permission = Permission.objects.get(
            content_type__app_label="core",
            codename="view_auditlog",
        )

        response = self.client.post(
            reverse("panel_module_create"),
            {
                "name": "Logs avançados",
                "slug": "logs-avancados",
                "description": "Acesso detalhado aos eventos",
                "icon": "ti ti-history",
                "url_name": "panel_audit_logs_list",
                "menu_group": "Segurança",
                "order": "45",
                "is_active": "on",
                "permission": str(permission.pk),
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_modules_list"))

        module = Module.objects.get(slug="logs-avancados")
        self.assertEqual(module.app_label, "core")
        self.assertEqual(module.permission_codename, "view_auditlog")
        self.assertEqual(module.url_name, "panel_audit_logs_list")
        self.assertTrue(module.is_active)

    def test_module_create_rejects_invalid_route_name(self) -> None:
        """O formulário deve bloquear rotas inexistentes ou que peçam argumentos."""

        self._login_with_permissions("add_module")

        response = self.client.post(
            reverse("panel_module_create"),
            {
                "name": "Destino quebrado",
                "slug": "destino-quebrado",
                "description": "Teste",
                "icon": "ti ti-alert-triangle",
                "url_name": "admin:app_list",
                "menu_group": "Teste",
                "order": "10",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Informe um nome de rota válido sem argumentos obrigatórios.",
        )
        self.assertFalse(Module.objects.filter(slug="destino-quebrado").exists())

    def test_module_update_can_switch_to_generic_entry_and_clear_permission(self) -> None:
        """A edição deve permitir voltar para a entrada genérica sem permissão."""

        self._login_with_permissions("change_module")
        module = Module.objects.create(
            name="Auditoria operacional",
            slug="auditoria-operacional",
            description="Área pronta",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=30,
            is_active=True,
        )

        response = self.client.post(
            reverse("panel_module_update", args=[module.pk]),
            {
                "name": "Auditoria operacional",
                "slug": "auditoria-operacional",
                "description": "Área em reorganização",
                "icon": "ti ti-history",
                "url_name": "module_entry",
                "menu_group": "Segurança",
                "order": "35",
                "permission": "",
                "is_active": "on",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        module.refresh_from_db()
        self.assertTrue(module.uses_generic_entry)
        self.assertEqual(module.app_label, "")
        self.assertEqual(module.permission_codename, "")
        self.assertEqual(module.order, 35)
