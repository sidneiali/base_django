"""Servicos de apoio para montagem de dados do dashboard."""

from collections import defaultdict

from .models import Module


def build_modules_for_user(user):
    """Agrupa os modulos ativos e calcula acesso para um usuario.

    O retorno e um dicionario indexado por ``menu_group`` com os dados
    necessarios para renderizar cards e links do dashboard.
    """

    modules = Module.objects.filter(is_active=True)
    grouped = defaultdict(list)

    for module in modules:
        has_access = (
            user.is_superuser
            or not module.full_permission
            or user.has_perm(module.full_permission)
        )

        grouped[module.menu_group].append(
            {
                "name": module.name,
                "slug": module.slug,
                "description": module.description,
                "icon": module.icon or "ti ti-layout-grid",
                "url": module.get_absolute_url(),
                "has_access": has_access,
            }
        )

    return dict(grouped)
