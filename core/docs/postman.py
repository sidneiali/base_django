"""Builders da coleção Postman pública da API."""

from __future__ import annotations

import json
from typing import Any

from django.urls import reverse

from core.api.openapi import build_public_base_url

POSTMAN_COLLECTION_SCHEMA = (
    "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
)


def build_postman_collection(request) -> dict[str, object]:
    """Monta a coleção Postman pública dos recursos disponíveis da API."""

    base_url = build_public_base_url(request)
    urls = _build_postman_urls(base_url)

    return {
        "info": {
            "name": "BaseApp API",
            "description": (
                "Coleção pública da API protegida por Bearer token para usuários, "
                "grupos, módulos do painel e logs de auditoria."
            ),
            "schema": POSTMAN_COLLECTION_SCHEMA,
        },
        "variable": [
            {"key": "base_url", "value": base_url},
            {"key": "token", "value": "SEU_TOKEN"},
            {"key": "user_id", "value": "1"},
            {"key": "group_id", "value": "1"},
            {"key": "module_id", "value": "1"},
            {"key": "audit_log_id", "value": "1"},
        ],
        "item": [
            {
                "name": "Operacional",
                "item": [
                    {
                        "name": "Health check",
                        "request": {"method": "GET", "url": urls["health"]},
                    }
                ],
            },
            {
                "name": "Acesso à API",
                "item": [
                    _build_request_item(
                        "Minha conta",
                        method="GET",
                        url=urls["me"],
                    ),
                    _build_request_item(
                        "Token atual",
                        method="GET",
                        url=urls["token"],
                    ),
                ],
            },
            {
                "name": "Usuários do painel",
                "item": [
                    _build_request_item(
                        "Listar usuários",
                        method="GET",
                        url=urls["users_collection"],
                    ),
                    _build_request_item(
                        "Criar usuário",
                        method="POST",
                        url=urls["users_collection"],
                        body_payload={
                            "username": "api-user",
                            "email": "api@example.com",
                            "password": "SenhaSegura@123",
                            "is_active": True,
                        },
                    ),
                    _build_request_item(
                        "Detalhar usuário",
                        method="GET",
                        url=urls["user_detail_template"],
                    ),
                    _build_request_item(
                        "Atualizar usuário",
                        method="PATCH",
                        url=urls["user_detail"],
                        body_payload={"email": "alterado@example.com"},
                    ),
                    _build_request_item(
                        "Excluir usuário",
                        method="DELETE",
                        url=urls["user_detail"],
                    ),
                ],
            },
            {
                "name": "Grupos do painel",
                "item": [
                    _build_request_item(
                        "Listar grupos",
                        method="GET",
                        url=urls["groups_collection"],
                    ),
                    _build_request_item(
                        "Criar grupo",
                        method="POST",
                        url=urls["groups_collection"],
                        body_payload={"name": "Grupo API", "permissions": [1]},
                    ),
                    _build_request_item(
                        "Detalhar grupo",
                        method="GET",
                        url=urls["group_detail_template"],
                    ),
                    _build_request_item(
                        "Atualizar grupo",
                        method="PATCH",
                        url=urls["group_detail"],
                        body_payload={
                            "name": "Grupo API Atualizado",
                            "permissions": [1],
                        },
                    ),
                    _build_request_item(
                        "Excluir grupo",
                        method="DELETE",
                        url=urls["group_detail"],
                    ),
                ],
            },
            {
                "name": "Módulos do painel",
                "item": [
                    _build_request_item(
                        "Listar módulos",
                        method="GET",
                        url=urls["modules_collection"],
                    ),
                    _build_request_item(
                        "Criar módulo",
                        method="POST",
                        url=urls["modules_collection"],
                        body_payload={
                            "name": "Módulo API",
                            "slug": "modulo-api",
                            "description": "Módulo criado pela API",
                            "icon": "ti ti-layout-grid",
                            "url_name": "module_entry",
                            "menu_group": "Integrações",
                            "order": 50,
                            "is_active": True,
                            "show_in_dashboard": True,
                            "show_in_sidebar": True,
                        },
                    ),
                    _build_request_item(
                        "Detalhar módulo",
                        method="GET",
                        url=urls["module_detail_template"],
                    ),
                    _build_request_item(
                        "Atualizar módulo",
                        method="PATCH",
                        url=urls["module_detail"],
                        body_payload={
                            "name": "Módulo API Atualizado",
                            "description": "Módulo ajustado via API",
                            "is_active": False,
                            "show_in_sidebar": False,
                        },
                    ),
                    _build_request_item(
                        "Excluir módulo",
                        method="DELETE",
                        url=urls["module_detail"],
                    ),
                ],
            },
            {
                "name": "Logs de auditoria",
                "item": [
                    _build_request_item(
                        "Listar logs de auditoria",
                        method="GET",
                        url=urls["audit_logs_collection"],
                    ),
                    _build_request_item(
                        "Detalhar log de auditoria",
                        method="GET",
                        url=urls["audit_log_detail"],
                    ),
                ],
            },
        ],
    }


def _build_postman_urls(base_url: str) -> dict[str, str]:
    """Concentra as URLs usadas pela coleção pública do Postman."""

    user_detail_template = f"{base_url}/api/v1/panel/users/:id/"
    group_detail_template = f"{base_url}/api/v1/panel/groups/:id/"
    module_detail_template = f"{base_url}/api/v1/panel/modules/:id/"
    audit_log_detail_template = f"{base_url}/api/v1/core/audit-logs/:id/"

    return {
        "health": f"{base_url}{reverse('api_v1_core_health')}",
        "me": f"{base_url}{reverse('api_v1_core_me')}",
        "token": f"{base_url}{reverse('api_v1_core_token')}",
        "users_collection": f"{base_url}{reverse('api_v1_panel_users_collection')}",
        "user_detail_template": user_detail_template,
        "user_detail": user_detail_template.replace(":id", "{{user_id}}"),
        "groups_collection": f"{base_url}{reverse('api_v1_panel_groups_collection')}",
        "group_detail_template": group_detail_template,
        "group_detail": group_detail_template.replace(":id", "{{group_id}}"),
        "modules_collection": f"{base_url}{reverse('api_v1_panel_modules_collection')}",
        "module_detail_template": module_detail_template,
        "module_detail": module_detail_template.replace(":id", "{{module_id}}"),
        "audit_logs_collection": (
            f"{base_url}{reverse('api_v1_core_audit_logs_collection')}"
        ),
        "audit_log_detail": audit_log_detail_template.replace(
            ":id", "{{audit_log_id}}"
        ),
    }


def _build_request_item(
    name: str,
    *,
    method: str,
    url: str,
    body_payload: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Materializa um item simples da coleção Postman."""

    request: dict[str, object] = {
        "method": method,
        "header": _build_request_headers(include_json=body_payload is not None),
        "url": url,
    }
    if body_payload is not None:
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body_payload, ensure_ascii=False, indent=2),
        }

    return {
        "name": name,
        "request": request,
    }


def _build_request_headers(*, include_json: bool) -> list[dict[str, str]]:
    """Retorna os headers padrão usados pelos requests autenticados."""

    headers = [
        {
            "key": "Authorization",
            "value": "Bearer {{token}}",
            "type": "text",
        }
    ]
    if include_json:
        headers.append(
            {
                "key": "Content-Type",
                "value": "application/json",
                "type": "text",
            }
        )
    return headers
