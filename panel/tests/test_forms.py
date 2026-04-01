"""Testes dos formulários do painel."""

from core.models import ApiAccessProfile, ApiResourcePermission
from django.test import TestCase

from panel.users.forms import PanelUserForm


class PanelUserFormTests(TestCase):
    """Valida os campos extras do cadastro de usuario no painel."""

    def test_form_save_persists_api_access_settings(self):
        """Salvar o formulario deve gravar API habilitada e matriz CRUD."""

        form = PanelUserForm(
            data={
                "username": "integracao",
                "first_name": "Usuário",
                "last_name": "API",
                "email": "integracao@example.com",
                "password": "SenhaSegura@123",
                "is_active": "on",
                "auto_refresh_enabled": "on",
                "auto_refresh_interval": "30",
                "api_enabled": "on",
                "api_core_api_access_create": "on",
                "api_core_api_access_read": "on",
                "api_core_api_access_update": "on",
                "api_core_api_access_delete": "on",
                "api_panel_users_read": "on",
                "api_panel_users_update": "on",
                "api_core_audit_logs_create": "on",
                "api_core_audit_logs_read": "on",
                "api_core_audit_logs_update": "on",
                "api_core_audit_logs_delete": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        access_profile = ApiAccessProfile.objects.get(user=user)
        self.assertTrue(access_profile.api_enabled)

        users_permission = ApiResourcePermission.objects.get(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.PANEL_USERS,
        )
        self.assertTrue(users_permission.can_read)
        self.assertTrue(users_permission.can_update)
        self.assertFalse(users_permission.can_create)
        self.assertFalse(users_permission.can_delete)

        api_access_permission = ApiResourcePermission.objects.get(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.CORE_API_ACCESS,
        )
        self.assertTrue(api_access_permission.can_read)
        self.assertFalse(api_access_permission.can_create)
        self.assertFalse(api_access_permission.can_update)
        self.assertFalse(api_access_permission.can_delete)

        audit_logs_permission = ApiResourcePermission.objects.get(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.CORE_AUDIT_LOGS,
        )
        self.assertTrue(audit_logs_permission.can_read)
        self.assertFalse(audit_logs_permission.can_create)
        self.assertFalse(audit_logs_permission.can_update)
        self.assertFalse(audit_logs_permission.can_delete)
