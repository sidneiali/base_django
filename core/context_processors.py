"""Context processors compartilhados pelo app core."""

from .services import build_modules_for_user


def sidebar_modules(request):
    """
    Injeta a chave ``modules`` em todos os templates.

    O sidebar reutiliza a mesma estrutura agrupada do dashboard para que
    a navegacao lateral reflita os modulos liberados ao usuario logado.
    """
    if not request.user.is_authenticated:
        return {"modules": {}}

    return {"modules": build_modules_for_user(request.user)}
