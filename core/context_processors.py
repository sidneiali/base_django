"""Context processors compartilhados pelo app core."""

from .navigation import get_request_modules, get_request_topbar_shortcuts
from .preferences import get_user_interface_preference_values


def sidebar_modules(request):
    """
    Injeta a chave ``modules`` em todos os templates.

    O sidebar reutiliza a mesma estrutura agrupada do dashboard para que
    a navegacao lateral reflita os modulos liberados ao usuario logado.
    """
    return {
        "modules": get_request_modules(request),
        "topbar_shortcuts": get_request_topbar_shortcuts(request),
    }


def user_interface_preferences(request):
    """Injeta preferencias globais do shell para o usuario autenticado."""

    return get_user_interface_preference_values(request.user)
