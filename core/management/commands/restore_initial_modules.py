"""Remove todo o catalogo atual de modulos do shell."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.management.module_cli import ModuleCommandPrompts
from core.models import Module


class Command(BaseCommand):
    """Remove todos os modulos cadastrados no shell."""

    help = "Remove todos os modulos cadastrados atualmente no shell."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        """Executa a limpeza completa do catalogo atual de modulos."""

        prompts = ModuleCommandPrompts(self)
        removed_count = Module.objects.count()

        if removed_count:
            prompts.write_existing_modules()
        else:
            self.stdout.write("Nenhum modulo cadastrado no momento.")

        self.stdout.write("Esse comando remove todos os modulos cadastrados atualmente.")
        if not prompts.prompt_bool("Continuar com a remocao completa?", default=False):
            self.stdout.write("Operacao cancelada.")
            return

        Module.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Remocao concluida: "
                f"{removed_count} modulo(s) removido(s)."
            )
        )
