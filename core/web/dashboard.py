"""Views do dashboard e entrada de módulos."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from core.htmx import render_page
from core.models import Module
from core.navigation import get_request_dashboard_modules


@login_required
def dashboard(request):
    """Renderiza o dashboard com os modulos visiveis ao usuario logado."""

    modules = get_request_dashboard_modules(request)
    return render_page(
        request,
        "dashboard.html",
        "partials/dashboard_content.html",
        {"dashboard_modules": modules},
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
