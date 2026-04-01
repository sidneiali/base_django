"""Seed idempotente para os modulos iniciais do dashboard."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Module
from core.module_catalog import INITIAL_MODULES


class Command(BaseCommand):
    """Cria ou atualiza o conjunto minimo de modulos do sistema."""

    help = "Cria ou atualiza os modulos iniciais do dashboard."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        created_count = 0
        updated_count = 0

        for definition in INITIAL_MODULES:
            module, created = Module.objects.update_or_create(
                slug=definition.slug,
                defaults=definition.defaults(),
            )

            if created:
                created_count += 1
                action = "criado"
            else:
                updated_count += 1
                action = "atualizado"

            self.stdout.write(f"Modulo {module.slug} {action}.")

        self.stdout.write(
            self.style.SUCCESS(
                "Seed concluido: "
                f"{created_count} criado(s), {updated_count} atualizado(s).",
            ),
        )
