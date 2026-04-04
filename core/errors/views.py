"""Views de erro usadas pelo projeto."""

from core.htmx import render_page


def not_found_view(request, exception=None):
    """Renderiza a pagina padrao de recurso inexistente."""

    return render_page(
        request,
        "not_found.html",
        "partials/not_found_content.html",
        {},
        status=404,
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


def server_error_view(request):
    """Renderiza a pagina padrao de erro interno da aplicacao."""

    return render_page(
        request,
        "server_error.html",
        "partials/server_error_content.html",
        {},
        status=500,
    )
