"""Testes de paridade de auditoria entre os fluxos HTML e JSON do painel."""

from __future__ import annotations

import json

from core.models import (
    ApiAccessProfile,
    ApiResourcePermission,
    ApiToken,
    AuditLog,
    Module,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class PanelHtmlApiAuditParityTests(TestCase):
    """Garante trilha auditável coerente entre painel HTML e API JSON."""

    def _login_with_permissions(self, client: Client, *codenames: str) -> str:
        """Autentica um operador com as permissões informadas no client recebido."""

        index = User.objects.count() + 1
        user = User.objects.create_user(
            username=f"operador-audit-{index}",
            email=f"operador-audit-{index}@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(Permission.objects.filter(codename__in=codenames))
        user.user_permissions.add(*permissions)
        client.force_login(user)
        return user.username

    def _issue_token(self, resource: str, **permissions: bool) -> tuple[str, str]:
        """Emite um token Bearer com a matriz de acesso informada."""

        index = User.objects.count() + 1
        user = User.objects.create_user(
            username=f"api-audit-{index}",
            email=f"api-audit-{index}@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=resource,
            **permissions,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return user.username, raw_token

    def _assert_log_context(
        self,
        log: AuditLog,
        *,
        actor_identifier: str,
        request_method: str,
        path: str,
        request_id: str,
    ) -> None:
        """Confere o contexto básico da requisição capturado no log."""

        self.assertEqual(log.actor_identifier, actor_identifier)
        self.assertEqual(log.request_method, request_method)
        self.assertEqual(log.path, path)
        self.assertEqual(log.metadata["request_id"], request_id)

    def test_group_permission_update_is_audited_in_html_and_api(self) -> None:
        """HTML e API devem gerar a mesma trilha M2M ao alterar permissões de grupo."""

        permission = Permission.objects.get(codename="view_user")
        html_client = Client()
        html_actor = self._login_with_permissions(html_client, "change_group")
        html_group = Group.objects.create(name="Suporte HTML")

        AuditLog.objects.all().delete()
        html_response = html_client.post(
            reverse("panel_group_update", args=[html_group.pk]),
            {
                "name": "Suporte HTML",
                "permissions": [str(permission.pk)],
            },
        )

        self.assertEqual(html_response.status_code, 302)
        html_log = AuditLog.objects.get(
            action=AuditLog.ACTION_UPDATE,
            content_type__app_label="auth",
            content_type__model="group",
            object_id=str(html_group.pk),
            metadata__relation="permissions",
        )
        self._assert_log_context(
            html_log,
            actor_identifier=html_actor,
            request_method="POST",
            path=reverse("panel_group_update", args=[html_group.pk]),
            request_id=html_response["X-Request-ID"],
        )
        self.assertEqual(html_log.changes["permissions"]["operation"], "post_add")
        self.assertEqual(
            html_log.changes["permissions"]["changed_items"],
            [{"id": str(permission.pk), "repr": str(permission)}],
        )

        api_client = Client()
        api_actor, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_GROUPS,
            can_update=True,
        )
        api_group = Group.objects.create(name="Suporte API")

        AuditLog.objects.all().delete()
        api_response = api_client.patch(
            reverse("api_panel_group_detail", args=[api_group.pk]),
            data=json.dumps(
                {
                    "name": "Suporte API",
                    "permissions": [permission.pk],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(api_response.status_code, 200)
        api_log = AuditLog.objects.get(
            action=AuditLog.ACTION_UPDATE,
            content_type__app_label="auth",
            content_type__model="group",
            object_id=str(api_group.pk),
            metadata__relation="permissions",
        )
        self._assert_log_context(
            api_log,
            actor_identifier=api_actor,
            request_method="PATCH",
            path=reverse("api_panel_group_detail", args=[api_group.pk]),
            request_id=api_response["X-Request-ID"],
        )
        self.assertEqual(api_log.changes["permissions"]["operation"], "post_add")
        self.assertEqual(
            api_log.changes["permissions"]["changed_items"],
            [{"id": str(permission.pk), "repr": str(permission)}],
        )

    def test_module_update_is_audited_in_html_and_api(self) -> None:
        """HTML e API devem registrar a mesma mudança relevante ao editar módulo."""

        html_client = Client()
        html_actor = self._login_with_permissions(html_client, "change_module")
        html_module = Module.objects.create(
            name="Auditoria HTML",
            slug="auditoria-html-audit",
            description="Área pronta",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=30,
            is_active=True,
        )

        AuditLog.objects.all().delete()
        html_response = html_client.post(
            reverse("panel_module_update", args=[html_module.pk]),
            {
                "name": "Auditoria HTML",
                "slug": "auditoria-html-audit",
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

        self.assertEqual(html_response.status_code, 302)
        html_log = AuditLog.objects.get(
            action=AuditLog.ACTION_UPDATE,
            content_type__app_label="core",
            content_type__model="module",
            object_id=str(html_module.pk),
        )
        self._assert_log_context(
            html_log,
            actor_identifier=html_actor,
            request_method="POST",
            path=reverse("panel_module_update", args=[html_module.pk]),
            request_id=html_response["X-Request-ID"],
        )
        for field_name in ("description", "url_name", "app_label", "permission_codename", "order"):
            with self.subTest(flow="html", field=field_name):
                self.assertIn(field_name, html_log.changes)
        self.assertEqual(html_log.changes["url_name"]["after"], "module_entry")
        self.assertEqual(html_log.changes["app_label"]["after"], "")
        self.assertEqual(html_log.changes["permission_codename"]["after"], "")

        api_client = Client()
        api_actor, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            can_update=True,
        )
        api_module = Module.objects.create(
            name="Auditoria API",
            slug="auditoria-api-audit",
            description="Área pronta",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=30,
            is_active=True,
        )

        AuditLog.objects.all().delete()
        api_response = api_client.patch(
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

        self.assertEqual(api_response.status_code, 200)
        api_log = AuditLog.objects.get(
            action=AuditLog.ACTION_UPDATE,
            content_type__app_label="core",
            content_type__model="module",
            object_id=str(api_module.pk),
        )
        self._assert_log_context(
            api_log,
            actor_identifier=api_actor,
            request_method="PATCH",
            path=reverse("api_panel_module_detail", args=[api_module.pk]),
            request_id=api_response["X-Request-ID"],
        )
        for field_name in ("description", "url_name", "app_label", "permission_codename", "order"):
            with self.subTest(flow="api", field=field_name):
                self.assertIn(field_name, api_log.changes)
        self.assertEqual(api_log.changes["url_name"]["after"], "module_entry")
        self.assertEqual(api_log.changes["app_label"]["after"], "")
        self.assertEqual(api_log.changes["permission_codename"]["after"], "")

    def test_module_delete_is_audited_in_html_and_api(self) -> None:
        """HTML e API devem registrar o snapshot anterior ao excluir módulo."""

        html_client = Client()
        html_actor = self._login_with_permissions(html_client, "delete_module")
        html_module = Module.objects.create(
            name="Módulo removido HTML",
            slug="modulo-removido-html",
            description="Módulo removido pelo painel",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Teste",
            order=15,
            is_active=False,
        )

        AuditLog.objects.all().delete()
        html_response = html_client.post(
            reverse("panel_module_delete", args=[html_module.pk]),
        )

        self.assertEqual(html_response.status_code, 302)
        html_log = AuditLog.objects.get(
            action=AuditLog.ACTION_DELETE,
            content_type__app_label="core",
            content_type__model="module",
            object_id=str(html_module.pk),
        )
        self._assert_log_context(
            html_log,
            actor_identifier=html_actor,
            request_method="POST",
            path=reverse("panel_module_delete", args=[html_module.pk]),
            request_id=html_response["X-Request-ID"],
        )
        self.assertEqual(html_log.before["name"], "Módulo removido HTML")
        self.assertEqual(html_log.before["slug"], "modulo-removido-html")

        api_client = Client()
        api_actor, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            can_delete=True,
        )
        api_module = Module.objects.create(
            name="Módulo removido API",
            slug="modulo-removido-api",
            description="Módulo removido pela API",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Teste",
            order=15,
            is_active=False,
        )

        AuditLog.objects.all().delete()
        api_response = api_client.delete(
            reverse("api_panel_module_detail", args=[api_module.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(api_response.status_code, 204)
        api_log = AuditLog.objects.get(
            action=AuditLog.ACTION_DELETE,
            content_type__app_label="core",
            content_type__model="module",
            object_id=str(api_module.pk),
        )
        self._assert_log_context(
            api_log,
            actor_identifier=api_actor,
            request_method="DELETE",
            path=reverse("api_panel_module_detail", args=[api_module.pk]),
            request_id=api_response["X-Request-ID"],
        )
        self.assertEqual(api_log.before["name"], "Módulo removido API")
        self.assertEqual(api_log.before["slug"], "modulo-removido-api")
