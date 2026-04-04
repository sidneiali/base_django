"""Testes dos formulários do painel."""

from core.models import (
    ApiAccessProfile,
    ApiResourcePermission,
    GroupInterfacePreference,
    UserInterfacePreference,
)
from django.contrib.auth.models import Permission
from django.test import TestCase

from panel.groups.forms import PanelGroupForm
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

        preference = UserInterfacePreference.objects.get(user=user)
        self.assertIsNone(preference.session_idle_timeout_minutes)

    def test_form_save_persists_user_session_idle_timeout(self):
        """Salvar o formulário deve persistir o timeout de sessão do usuário."""

        form = PanelUserForm(
            data={
                "username": "sessao-user",
                "first_name": "Sessao",
                "last_name": "User",
                "email": "sessao-user@example.com",
                "password": "SenhaSegura@123",
                "is_active": "on",
                "auto_refresh_interval": "30",
                "session_idle_timeout_minutes": "45",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        preference = UserInterfacePreference.objects.get(user=user)
        self.assertEqual(preference.session_idle_timeout_minutes, 45)


class PanelGroupFormTests(TestCase):
    """Valida os campos extras do cadastro de grupos no painel."""

    def test_form_save_persists_group_session_idle_timeout(self):
        """Salvar o formulário deve persistir a política de sessão do grupo."""

        permission = Permission.objects.get(codename="view_user")
        form = PanelGroupForm(
            data={
                "name": "Suporte Sessão",
                "permissions": [str(permission.pk)],
                "session_idle_timeout_minutes": "20",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        group = form.save()

        preference = GroupInterfacePreference.objects.get(group=group)
        self.assertEqual(preference.session_idle_timeout_minutes, 20)
