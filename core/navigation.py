"""Montagem da navegação autenticada do shell principal."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast

from django.http import HttpRequest

from .models import Module


@dataclass(frozen=True, slots=True)
class ModuleNavigationItem:
    """Representa um módulo renderizável no dashboard e no sidebar."""

    name: str
    slug: str
    description: str
    icon: str
    url: str
    has_access: bool


ModuleNavigationGroups = dict[str, list[ModuleNavigationItem]]


def _module_has_access(module: Module, user: Any) -> bool:
    """Resolve se o usuário atual pode acessar o módulo informado."""

    return bool(
        user.is_superuser
        or not module.full_permission
        or user.has_perm(module.full_permission)
    )


def build_modules_for_user(user: Any) -> ModuleNavigationGroups:
    """Agrupa os módulos ativos e calcula acesso para um usuário."""

    modules = Module.objects.filter(is_active=True)
    grouped: ModuleNavigationGroups = defaultdict(list)

    for module in modules:
        grouped[module.menu_group].append(
            ModuleNavigationItem(
                name=module.name,
                slug=module.slug,
                description=module.description,
                icon=module.icon or "ti ti-layout-grid",
                url=module.get_absolute_url(),
                has_access=_module_has_access(module, user),
            )
        )

    return dict(grouped)


def get_request_modules(request: HttpRequest) -> ModuleNavigationGroups:
    """Retorna os módulos da navegação com cache por request."""

    if not request.user.is_authenticated:
        return {}

    cached_modules = cast(
        ModuleNavigationGroups | None,
        getattr(request, "_cached_navigation_modules", None),
    )
    if cached_modules is not None:
        return cached_modules

    modules = build_modules_for_user(request.user)
    setattr(request, "_cached_navigation_modules", modules)
    return modules
