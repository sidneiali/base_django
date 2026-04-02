"""Testes do comando de seed dos modulos iniciais."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from core import canonical_modules
from core.initial_modules import INITIAL_MODULES as BASE_INITIAL_MODULES
from core.models import Module


class SeedInitialModulesCommandTests(TestCase):
    """Valida o seed idempotente dos modulos iniciais."""

    def test_canonical_catalog_builds_from_initial_and_additional_sources(self) -> None:
        """O catalogo final deve conter os modulos iniciais e aceitar extras sem conflito."""

        canonical_slugs = {definition.slug for definition in canonical_modules.INITIAL_MODULES}

        self.assertTrue(BASE_INITIAL_MODULES.keys() <= canonical_slugs)

        extra_modules = {
            "relatorios": {
                "name": "Relatórios",
                "description": "Área adicional do projeto",
                "icon": "ti ti-report",
                "url_name": "module_entry",
                "app_label": "",
                "permission_codename": "",
                "menu_group": "Operação",
                "order": 90,
            }
        }
        with patch.dict(canonical_modules.MODULES, extra_modules, clear=True):
            built = canonical_modules._build_canonical_module_map()

        self.assertIn("relatorios", built)
        self.assertEqual(built["relatorios"]["name"], "Relatórios")
        self.assertTrue(BASE_INITIAL_MODULES.keys() <= built.keys())

    def test_canonical_catalog_rejects_duplicate_slugs(self) -> None:
        """Slug duplicado entre bases inicial e adicional deve falhar cedo."""

        duplicated = {
            "usuarios": {
                "name": "Usuários duplicado",
                "description": "Nao deveria entrar",
                "icon": "ti ti-alert-circle",
                "url_name": "module_entry",
                "app_label": "",
                "permission_codename": "",
                "menu_group": "Teste",
                "order": 999,
            }
        }

        with patch.dict(canonical_modules.MODULES, duplicated, clear=True):
            with self.assertRaisesMessage(
                ValueError,
                "Slugs canonicos duplicados entre initial_modules e modules: usuarios",
            ):
                canonical_modules._build_canonical_module_map()

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
        docs_module = Module.objects.get(slug="documentacao-api")
        self.assertFalse(docs_module.show_in_dashboard)
        self.assertTrue(docs_module.show_in_sidebar)

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
        docs_module = Module.objects.get(slug="documentacao-api")
        self.assertFalse(docs_module.show_in_dashboard)
        self.assertTrue(docs_module.show_in_sidebar)
        self.assertIn("0 criado(s), 5 atualizado(s)", stdout.getvalue())
