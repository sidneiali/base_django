"""Testes da navegação autenticada do shell principal."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from core import navigation
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

    def test_dashboard_and_sidebar_share_request_scoped_module_cache(self) -> None:
        """O dashboard e o sidebar devem reutilizar a mesma montagem por request."""

        user = User.objects.create_user(
            username="cacheado",
            email="cacheado@example.com",
            password="SenhaSegura@123",
        )
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

        with patch(
            "core.navigation.build_modules_for_user",
            wraps=navigation.build_modules_for_user,
        ) as mocked_builder:
            response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked_builder.call_count, 1)

    def test_superuser_topbar_exposes_shell_shortcuts_without_seeded_modules(self):
        """O topo deve expor as áreas operacionais mesmo sem módulos seedados no banco."""

        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="SenhaSegura@123",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-topbar-shortcut="users"',
            html=False,
        )
        self.assertContains(
            response,
            'data-topbar-shortcut="modules"',
            html=False,
        )
        self.assertContains(
            response,
            'data-topbar-shortcut="groups"',
            html=False,
        )
        self.assertContains(
            response,
            'data-topbar-shortcut="audit"',
            html=False,
        )
        self.assertContains(
            response,
            'data-topbar-shortcut="api-docs"',
            html=False,
        )
        self.assertContains(
            response,
            'data-topbar-shortcut="admin-users"',
            html=False,
        )
        self.assertContains(response, reverse("panel_users_list"))
        self.assertContains(response, reverse("panel_modules_list"))
        self.assertContains(response, reverse("panel_groups_list"))
        self.assertContains(response, reverse("panel_audit_logs_list"))
        self.assertContains(response, reverse("api_docs"))
        self.assertContains(response, reverse("admin:auth_user_changelist"))

    def test_topbar_shortcuts_follow_permissions_when_modules_are_absent(self):
        """O topo deve continuar útil mesmo quando a navegação por módulos ainda não foi seedada."""

        user = User.objects.create_user(
            username="operador",
            email="operador@example.com",
            password="SenhaSegura@123",
        )
        user.user_permissions.add(
            Permission.objects.get(codename="view_module"),
            Permission.objects.get(codename="view_auditlog"),
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-topbar-shortcut="modules"',
            html=False,
        )
        self.assertContains(
            response,
            'data-topbar-shortcut="audit"',
            html=False,
        )
        self.assertNotContains(
            response,
            'data-topbar-shortcut="users"',
            html=False,
        )
        self.assertNotContains(
            response,
            'data-topbar-shortcut="groups"',
            html=False,
        )
