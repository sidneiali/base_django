"""Helpers para respostas com suporte a navegacao parcial via HTMX."""

from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def is_htmx_request(request: HttpRequest) -> bool:
    """Indica se a requisicao atual foi disparada pelo HTMX."""

    return request.headers.get("HX-Request") == "true"


def render_page(
    request: HttpRequest,
    full_template: str,
    partial_template: str,
    context: dict[str, Any],
    *,
    status: int = 200,
) -> HttpResponse:
    """Renderiza a pagina completa ou apenas o fragmento central."""

    template_name = partial_template if is_htmx_request(request) else full_template
    return render(request, template_name, context, status=status)


def htmx_location(path: str) -> HttpResponse:
    """Instrui o HTMX a navegar para uma nova URL sem recarregar a pagina."""

    payload = {
        "path": path,
        "target": "#page-content",
        "swap": "innerHTML show:window:top",
    }
    return HttpResponse(status=204, headers={"HX-Location": json.dumps(payload)})
