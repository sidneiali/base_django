"""Facade do catalogo canonico de modulos do sistema."""

from __future__ import annotations

from core.canonical_modules import INITIAL_MODULES, ModuleSeedDefinition

INITIAL_MODULE_SLUGS = frozenset(definition.slug for definition in INITIAL_MODULES)


def is_initial_module_slug(slug: str) -> bool:
    """Indica se o slug informado pertence ao catálogo canônico inicial."""

    return slug in INITIAL_MODULE_SLUGS


__all__ = [
    "INITIAL_MODULES",
    "INITIAL_MODULE_SLUGS",
    "ModuleSeedDefinition",
    "is_initial_module_slug",
]
