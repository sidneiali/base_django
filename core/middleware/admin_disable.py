"""Middleware para desativacao opcional da superficie /admin/."""

from __future__ import annotations

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse


class AdminRouteDisableMiddleware:
    """Responde 404 para qualquer rota do admin quando a flag estiver desligada."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not getattr(settings, "ENABLE_DJANGO_ADMIN", True) and self._is_admin_path(
            request
        ):
            raise Http404("Admin desativado.")

        return self.get_response(request)

    @staticmethod
    def _is_admin_path(request: HttpRequest) -> bool:
        """Retorna se o path atual pertence a superficie do Django admin."""

        path = request.path_info.rstrip("/")
        return path == "/admin" or path.startswith("/admin/")
