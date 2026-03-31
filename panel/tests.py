"""Testes do painel administrativo interno."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import ApiAccessProfile, ApiResourcePermission

from .forms import PanelUserForm

User = get_user_model()


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
                "api_panel_users_read": "on",
                "api_panel_users_update": "on",
                "api_panel_groups_read": "on",
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

        groups_permission = ApiResourcePermission.objects.get(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
        )
        self.assertTrue(groups_permission.can_read)
        self.assertFalse(
            ApiResourcePermission.objects.filter(
                access_profile=access_profile,
                resource=ApiResourcePermission.Resource.CORE_MODULES,
            ).exists()
        )
