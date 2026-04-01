"""Middlewares de autenticacao complementar, limite de taxa e auditoria."""

from __future__ import annotations

import time
import uuid

from django.conf import settings
from django.core.cache import cache

from .api_auth import api_error_response, authenticate_api_request
from .audit import create_audit_log, reset_audit_context, set_audit_context
from .models import AuditLog


def _is_json_api_request(path: str) -> bool:
    """Indica se a rota pertence aos endpoints JSON protegidos/operacionais."""

    if path.startswith("/api/docs/"):
        return False
    if path in {
        "/api/docs/",
        "/api/docs/postman.json",
        "/api/openapi.json",
        "/api/v1/openapi.json",
    }:
        return False
    return (
        path.startswith("/api/core/")
        or path.startswith("/api/panel/")
        or path.startswith("/api/v1/core/")
        or path.startswith("/api/v1/panel/")
    )


def _is_rate_limited_path(path: str) -> bool:
    """Define quais rotas JSON entram no controle de rate limit."""

    if not _is_json_api_request(path):
        return False
    return path not in {"/api/core/health/", "/api/v1/core/health/"}


def _build_request_id(request) -> str:
    """Gera um identificador seguro para rastrear a requisição atual."""

    incoming = str(request.META.get("HTTP_X_REQUEST_ID", "")).strip()
    if incoming and len(incoming) <= 128:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:.")
        if all(char in allowed for char in incoming):
            return incoming

    return str(uuid.uuid4())


def _build_rate_limit_identifier(request) -> str:
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


def _consume_rate_limit_slot(identifier: str) -> tuple[int, int]:
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


def _set_rate_limit_headers(response, *, limit: int, remaining: int, window_seconds: int):
    """Anexa headers úteis de rate limit à resposta JSON da API."""

    response["X-RateLimit-Limit"] = str(limit)
    response["X-RateLimit-Remaining"] = str(max(0, remaining))
    response["X-RateLimit-Window"] = str(window_seconds)
    return response


class ApiTokenAuthenticationMiddleware:
    """Autentica chamadas Bearer da API antes da auditoria montar o contexto."""

    def __init__(self, get_response):
        """Armazena o próximo callable da stack de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Resolve o token Bearer em ``request.user`` para rotas JSON da API."""

        request.api_token = None
        request.api_auth_result = None

        if _is_json_api_request(request.path):
            auth_result = authenticate_api_request(request)
            request.api_auth_result = auth_result
            request.api_token = auth_result.token

            if auth_result.is_authenticated:
                request.user = auth_result.user
                request._cached_user = auth_result.user

        return self.get_response(request)


class AuditContextMiddleware:
    """Mantem usuario, rota e IP acessiveis durante o ciclo da requisicao."""

    def __init__(self, get_response):
        """Armazena o callable seguinte da stack de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Publica o contexto atual e o limpa ao final da resposta."""

        token = set_audit_context(request)
        try:
            return self.get_response(request)
        finally:
            reset_audit_context(token)


class RequestIdMiddleware:
    """Anexa um X-Request-ID estável às respostas da aplicação."""

    def __init__(self, get_response):
        """Armazena o próximo callable da cadeia de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Gera ou reaproveita o request id e o devolve no response header."""

        request.request_id = _build_request_id(request)
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class ApiRateLimitMiddleware:
    """Aplica rate limit simples por token/IP nas rotas JSON da API."""

    def __init__(self, get_response):
        """Armazena o próximo callable da cadeia de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Conta o uso da API e bloqueia excesso com resposta JSON 429."""

        if not _is_rate_limited_path(request.path):
            return self.get_response(request)

        if not getattr(settings, "API_RATE_LIMIT_ENABLED", True):
            return self.get_response(request)

        limit = max(1, int(getattr(settings, "API_RATE_LIMIT_REQUESTS", 120)))
        window_seconds = max(1, int(getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)))
        identifier = _build_rate_limit_identifier(request)
        count, remaining = _consume_rate_limit_slot(identifier)

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
            )
            response["Retry-After"] = str(window_seconds)
            return _set_rate_limit_headers(
                response,
                limit=limit,
                remaining=0,
                window_seconds=window_seconds,
            )

        response = self.get_response(request)
        return _set_rate_limit_headers(
            response,
            limit=limit,
            remaining=remaining,
            window_seconds=window_seconds,
        )
