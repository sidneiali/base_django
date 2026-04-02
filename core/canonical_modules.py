"""Definicoes canonicas dos modulos iniciais do sistema."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from core.initial_modules import INITIAL_MODULES as BASE_INITIAL_MODULES
from core.modules import MODULES, ModuleDefinition


@dataclass(frozen=True, slots=True)
class ModuleSeedDefinition:
    """Define os campos persistidos para um modulo inicial."""

    name: str
    slug: str
    description: str
    icon: str
    url_name: str
    app_label: str
    permission_codename: str
    menu_group: str
    order: int
    is_active: bool = True
    show_in_sidebar: bool = True
    show_in_dashboard: bool = True

    def defaults(self) -> dict[str, object]:
        """Retorna os campos usados no ``update_or_create`` do seed."""

        data = asdict(self)
        data.pop("slug")
        return data

def _build_canonical_module_map() -> dict[str, ModuleDefinition]:
    """Monta o mapa canonico final a partir dos modulos iniciais e extras."""

    duplicate_slugs = BASE_INITIAL_MODULES.keys() & MODULES.keys()
    if duplicate_slugs:
        duplicated = ", ".join(sorted(duplicate_slugs))
        raise ValueError(
            "Slugs canonicos duplicados entre initial_modules e modules: "
            f"{duplicated}"
        )

    return {
        **BASE_INITIAL_MODULES,
        **MODULES,
    }


CANONICAL_MODULES = _build_canonical_module_map()


INITIAL_MODULES: tuple[ModuleSeedDefinition, ...] = tuple(
    ModuleSeedDefinition(slug=slug, **module_definition)
    for slug, module_definition in CANONICAL_MODULES.items()
)
