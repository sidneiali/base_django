"""Middleware de expiracao de sessao por inatividade."""

from __future__ import annotations

from ..preferences import resolve_session_idle_timeout_minutes
from .paths import is_json_api_request


class SessionIdleTimeoutMiddleware:
    """Aplica janela de inatividade configurada para sessoes autenticadas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_json_api_request(request.path):
            timeout_minutes = resolve_session_idle_timeout_minutes(request.user)
            if timeout_minutes is not None:
                request.session.set_expiry(timeout_minutes * 60)

        return self.get_response(request)
