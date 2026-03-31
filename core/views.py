"""Views principais do dashboard e das entradas de modulo."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .htmx import render_page
from .models import Module
from .services import build_modules_for_user


@login_required
def dashboard(request):
    """Renderiza o dashboard com os modulos visiveis ao usuario logado."""

    modules = build_modules_for_user(request.user)
    return render_page(
        request,
        "dashboard.html",
        "partials/dashboard_content.html",
        {"modules": modules},
    )


@login_required
def module_entry(request, slug: str):
    """Abre a pagina de entrada de um modulo ativo e valida permissao."""

    module = get_object_or_404(Module, slug=slug, is_active=True)

    if module.full_permission:
        if not (
            request.user.is_superuser
            or request.user.has_perm(module.full_permission)
        ):
            raise PermissionDenied

    return render_page(
        request,
        "module_page.html",
        "partials/module_page_content.html",
        {"module": module},
    )


def forbidden_view(request, exception=None):
    """Renderiza a pagina padrao de acesso negado do projeto."""

    return render_page(
        request,
        "forbidden.html",
        "partials/forbidden_content.html",
        {},
        status=403,
    )
