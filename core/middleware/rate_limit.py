"""Middleware de rate limit simples para os endpoints JSON da API."""

from __future__ import annotations

from django.conf import settings

from ..api.auth import api_error_response
from ..audit import create_audit_log
from ..models import AuditLog
from ..services.rate_limit_service import (
    build_rate_limit_identifier,
    consume_rate_limit_slot,
    get_rate_limit_config,
)
from .paths import is_rate_limited_path


def set_rate_limit_headers(response, *, limit: int, remaining: int, window_seconds: int):
    """Anexa headers úteis de rate limit à resposta JSON da API."""

    response["X-RateLimit-Limit"] = str(limit)
    response["X-RateLimit-Remaining"] = str(max(0, remaining))
    response["X-RateLimit-Window"] = str(window_seconds)
    return response


class ApiRateLimitMiddleware:
    """Aplica rate limit simples por token/IP nas rotas JSON da API."""

    def __init__(self, get_response):
        """Armazena o próximo callable da cadeia de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Conta o uso da API e bloqueia excesso com resposta JSON 429."""

        if not is_rate_limited_path(request.path):
            return self.get_response(request)

        if not getattr(settings, "API_RATE_LIMIT_ENABLED", True):
            return self.get_response(request)

        config = get_rate_limit_config()
        identifier = build_rate_limit_identifier(request)
        count, remaining = consume_rate_limit_slot(identifier, config=config)

        if count > config.limit:
            auth_result = getattr(request, "api_auth_result", None)
            actor = auth_result.user if auth_result and auth_result.is_authenticated else None
            actor_identifier = actor.get_username() if actor is not None else ""
            create_audit_log(
                AuditLog.ACTION_RATE_LIMITED,
                actor=actor,
                actor_identifier=actor_identifier,
                metadata={
                    "event": "api_rate_limited",
                    "identifier": identifier,
                    "limit": config.limit,
                    "window_seconds": config.window_seconds,
                    "path": request.path,
                },
                object_repr=request.path,
            )
            response = api_error_response(
                "Limite de requisições da API excedido. Tente novamente em instantes.",
                code="rate_limited",
                status=429,
                request=request,
            )
            response["Retry-After"] = str(config.window_seconds)
            return set_rate_limit_headers(
                response,
                limit=config.limit,
                remaining=0,
                window_seconds=config.window_seconds,
            )

        response = self.get_response(request)
        return set_rate_limit_headers(
            response,
            limit=config.limit,
            remaining=remaining,
            window_seconds=config.window_seconds,
        )
