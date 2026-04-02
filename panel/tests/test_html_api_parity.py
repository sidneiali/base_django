"""Testes de paridade entre os fluxos HTML e JSON do painel."""

from __future__ import annotations

import json

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken, Module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PanelHtmlApiParityTests(TestCase):
    """Garante que HTML e API apliquem as mesmas regras de negócio."""

    def _login_with_permissions(self, *codenames: str) -> None:
        """Autentica um operador com as permissões informadas."""

        index = User.objects.count() + 1
        user = User.objects.create_user(
            username=f"operador-parity-{index}",
            email=f"operador-parity-{index}@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(Permission.objects.filter(codename__in=codenames))
        user.user_permissions.add(*permissions)
        self.client.force_login(user)

    def _issue_token(self, resource: str, **permissions: bool) -> str:
        """Emite um token Bearer com a matriz de acesso informada."""

        index = User.objects.count() + 1
        user = User.objects.create_user(
            username=f"api-parity-{index}",
            email=f"api-parity-{index}@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=resource,
            **permissions,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return raw_token

    def test_protected_group_name_is_rejected_in_html_and_api(self) -> None:
        """HTML e API devem bloquear o mesmo nome reservado de grupo."""

        self._login_with_permissions("add_group")
        raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_GROUPS,
            can_create=True,
        )

        html_response = self.client.post(
            reverse("panel_group_create"),
            {"name": "Root"},
        )
        api_response = self.client.post(
            reverse("api_panel_groups_collection"),
            data=json.dumps({"name": "Root"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(html_response.status_code, 200)
        self.assertContains(html_response, "Esse grupo é protegido.")
        self.assertEqual(api_response.status_code, 400)
        self.assertEqual(api_response.json()["error"]["code"], "validation_error")
        self.assertEqual(
            api_response.json()["error"]["fields"]["name"][0]["message"],
            "Esse grupo é protegido.",
        )
        self.assertFalse(Group.objects.filter(name="Root").exists())

    def test_blocked_group_permission_is_rejected_in_html_and_api(self) -> None:
        """HTML e API devem rejeitar permissões fora da lista editável do painel."""

        self._login_with_permissions("add_group")
        raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_GROUPS,
            can_create=True,
        )
        blocked_permission = Permission.objects.filter(
            content_type__app_label="sessions"
        ).first()
        assert blocked_permission is not None

        html_response = self.client.post(
            reverse("panel_group_create"),
            {
                "name": "Grupo bloqueado no HTML",
                "permissions": [str(blocked_permission.pk)],
            },
        )
        api_response = self.client.post(
            reverse("api_panel_groups_collection"),
            data=json.dumps(
                {
                    "name": "Grupo bloqueado na API",
                    "permissions": [blocked_permission.pk],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(html_response.status_code, 200)
        self.assertContains(html_response, "não é uma das escolhas disponíveis.")
        self.assertEqual(api_response.status_code, 400)
        self.assertEqual(api_response.json()["error"]["code"], "validation_error")
        self.assertIn(
            "não é uma das escolhas disponíveis.",
            api_response.json()["error"]["fields"]["permissions"][0]["message"],
        )
        self.assertFalse(Group.objects.filter(name__icontains="bloqueado").exists())

    def test_invalid_module_route_is_rejected_in_html_and_api(self) -> None:
        """HTML e API devem validar o nome de rota do módulo do mesmo jeito."""

        self._login_with_permissions("add_module")
        raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            can_create=True,
        )
        payload = {
            "name": "Destino inválido",
            "slug": "destino-invalido",
            "description": "Teste cruzado",
            "icon": "ti ti-alert-triangle",
            "url_name": "admin:app_list",
            "menu_group": "Teste",
            "order": 10,
            "is_active": True,
            "show_in_dashboard": True,
            "show_in_sidebar": True,
        }

        html_response = self.client.post(reverse("panel_module_create"), payload)
        api_response = self.client.post(
            reverse("api_panel_modules_collection"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(html_response.status_code, 200)
        self.assertContains(
            html_response,
            "Informe um nome de rota válido sem argumentos obrigatórios.",
        )
        self.assertEqual(api_response.status_code, 400)
        self.assertEqual(api_response.json()["error"]["code"], "validation_error")
        self.assertEqual(
            api_response.json()["error"]["fields"]["url_name"][0]["message"],
            "Informe um nome de rota válido sem argumentos obrigatórios.",
        )
        self.assertFalse(Module.objects.filter(slug="destino-invalido").exists())

    def test_generic_module_entry_clears_permission_in_html_and_api(self) -> None:
        """HTML e API devem limpar a permissão ao voltar para a entrada genérica."""

        self._login_with_permissions("change_module")
        raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            can_update=True,
        )
        permission = Permission.objects.get(codename="view_auditlog")
        html_module = Module.objects.create(
            name="Auditoria HTML",
            slug="auditoria-html",
            description="Área pronta",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=30,
            is_active=True,
        )
        api_module = Module.objects.create(
            name="Auditoria API",
            slug="auditoria-api",
            description="Área pronta",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=30,
            is_active=True,
        )

        html_response = self.client.post(
            reverse("panel_module_update", args=[html_module.pk]),
            {
                "name": "Auditoria HTML",
                "slug": "auditoria-html",
                "description": "Área em reorganização",
                "icon": "ti ti-history",
                "url_name": "module_entry",
                "menu_group": "Segurança",
                "order": "35",
                "permission": "",
                "is_active": "on",
                "show_in_dashboard": "on",
                "show_in_sidebar": "on",
            },
        )
        api_response = self.client.patch(
            reverse("api_panel_module_detail", args=[api_module.pk]),
            data=json.dumps(
                {
                    "description": "Área em reorganização",
                    "url_name": "module_entry",
                    "order": 35,
                    "permission": None,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(permission.codename, "view_auditlog")
        self.assertEqual(html_response.status_code, 302)
        self.assertEqual(api_response.status_code, 200)

        html_module.refresh_from_db()
        api_module.refresh_from_db()

        for module in (html_module, api_module):
            with self.subTest(slug=module.slug):
                self.assertTrue(module.uses_generic_entry)
                self.assertEqual(module.app_label, "")
                self.assertEqual(module.permission_codename, "")
                self.assertEqual(module.description, "Área em reorganização")
                self.assertEqual(module.order, 35)

    def test_module_delete_block_reason_matches_between_html_and_api(self) -> None:
        """HTML e API devem expor o mesmo motivo de bloqueio na exclusão."""

        self._login_with_permissions("delete_module")
        raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            can_delete=True,
        )
        html_module = Module.objects.create(
            name="CRM ativo HTML",
            slug="crm-ativo-html",
            description="Módulo ainda em uso",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Comercial",
            order=10,
            is_active=True,
        )
        api_module = Module.objects.create(
            name="CRM ativo API",
            slug="crm-ativo-api",
            description="Módulo ainda em uso",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Comercial",
            order=10,
            is_active=True,
        )

        html_response = self.client.post(
            reverse("panel_module_delete", args=[html_module.pk]),
        )
        api_response = self.client.delete(
            reverse("api_panel_module_detail", args=[api_module.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(html_response.status_code, 400)
        self.assertEqual(api_response.status_code, 400)
        self.assertContains(
            html_response,
            "Inative o módulo antes de solicitar a exclusão.",
            status_code=400,
        )
        self.assertEqual(
            api_response.json()["error"]["detail"],
            "Inative o módulo antes de solicitar a exclusão.",
        )
        self.assertEqual(api_response.json()["error"]["code"], "delete_not_allowed")
        self.assertTrue(Module.objects.filter(pk=html_module.pk).exists())
        self.assertTrue(Module.objects.filter(pk=api_module.pk).exists())
