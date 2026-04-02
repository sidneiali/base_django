"""Assistente interativo para criacao de novos modulos do shell."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.management.module_cli import ModuleCommandPrompts


class Command(BaseCommand):
    """Cria um novo modulo com perguntas guiadas no terminal."""

    help = "Cria um novo modulo do shell com perguntas sobre rota, permissao e visibilidade."

    def handle(self, *args: object, **options: object) -> None:
        """Executa o assistente de criacao e salva via formulario real."""

        prompts = ModuleCommandPrompts(self)
        prompts.write_canonical_modules()
        slug = prompts.prompt_new_slug()

        self.stdout.write(self.style.WARNING("Criando um novo modulo."))

        form = prompts.build_form(slug=slug, lock_slug=True)
        if not form.is_valid():
            raise CommandError(prompts.format_form_errors(form))

        module = form.save()
        self.stdout.write(
            self.style.SUCCESS(f"Modulo {module.slug} criado com sucesso.")
        )
        self.stdout.write(f"- URL final: {module.get_absolute_url()}")
        self.stdout.write(f"- Permissao: {module.permission_label}")
        self.stdout.write(f"- Exibicao: {module.visibility_label}")
        if not module.is_initial_module:
            self.stdout.write(
                "- Dica: modulos de areas em core/ ou panel/ entram no catalogo canonico; replique a definicao em core/modules.py e, se fizer parte do conjunto inicial, inclua o slug em core/initial_modules.py."
            )
