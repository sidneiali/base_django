"""Assistente interativo para edicao de modulos existentes do shell."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.management.module_cli import ModuleCommandPrompts


class Command(BaseCommand):
    """Edita um modulo existente com perguntas guiadas no terminal."""

    help = (
        "Edita um modulo existente do shell com perguntas sobre rota, "
        "permissao e visibilidade."
    )

    def add_arguments(self, parser) -> None:
        """Aceita o slug do modulo como argumento opcional."""

        parser.add_argument(
            "slug",
            nargs="?",
            help="Slug do modulo existente que sera editado.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Executa o assistente de edicao e salva via formulario real."""

        prompts = ModuleCommandPrompts(self)
        slug = options.get("slug")
        instance = prompts.prompt_existing_module(
            slug=slug if isinstance(slug, str) else None
        )

        self.stdout.write(
            self.style.WARNING(
                f"Editando o modulo existente '{instance.name}' ({instance.slug})."
            )
        )

        form = prompts.build_form(instance=instance)
        if not form.is_valid():
            raise CommandError(prompts.format_form_errors(form))

        module = form.save()
        self.stdout.write(
            self.style.SUCCESS(f"Modulo {module.slug} atualizado com sucesso.")
        )
        self.stdout.write(f"- URL final: {module.get_absolute_url()}")
        self.stdout.write(f"- Permissao: {module.permission_label}")
        self.stdout.write(f"- Exibicao: {module.visibility_label}")
