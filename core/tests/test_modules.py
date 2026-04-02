"""Testes do model Module e da entrada genérica de módulos."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from core.models import Module

User = get_user_model()


class ModuleModelTests(TestCase):
    """Valida o comportamento central do model de módulo."""

    def test_generic_entry_resolves_url_with_slug(self) -> None:
        """Módulos genéricos precisam apontar para a rota por slug."""

        module = Module.objects.create(
            name="Relatórios",
            slug="relatorios",
            description="Área em construção",
            icon="ti ti-report",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )

        self.assertTrue(module.uses_generic_entry)
        self.assertEqual(
            module.get_absolute_url(),
            reverse("module_entry", args=[module.slug]),
        )
        self.assertEqual(module.permission_label, "Apenas login no sistema")
        self.assertEqual(module.visibility_label, "Dashboard e sidebar")


class ModuleEntryViewTests(TestCase):
    """Valida a experiência da rota genérica de módulos."""

    def test_module_entry_requires_configured_permission(self) -> None:
        """Usuários sem a permissão exigida devem receber 403."""

        user = User.objects.create_user(
            username="sem-permissao",
            email="sem-permissao@example.com",
            password="SenhaSegura@123",
        )
        module = Module.objects.create(
            name="Auditoria interna",
            slug="auditoria-interna",
            description="Painel interno de auditoria",
            icon="ti ti-history",
            url_name="module_entry",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=10,
            is_active=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("module_entry", args=[module.slug]))

        self.assertEqual(response.status_code, 403)

    def test_module_entry_renders_operational_summary_for_generic_module(self) -> None:
        """A página genérica deve mostrar os metadados úteis do módulo."""

        user = User.objects.create_user(
            username="operador-modulo",
            email="operador-modulo@example.com",
            password="SenhaSegura@123",
        )
        permission = Permission.objects.get(codename="view_auditlog")
        user.user_permissions.add(permission)
        module = Module.objects.create(
            name="Auditoria interna",
            slug="auditoria-interna",
            description="Painel interno de auditoria",
            icon="ti ti-history",
            url_name="module_entry",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=10,
            is_active=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("module_entry", args=[module.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Auditoria interna"', html=False)
        self.assertContains(response, "Módulo genérico")
        self.assertContains(response, "Em preparação")
        self.assertContains(response, module.slug)
        self.assertContains(response, module.menu_group)
        self.assertContains(response, module.permission_label)
