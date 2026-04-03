"""Views públicas da documentação da API."""

import json

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from core.api.openapi import (
    build_docs_sections,
    build_openapi_schema,
    build_public_base_url,
)

from .postman import build_postman_collection


def api_docs(request):
    """Exibe a pagina publica de documentação/testes da API."""

    openapi_schema = build_openapi_schema(request)

    return render(
        request,
        "account/api_docs.html",
        {
            "page_title": "Swagger da API",
            "api_base_url": build_public_base_url(request),
            "docs_sections": build_docs_sections(openapi_schema),
            "openapi_download_url": reverse("api_v1_openapi"),
            "postman_download_url": reverse("api_docs_postman"),
        },
    )


def api_openapi(request):
    """Entrega a especificação OpenAPI pública da API versionada."""

    schema = build_openapi_schema(request)
    return HttpResponse(
        json.dumps(schema, ensure_ascii=False, indent=2),
        content_type="application/json",
    )


def api_docs_postman(request):
    """Entrega a coleção Postman pública da API para download."""

    collection = build_postman_collection(request)
    response = HttpResponse(
        json.dumps(collection, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = (
        'attachment; filename="baseapp-api-postman-collection.json"'
    )
    return response
