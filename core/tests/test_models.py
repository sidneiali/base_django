"""Testes dos models e helpers de acesso da API."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.api.access import get_user_api_access_values
from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken, AuditLog

User = get_user_model()


class ApiAccessModelTests(TestCase):
    """Valida a camada inicial de acesso e token da API."""

    def test_api_token_issue_stores_only_hash_and_redacts_audit_log(self):
        """Emitir um token deve persistir apenas o hash e mascarar o log."""

        user = User.objects.create_user(username="api-user", password="senha-forte")
        AuditLog.objects.all().delete()

        token, raw_token = ApiToken.issue_for_user(user)

        self.assertNotEqual(raw_token, token.token_hash)
        self.assertEqual(token.token_prefix, raw_token[: ApiToken.PREFIX_LENGTH])
        self.assertTrue(token.matches(raw_token))
        self.assertTrue(token.is_active)

        create_log = AuditLog.objects.get(
            action=AuditLog.ACTION_CREATE,
            content_type__app_label="core",
            content_type__model="apitoken",
            object_id=str(token.pk),
        )
        self.assertEqual(create_log.after["token_hash"], "[redacted]")
        self.assertEqual(
            create_log.changes["token_hash"]["after"],
            "[redacted]",
        )

    def test_api_resource_permission_maps_crud_actions(self):
        """As flags CRUD precisam refletir corretamente a autorizacao final."""

        user = User.objects.create_user(username="carol", password="senha-forte")
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        permission = ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.PANEL_USERS,
            can_read=True,
            can_update=True,
        )

        self.assertTrue(permission.has_any_permission())
        self.assertFalse(permission.allows("create"))
        self.assertTrue(permission.allows("read"))
        self.assertTrue(permission.allows("update"))
        self.assertFalse(permission.allows("delete"))

    def test_api_access_values_ignore_legacy_resources(self):
        """Recursos antigos sem endpoint não devem quebrar a matriz atual."""

        user = User.objects.create_user(username="legacy-api", password="senha-forte")
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource="core.modules",
            can_read=True,
        )

        values = get_user_api_access_values(user)

        self.assertTrue(values["api_enabled"])
        self.assertIn(ApiResourcePermission.Resource.PANEL_USERS, values["permissions"])
        self.assertIn(ApiResourcePermission.Resource.PANEL_GROUPS, values["permissions"])
        self.assertIn(ApiResourcePermission.Resource.PANEL_MODULES, values["permissions"])
        self.assertIn(ApiResourcePermission.Resource.CORE_API_ACCESS, values["permissions"])
        self.assertIn(
            ApiResourcePermission.Resource.CORE_AUDIT_LOGS,
            values["permissions"],
        )
