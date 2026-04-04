"""Testes dos formulários do painel."""

from core.api.access import (
    build_default_api_permission_matrix,
    save_user_api_access,
)
from core.models import (
    ApiAccessProfile,
    ApiResourcePermission,
    GroupInterfacePreference,
    UserInterfacePreference,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from panel.groups.forms import PanelGroupForm
from panel.users.forms import PanelUserForm

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
        self.assertFalse(user.has_usable_password())

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

    def test_form_create_requires_email_for_first_access_invitation(self):
        """Novos usuários precisam de e-mail para o convite inicial."""

        form = PanelUserForm(
            data={
                "username": "sem-email",
                "first_name": "Sem",
                "last_name": "Email",
                "password": "",
                "auto_refresh_interval": "30",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

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

    def test_form_limits_groups_and_api_to_acting_user_scope(self):
        """O operador só pode ver grupos e flags de API dentro do próprio teto."""

        acting_user = User.objects.create_user(
            username="operador-form-user",
            email="operador-form-user@example.com",
            password="SenhaSegura@123",
        )
        view_user_permission = Permission.objects.get(codename="view_user")
        delete_user_permission = Permission.objects.get(codename="delete_user")
        acting_user.user_permissions.add(view_user_permission)

        api_permissions = build_default_api_permission_matrix()
        api_permissions[ApiResourcePermission.Resource.PANEL_USERS]["can_read"] = True
        save_user_api_access(
            acting_user,
            api_enabled=True,
            permissions=api_permissions,
        )

        allowed_group = Group.objects.create(name="Leitura User")
        allowed_group.permissions.add(view_user_permission)
        blocked_group = Group.objects.create(name="Delete User")
        blocked_group.permissions.add(delete_user_permission)

        form = PanelUserForm(acting_user=acting_user)

        self.assertQuerySetEqual(
            form.fields["groups"].queryset.order_by("name"),
            [allowed_group],
            transform=lambda group: group,
        )
        self.assertFalse(form.fields["api_panel_users_read"].disabled)
        self.assertTrue(form.fields["api_panel_users_delete"].disabled)


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

    def test_form_limits_permissions_to_acting_user_scope(self):
        """O operador só pode escolher permissões que já possui na própria conta."""

        acting_user = User.objects.create_user(
            username="operador-form-group",
            email="operador-form-group@example.com",
            password="SenhaSegura@123",
        )
        view_user_permission = Permission.objects.get(codename="view_user")
        delete_user_permission = Permission.objects.get(codename="delete_user")
        acting_user.user_permissions.add(view_user_permission)

        form = PanelGroupForm(acting_user=acting_user)

        self.assertQuerySetEqual(
            form.fields["permissions"].queryset,
            [view_user_permission],
            transform=lambda permission: permission,
            ordered=False,
        )
        self.assertNotIn(
            delete_user_permission.pk,
            form.fields["permissions"].queryset.values_list("pk", flat=True),
        )
