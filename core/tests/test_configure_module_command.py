"""Testes dos comandos CLI de modulos do shell."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from core.models import Module


class ModuleCommandTests(TestCase):
    """Valida os assistentes CLI de criacao, edicao e restauracao."""

    def test_configure_module_creates_new_module(self) -> None:
        """O assistente de criacao deve persistir um novo modulo."""

        stdout = StringIO()
        answers = iter(
            [
                "financeiro",
                "Financeiro",
                "Painel financeiro",
                "ti ti-cash",
                "module_entry",
                "Operacao",
                "15",
                "s",
                "n",
                "s",
                "",
            ]
        )

        with patch("builtins.input", side_effect=lambda _: next(answers)):
            call_command("configure_module", stdout=stdout)

        module = Module.objects.get(slug="financeiro")
        self.assertEqual(module.name, "Financeiro")
        self.assertTrue(module.show_in_dashboard)
        self.assertFalse(module.show_in_sidebar)
        self.assertTrue(module.is_active)
        self.assertEqual(module.permission_label, "Apenas login no sistema")
        self.assertIn("Modulo financeiro criado com sucesso.", stdout.getvalue())
        self.assertIn("Modulos canonicos:", stdout.getvalue())

    def test_configure_module_reprompts_when_slug_already_exists(self) -> None:
        """Criacao deve orientar para edicao quando o slug ja existir."""

        Module.objects.create(
            name="Financeiro legado",
            slug="financeiro",
            description="Versao anterior",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operacao",
            order=10,
        )
        stdout = StringIO()
        answers = iter(
            [
                "financeiro",
                "financeiro-novo",
                "Financeiro novo",
                "Nova versao",
                "ti ti-cash",
                "module_entry",
                "Operacao",
                "20",
                "s",
                "s",
                "s",
                "",
            ]
        )

        with patch("builtins.input", side_effect=lambda _: next(answers)):
            call_command("configure_module", stdout=stdout)

        self.assertTrue(Module.objects.filter(slug="financeiro").exists())
        self.assertTrue(Module.objects.filter(slug="financeiro-novo").exists())
        self.assertIn(
            "Esse slug ja existe. Use edit_module para atualizar um modulo existente.",
            stdout.getvalue(),
        )

    def test_edit_module_updates_existing_module(self) -> None:
        """O comando de edicao deve atualizar um modulo existente."""

        module = Module.objects.create(
            name="Financeiro antigo",
            slug="financeiro",
            description="Versao anterior",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operacao",
            order=10,
            is_active=True,
            show_in_dashboard=True,
            show_in_sidebar=True,
        )
        stdout = StringIO()
        answers = iter(
            [
                "financeiro",
                "",
                "Financeiro revisado",
                "Versao nova",
                "",
                "",
                "",
                "",
                "n",
                "s",
                "n",
                "",
            ]
        )

        with patch("builtins.input", side_effect=lambda _: next(answers)):
            call_command("edit_module", stdout=stdout)

        module.refresh_from_db()
        self.assertEqual(module.name, "Financeiro revisado")
        self.assertEqual(module.description, "Versao nova")
        self.assertFalse(module.show_in_dashboard)
        self.assertTrue(module.show_in_sidebar)
        self.assertFalse(module.is_active)
        self.assertIn("Modulo financeiro atualizado com sucesso.", stdout.getvalue())
        self.assertIn("Modulos existentes:", stdout.getvalue())

    def test_restore_initial_modules_removes_all_registered_modules(self) -> None:
        """A remocao completa deve apagar todo o catalogo atual."""

        Module.objects.create(
            name="Financeiro",
            slug="financeiro",
            description="Painel financeiro",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operacao",
            order=15,
        )
        Module.objects.create(
            name="Temporario",
            slug="temporario",
            description="Area provisoria",
            icon="ti ti-box",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operacao",
            order=20,
        )
        stdout = StringIO()
        answers = iter(["s"])

        with patch("builtins.input", side_effect=lambda _: next(answers)):
            call_command("restore_initial_modules", stdout=stdout)

        self.assertEqual(Module.objects.count(), 0)
        self.assertFalse(Module.objects.filter(slug="financeiro").exists())
        self.assertFalse(Module.objects.filter(slug="temporario").exists())
        self.assertIn(
            "Remocao concluida: 2 modulo(s) removido(s).",
            stdout.getvalue(),
        )

    def test_restore_initial_module_removes_selected_module(self) -> None:
        """A remocao unitaria deve exibir a lista atual e apagar o modulo escolhido."""

        Module.objects.create(
            name="Financeiro",
            slug="financeiro",
            description="Painel financeiro",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operacao",
            order=15,
        )
        Module.objects.create(
            name="Temporario",
            slug="temporario",
            description="Area provisoria",
            icon="ti ti-box",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operacao",
            order=20,
        )
        stdout = StringIO()
        answers = iter(["financeiro", "s"])

        with patch("builtins.input", side_effect=lambda _: next(answers)):
            call_command("restore_initial_module", stdout=stdout)

        self.assertFalse(Module.objects.filter(slug="financeiro").exists())
        self.assertTrue(Module.objects.filter(slug="temporario").exists())
        self.assertIn("Modulos existentes:", stdout.getvalue())
        self.assertIn("Modulo financeiro removido com sucesso.", stdout.getvalue())
