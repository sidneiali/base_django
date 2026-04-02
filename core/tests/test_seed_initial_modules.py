"""Testes do comando de seed dos modulos iniciais."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Module


class SeedInitialModulesCommandTests(TestCase):
    """Valida o seed idempotente dos modulos iniciais."""

    def test_command_creates_expected_modules(self) -> None:
        """O seed deve criar os modulos canonicos do dashboard."""

        stdout = StringIO()

        call_command("seed_initial_modules", stdout=stdout)

        self.assertEqual(Module.objects.count(), 5)
        self.assertTrue(Module.objects.filter(slug="modulos").exists())
        self.assertTrue(Module.objects.filter(slug="usuarios").exists())
        self.assertTrue(Module.objects.filter(slug="grupos").exists())
        self.assertTrue(Module.objects.filter(slug="auditoria").exists())
        self.assertTrue(Module.objects.filter(slug="documentacao-api").exists())
        self.assertFalse(
            Module.objects.filter(show_in_dashboard=False).exists()
        )
        self.assertFalse(
            Module.objects.filter(show_in_sidebar=False).exists()
        )

    def test_command_is_idempotent_and_refreshes_canonical_fields(self) -> None:
        """Rerodar o seed nao deve duplicar registros e deve restaurar o catalogo."""

        call_command("seed_initial_modules")
        Module.objects.filter(slug="usuarios").update(
            description="Descricao alterada manualmente",
            menu_group="Outro grupo",
            order=999,
        )

        stdout = StringIO()
        call_command("seed_initial_modules", stdout=stdout)

        self.assertEqual(Module.objects.count(), 5)

        users_module = Module.objects.get(slug="usuarios")
        self.assertEqual(users_module.description, "Gestão de usuários do sistema")
        self.assertEqual(users_module.menu_group, "Configurações")
        self.assertEqual(users_module.order, 10)
        self.assertTrue(users_module.show_in_dashboard)
        self.assertTrue(users_module.show_in_sidebar)
        self.assertIn("0 criado(s), 5 atualizado(s)", stdout.getvalue())
