"""Middleware de rate limit simples para os endpoints JSON da API."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache

from ..api.auth import api_error_response
from ..audit import create_audit_log
from ..models import AuditLog
from .paths import is_rate_limited_path


def build_rate_limit_identifier(request) -> str:
    """Escolhe um identificador estável para o bucket do limite da API."""

    auth_result = getattr(request, "api_auth_result", None)
    if auth_result is not None and auth_result.is_authenticated and auth_result.token is not None:
        return f"token:{auth_result.token.pk}"

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
        if ip_address:
            return f"ip:{ip_address}"

    remote_addr = request.META.get("REMOTE_ADDR", "").strip()
    if remote_addr:
        return f"ip:{remote_addr}"

    return "ip:unknown"


def consume_rate_limit_slot(identifier: str) -> tuple[int, int]:
    """Consome um slot do bucket atual e devolve contador e restante."""

    limit = max(1, int(getattr(settings, "API_RATE_LIMIT_REQUESTS", 120)))
    window_seconds = max(1, int(getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)))
    current_window = int(time.time() // window_seconds)
    cache_key = f"api-rate:{current_window}:{identifier}"
    timeout = window_seconds + 2

    if cache.add(cache_key, 1, timeout=timeout):
        count = 1
    else:
        try:
            count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=timeout)
            count = 1

    remaining = max(0, limit - count)
    return count, remaining


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

        limit = max(1, int(getattr(settings, "API_RATE_LIMIT_REQUESTS", 120)))
        window_seconds = max(1, int(getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)))
        identifier = build_rate_limit_identifier(request)
        count, remaining = consume_rate_limit_slot(identifier)

        if count > limit:
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
                    "limit": limit,
                    "window_seconds": window_seconds,
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
            response["Retry-After"] = str(window_seconds)
            return set_rate_limit_headers(
                response,
                limit=limit,
                remaining=0,
                window_seconds=window_seconds,
            )

        response = self.get_response(request)
        return set_rate_limit_headers(
            response,
            limit=limit,
            remaining=remaining,
            window_seconds=window_seconds,
        )
