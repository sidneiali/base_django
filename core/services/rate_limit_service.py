"""Serviços puros para consumo de buckets de rate limit da API."""

from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Representa a janela vigente do rate limit da API."""

    limit: int
    window_seconds: int


def get_rate_limit_config() -> RateLimitConfig:
    """Normaliza os limites da API a partir dos settings atuais."""

    return RateLimitConfig(
        limit=max(1, int(getattr(settings, "API_RATE_LIMIT_REQUESTS", 120))),
        window_seconds=max(
            1,
            int(getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)),
        ),
    )


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


def consume_rate_limit_slot(
    identifier: str,
    *,
    config: RateLimitConfig | None = None,
) -> tuple[int, int]:
    """Consome um slot do bucket atual e devolve contador e restante."""

    active_config = config or get_rate_limit_config()
    current_window = int(time.time() // active_config.window_seconds)
    cache_key = f"api-rate:{current_window}:{identifier}"
    timeout = active_config.window_seconds + 2

    if cache.add(cache_key, 1, timeout=timeout):
        count = 1
    else:
        try:
            count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=timeout)
            count = 1

    remaining = max(0, active_config.limit - count)
    return count, remaining
