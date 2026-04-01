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


def _build_postman_collection(request) -> dict[str, object]:
    """Monta a coleção Postman pública dos recursos disponíveis da API."""

    base_url = build_public_base_url(request)
    health_url = f"{base_url}{reverse('api_v1_core_health')}"
    me_url = f"{base_url}{reverse('api_v1_core_me')}"
    token_url = f"{base_url}{reverse('api_v1_core_token')}"
    users_collection_url = f"{base_url}{reverse('api_v1_panel_users_collection')}"
    user_detail_url = f"{base_url}/api/v1/panel/users/:id/"
    groups_collection_url = f"{base_url}{reverse('api_v1_panel_groups_collection')}"
    group_detail_url = f"{base_url}/api/v1/panel/groups/:id/"
    audit_logs_collection_url = f"{base_url}{reverse('api_v1_core_audit_logs_collection')}"
    audit_log_detail_url = f"{base_url}/api/v1/core/audit-logs/:id/"

    return {
        "info": {
            "name": "BaseApp API",
            "description": (
                "Coleção pública da API protegida por Bearer token para usuários, "
                "grupos do painel e logs de auditoria."
            ),
            "schema": (
                "https://schema.getpostman.com/json/collection/v2.1.0/"
                "collection.json"
            ),
        },
        "variable": [
            {"key": "base_url", "value": base_url},
            {"key": "token", "value": "SEU_TOKEN"},
            {"key": "user_id", "value": "1"},
            {"key": "group_id", "value": "1"},
            {"key": "audit_log_id", "value": "1"},
        ],
        "item": [
            {
                "name": "Operacional",
                "item": [{"name": "Health check", "request": {"method": "GET", "url": health_url}}],
            },
            {
                "name": "Acesso à API",
                "item": [
                    {
                        "name": "Minha conta",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": me_url,
                        },
                    },
                    {
                        "name": "Token atual",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": token_url,
                        },
                    },
                ],
            },
            {
                "name": "Usuários do painel",
                "item": [
                    {
                        "name": "Listar usuários",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": users_collection_url,
                        },
                    },
                    {
                        "name": "Criar usuário",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"},
                                {"key": "Content-Type", "value": "application/json", "type": "text"},
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "username": "api-user",
                                        "email": "api@example.com",
                                        "password": "SenhaSegura@123",
                                        "is_active": True,
                                    },
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                            },
                            "url": users_collection_url,
                        },
                    },
                    {
                        "name": "Detalhar usuário",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": user_detail_url,
                        },
                    },
                    {
                        "name": "Atualizar usuário",
                        "request": {
                            "method": "PATCH",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"},
                                {"key": "Content-Type", "value": "application/json", "type": "text"},
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps({"email": "alterado@example.com"}, ensure_ascii=False, indent=2),
                            },
                            "url": user_detail_url.replace(":id", "{{user_id}}"),
                        },
                    },
                    {
                        "name": "Excluir usuário",
                        "request": {
                            "method": "DELETE",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": user_detail_url.replace(":id", "{{user_id}}"),
                        },
                    },
                ],
            },
            {
                "name": "Grupos do painel",
                "item": [
                    {
                        "name": "Listar grupos",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": groups_collection_url,
                        },
                    },
                    {
                        "name": "Criar grupo",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"},
                                {"key": "Content-Type", "value": "application/json", "type": "text"},
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "name": "Grupo API",
                                        "permissions": [1],
                                    },
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                            },
                            "url": groups_collection_url,
                        },
                    },
                    {
                        "name": "Detalhar grupo",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": group_detail_url,
                        },
                    },
                    {
                        "name": "Atualizar grupo",
                        "request": {
                            "method": "PATCH",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"},
                                {"key": "Content-Type", "value": "application/json", "type": "text"},
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {"name": "Grupo API Atualizado", "permissions": [1]},
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                            },
                            "url": group_detail_url.replace(":id", "{{group_id}}"),
                        },
                    },
                    {
                        "name": "Excluir grupo",
                        "request": {
                            "method": "DELETE",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": group_detail_url.replace(":id", "{{group_id}}"),
                        },
                    },
                ],
            },
            {
                "name": "Logs de auditoria",
                "item": [
                    {
                        "name": "Listar logs de auditoria",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": audit_logs_collection_url,
                        },
                    },
                    {
                        "name": "Detalhar log de auditoria",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}],
                            "url": audit_log_detail_url.replace(":id", "{{audit_log_id}}"),
                        },
                    },
                ],
            },
        ],
    }


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

    collection = _build_postman_collection(request)
    response = HttpResponse(
        json.dumps(collection, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = (
        'attachment; filename="baseapp-api-postman-collection.json"'
    )
    return response
