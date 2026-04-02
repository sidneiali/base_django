"""Remove um unico modulo escolhido da lista atual do shell."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.management.module_cli import ModuleCommandPrompts


class Command(BaseCommand):
    """Permite escolher e remover um unico modulo cadastrado."""

    help = "Pergunta qual modulo existente deve ser removido do shell."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        """Exibe a lista atual, escolhe um modulo e confirma a remocao."""

        prompts = ModuleCommandPrompts(self)
        module = prompts.prompt_existing_module()

        self.stdout.write(
            self.style.WARNING(
                f"Modulo selecionado: {module.name} ({module.slug})"
            )
        )
        self.stdout.write(f"- Grupo: {module.menu_group}")
        self.stdout.write(f"- Exibicao: {module.visibility_label}")
        self.stdout.write(f"- Permissao: {module.permission_label}")

        if not prompts.prompt_bool("Remover este modulo?", default=False):
            self.stdout.write("Operacao cancelada.")
            return

        slug = module.slug
        module.delete()
        self.stdout.write(self.style.SUCCESS(f"Modulo {slug} removido com sucesso."))
