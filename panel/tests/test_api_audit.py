"""Testes de auditoria dos endpoints JSON do painel."""

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
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PanelApiAuditTests(TestCase):
    """Valida a trilha de auditoria gerada pelos fluxos JSON do painel."""

    def _issue_token(
        self,
        resource: str,
        *,
        username: str,
        **permissions: bool,
    ) -> tuple[str, str]:
        """Cria um token Bearer ativo com permissões configuráveis no recurso."""

        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=resource,
            **permissions,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return username, raw_token

    def test_user_create_via_api_generates_audited_create_log(self) -> None:
        """Criar usuário pela API deve registrar criação com contexto completo."""

        actor_username, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_USERS,
            username="api-users-audit",
            can_create=True,
        )
        AuditLog.objects.all().delete()

        response = self.client.post(
            reverse("api_panel_users_collection"),
            data=json.dumps(
                {
                    "username": "usuario-auditado",
                    "email": "usuario-auditado@example.com",
                    "password": "SenhaSegura@123",
                    "is_active": True,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        created_user = User.objects.get(username="usuario-auditado")
        log = AuditLog.objects.get(
            action=AuditLog.ACTION_CREATE,
            content_type__app_label="auth",
            content_type__model="user",
            object_id=str(created_user.pk),
        )
        self.assertEqual(log.actor_identifier, actor_username)
        self.assertEqual(log.request_method, "POST")
        self.assertEqual(log.path, reverse("api_panel_users_collection"))
        self.assertEqual(log.metadata["request_id"], response["X-Request-ID"])
        self.assertEqual(log.after["username"], "usuario-auditado")
        self.assertEqual(log.after["email"], "usuario-auditado@example.com")

    def test_group_permission_update_via_api_generates_audited_m2m_log(self) -> None:
        """Atualizar permissões de grupo via API deve gerar log M2M auditável."""

        actor_username, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_GROUPS,
            username="api-groups-audit",
            can_update=True,
        )
        group = Group.objects.create(name="Suporte API")
        permission = Permission.objects.get(codename="view_user")
        AuditLog.objects.all().delete()

        response = self.client.patch(
            reverse("api_panel_group_detail", args=[group.pk]),
            data=json.dumps(
                {
                    "name": "Suporte API",
                    "permissions": [permission.pk],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        log = AuditLog.objects.get(
            action=AuditLog.ACTION_UPDATE,
            content_type__app_label="auth",
            content_type__model="group",
            object_id=str(group.pk),
            metadata__relation="permissions",
        )
        self.assertEqual(log.actor_identifier, actor_username)
        self.assertEqual(log.request_method, "PATCH")
        self.assertEqual(log.path, reverse("api_panel_group_detail", args=[group.pk]))
        self.assertEqual(log.metadata["request_id"], response["X-Request-ID"])
        self.assertEqual(log.changes["permissions"]["operation"], "post_add")
        self.assertEqual(
            log.changes["permissions"]["changed_items"],
            [{"id": str(permission.pk), "repr": str(permission)}],
        )

    def test_module_delete_via_api_generates_audited_delete_log(self) -> None:
        """Excluir módulo pela API deve registrar o snapshot anterior do recurso."""

        actor_username, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            username="api-modules-audit",
            can_delete=True,
        )
        module = Module.objects.create(
            name="Módulo descartável",
            slug="modulo-descartavel",
            description="Módulo removido pela API",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Teste",
            order=15,
            is_active=False,
        )
        detail_url = reverse("api_panel_module_detail", args=[module.pk])
        AuditLog.objects.all().delete()

        response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 204)
        log = AuditLog.objects.get(
            action=AuditLog.ACTION_DELETE,
            content_type__app_label="core",
            content_type__model="module",
            object_id=str(module.pk),
        )
        self.assertEqual(log.actor_identifier, actor_username)
        self.assertEqual(log.request_method, "DELETE")
        self.assertEqual(log.path, detail_url)
        self.assertEqual(log.metadata["request_id"], response["X-Request-ID"])
        self.assertEqual(log.before["name"], "Módulo descartável")
        self.assertEqual(log.before["slug"], "modulo-descartavel")

    def test_blocked_module_delete_via_api_generates_denied_audit_log(self) -> None:
        """Bloqueio de exclusão de módulo deve virar evento auditável da API."""

        actor_username, raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            username="api-modules-blocked",
            can_delete=True,
        )
        module = Module.objects.create(
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
        detail_url = reverse("api_panel_module_detail", args=[module.pk])
        AuditLog.objects.all().delete()

        response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "delete_not_allowed")
        log = AuditLog.objects.get(
            action=AuditLog.ACTION_API_ACCESS_DENIED,
            content_type__app_label="core",
            content_type__model="module",
            object_id=str(module.pk),
            metadata__reason_code="delete_not_allowed",
        )
        self.assertEqual(log.actor_identifier, actor_username)
        self.assertEqual(log.request_method, "DELETE")
        self.assertEqual(log.path, detail_url)
        self.assertEqual(log.metadata["request_id"], response["X-Request-ID"])
        self.assertEqual(log.metadata["resource"], "panel.modules")
        self.assertEqual(log.metadata["action"], "delete")
        self.assertEqual(log.metadata["status"], 400)
