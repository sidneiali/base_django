"""Endpoints operacionais leves da API do app core."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .responses import api_success_response


def health(request: HttpRequest) -> HttpResponse:
    """Expõe um health check público e leve para observabilidade."""

    current_time = timezone.localtime(timezone.now())
    current_timezone = timezone.get_current_timezone_name()

    return api_success_response(
        request,
        data={
            "status": "ok",
            "timestamp": current_time.isoformat(),
            "timezone": current_timezone,
            "rate_limit": {
                "enabled": bool(getattr(settings, "API_RATE_LIMIT_ENABLED", True)),
                "requests": int(getattr(settings, "API_RATE_LIMIT_REQUESTS", 120)),
                "window_seconds": int(
                    getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)
                ),
            },
        },
    )
