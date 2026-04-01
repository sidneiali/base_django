"""Testes da navegação autenticada do shell principal."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from core.models import Module

User = get_user_model()


class SidebarNavigationTests(TestCase):
    """Valida a renderização da navegação lateral por módulos e grupos."""

    def test_sidebar_groups_modules_and_marks_locked_entries(self):
        """O sidebar deve refletir grupos, ícones e estado de acesso do dashboard."""

        user = User.objects.create_user(
            username="lucas",
            email="lucas@example.com",
            password="SenhaSegura@123",
        )
        view_user_permission = Permission.objects.get(codename="view_user")
        user.user_permissions.add(view_user_permission)
        self.client.force_login(user)

        Module.objects.create(
            name="Usuários",
            slug="usuarios",
            description="Gestão de usuários",
            icon="ti ti-users",
            url_name="panel_users_list",
            app_label="auth",
            permission_codename="view_user",
            menu_group="Configurações",
            order=10,
            is_active=True,
        )
        Module.objects.create(
            name="Grupos",
            slug="grupos",
            description="Gestão de grupos",
            icon="ti ti-users-group",
            url_name="panel_groups_list",
            app_label="auth",
            permission_codename="view_group",
            menu_group="Segurança",
            order=20,
            is_active=True,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-sidebar-group="Configurações"', html=False)
        self.assertContains(response, 'data-sidebar-group="Segurança"', html=False)
        self.assertContains(response, "ti ti-users")
        self.assertContains(response, "ti ti-users-group")
        self.assertContains(response, reverse("panel_users_list"))
        self.assertContains(response, 'aria-disabled="true"', html=False)
        self.assertContains(response, "Grupos")
        self.assertContains(response, 'data-topbar-close-menu="true"', html=False)
