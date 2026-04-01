"""Middleware responsável por gerar o X-Request-ID da aplicação."""

from __future__ import annotations

import uuid


def build_request_id(request) -> str:
    """Gera um identificador seguro para rastrear a requisição atual."""

    incoming = str(request.META.get("HTTP_X_REQUEST_ID", "")).strip()
    if incoming and len(incoming) <= 128:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:.")
        if all(char in allowed for char in incoming):
            return incoming

    return str(uuid.uuid4())


class RequestIdMiddleware:
    """Anexa um X-Request-ID estável às respostas da aplicação."""

    def __init__(self, get_response):
        """Armazena o próximo callable da cadeia de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Gera ou reaproveita o request id e o devolve no response header."""

        request.request_id = build_request_id(request)
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
