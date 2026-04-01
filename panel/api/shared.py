"""Helpers compartilhados entre recursos JSON do app panel."""

from __future__ import annotations

import json
from json import JSONDecodeError

from core.api.responses import api_error_response
from django import forms
from django.http import HttpRequest, JsonResponse


def parse_json_body(
    request: HttpRequest,
) -> tuple[dict[str, object], JsonResponse | None]:
    """Converte o corpo JSON da requisição em dicionário Python."""

    if not request.body:
        return {}, None

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError):
        return {}, api_error_response(
            "O corpo da requisição deve ser um JSON válido.",
            code="invalid_json",
            status=400,
            request=request,
        )

    if not isinstance(payload, dict):
        return {}, api_error_response(
            "O corpo JSON deve ser um objeto com pares chave/valor.",
            code="invalid_payload",
            status=400,
            request=request,
        )

    return payload, None


def json_form_errors(request: HttpRequest, form: forms.BaseForm) -> JsonResponse:
    """Retorna erros de validação do formulário em formato JSON padronizado."""

    return api_error_response(
        "Os dados enviados são inválidos.",
        code="validation_error",
        status=400,
        request=request,
        fields=form.errors.get_json_data(),
    )
