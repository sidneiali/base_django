"""Geração da especificação OpenAPI e da estrutura usada na docs pública."""

from __future__ import annotations

import re
from collections import OrderedDict

from .types import DocsOperation, DocsSection

TAG_ORDER = [
    "Operacional",
    "Acesso à API",
    "Usuários do painel",
    "Grupos do painel",
    "Módulos do painel",
    "Logs de auditoria",
]


def build_public_base_url(request) -> str:
    """Retorna a URL base absoluta da instância atual sem barra final."""

    return request.build_absolute_uri("/").rstrip("/")


def _slugify_label(value: str) -> str:
    """Converte um rótulo humano em slug simples para ids HTML."""

    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "section"


def build_openapi_schema(request) -> dict[str, object]:
    """Monta a especificação OpenAPI real da API pública versionada."""

    base_url = build_public_base_url(request)

    def full_url(path: str) -> str:
        return f"{base_url}{path}"

    paths = OrderedDict(
        {
            "/api/v1/core/health/": {
                "get": {
                    "tags": ["Operacional"],
                    "summary": "Health check",
                    "description": "Retorna o status operacional da API, com informações básicas de timezone e rate limit.",
                    "operationId": "api_health",
                    "security": [],
                    "x-base-url": "/api/v1/core/health/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": f"curl {full_url('/api/v1/core/health/')}",
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/core/health/")}",\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Status operacional da API.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HealthEnvelope"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/v1/core/me/": {
                "get": {
                    "tags": ["Acesso à API"],
                    "summary": "Conta autenticada",
                    "description": "Exibe os dados básicos do usuário vinculado ao Bearer token atual.",
                    "operationId": "api_me",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/core/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/core/me/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/core/me/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Usuário autenticado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CurrentUserEnvelope"}
                                }
                            },
                        },
                        "401": {
                            "description": "Token ausente ou inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                        "403": {
                            "description": "Token sem permissão de leitura do recurso.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                }
            },
            "/api/v1/core/token/": {
                "get": {
                    "tags": ["Acesso à API"],
                    "summary": "Token atual",
                    "description": "Retorna o status do token atual e a matriz de permissões efetivas da API para a conta autenticada.",
                    "operationId": "api_token_status",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/core/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/core/token/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/core/token/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Status do token atual.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TokenStatusEnvelope"}
                                }
                            },
                        },
                        "401": {
                            "description": "Token ausente ou inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                        "403": {
                            "description": "Token sem permissão de leitura do recurso.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                }
            },
            "/api/v1/panel/users/": {
                "get": {
                    "tags": ["Usuários do painel"],
                    "summary": "Listar usuários",
                    "description": "Lista usuários comuns do painel, excluindo superusuários.",
                    "operationId": "api_users_list",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/users/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/panel/users/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/panel/users/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "search", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "username", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "email", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "is_active", "in": "query", "required": False, "schema": {"type": "boolean"}},
                        {"name": "group_id", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "ordering", "in": "query", "required": False, "schema": {"type": "string", "enum": ["username", "-username", "email", "-email", "date_joined", "-date_joined", "id", "-id"]}},
                        {"name": "page", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "page_size", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 100}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Lista de usuários.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserListEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Filtro, paginação ou ordenação inválidos.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        }
                    },
                },
                "post": {
                    "tags": ["Usuários do painel"],
                    "summary": "Criar usuário",
                    "description": "Cria um usuário comum do painel.",
                    "operationId": "api_users_create",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/users/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X POST {full_url('/api/v1/panel/users/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
                                '  -H "Content-Type: application/json" \\\n'
                                '  -d "{\\"username\\":\\"api-user\\",\\"email\\":\\"api@example.com\\",\\"password\\":\\"SenhaSegura@123\\",\\"is_active\\":true}"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "payload = {\n"
                                '    "username": "api-user",\n'
                                '    "email": "api@example.com",\n'
                                '    "password": "SenhaSegura@123",\n'
                                '    "is_active": True,\n'
                                "}\n\n"
                                "response = requests.post(\n"
                                f'    "{full_url("/api/v1/panel/users/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    json=payload,\n"
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserWriteInput"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Usuário criado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Payload inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                                }
                            },
                        },
                    },
                },
            },
            "/api/v1/panel/users/{id}/": {
                "get": {
                    "tags": ["Usuários do painel"],
                    "summary": "Detalhar usuário",
                    "description": "Retorna um usuário comum específico.",
                    "operationId": "api_users_detail",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/users/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/panel/users/1/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/panel/users/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Usuário encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserEnvelope"}
                                }
                            },
                        },
                        "404": {
                            "description": "Usuário não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "patch": {
                    "tags": ["Usuários do painel"],
                    "summary": "Atualizar usuário",
                    "description": "Atualiza campos de um usuário comum existente.",
                    "operationId": "api_users_update",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/users/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X PATCH {full_url('/api/v1/panel/users/1/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
                                '  -H "Content-Type: application/json" \\\n'
                                '  -d "{\\"email\\":\\"alterado@example.com\\"}"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "payload = {\n"
                                '    "email": "alterado@example.com",\n'
                                "}\n\n"
                                "response = requests.patch(\n"
                                f'    "{full_url("/api/v1/panel/users/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    json=payload,\n"
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserWritePartialInput"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Usuário atualizado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Payload inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "delete": {
                    "tags": ["Usuários do painel"],
                    "summary": "Excluir usuário",
                    "description": "Remove um usuário comum existente.",
                    "operationId": "api_users_delete",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/users/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X DELETE {full_url('/api/v1/panel/users/1/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.delete(\n"
                                f'    "{full_url("/api/v1/panel/users/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "204": {"description": "Usuário removido."},
                        "404": {
                            "description": "Usuário não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
            },
            "/api/v1/panel/groups/": {
                "get": {
                    "tags": ["Grupos do painel"],
                    "summary": "Listar grupos",
                    "description": "Lista grupos editáveis do painel, excluindo grupos protegidos.",
                    "operationId": "api_groups_list",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/groups/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/panel/groups/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/panel/groups/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "search", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "name", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "permission_id", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "ordering", "in": "query", "required": False, "schema": {"type": "string", "enum": ["name", "-name", "id", "-id"]}},
                        {"name": "page", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "page_size", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 100}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Lista de grupos.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelGroupListEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Filtro, paginação ou ordenação inválidos.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "post": {
                    "tags": ["Grupos do painel"],
                    "summary": "Criar grupo",
                    "description": "Cria um grupo editável do painel com permissões visíveis.",
                    "operationId": "api_groups_create",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/groups/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X POST {full_url('/api/v1/panel/groups/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
                                '  -H "Content-Type: application/json" \\\n'
                                '  -d "{\\"name\\":\\"Grupo API\\",\\"permissions\\":[1]}"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "payload = {\n"
                                '    "name": "Grupo API",\n'
                                '    "permissions": [1],\n'
                                "}\n\n"
                                "response = requests.post(\n"
                                f'    "{full_url("/api/v1/panel/groups/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    json=payload,\n"
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PanelGroupWriteInput"
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Grupo criado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelGroupEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Payload inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                                }
                            },
                        },
                    },
                },
            },
            "/api/v1/panel/groups/{id}/": {
                "get": {
                    "tags": ["Grupos do painel"],
                    "summary": "Detalhar grupo",
                    "description": "Retorna um grupo editável específico do painel.",
                    "operationId": "api_groups_detail",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/groups/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/panel/groups/1/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/panel/groups/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Grupo encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelGroupEnvelope"}
                                }
                            },
                        },
                        "404": {
                            "description": "Grupo não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "patch": {
                    "tags": ["Grupos do painel"],
                    "summary": "Atualizar grupo",
                    "description": "Atualiza um grupo editável do painel.",
                    "operationId": "api_groups_update",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/groups/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X PATCH {full_url('/api/v1/panel/groups/1/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
                                '  -H "Content-Type: application/json" \\\n'
                                '  -d "{\\"name\\":\\"Grupo API Atualizado\\",\\"permissions\\":[1]}"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "payload = {\n"
                                '    "name": "Grupo API Atualizado",\n'
                                '    "permissions": [1],\n'
                                "}\n\n"
                                "response = requests.patch(\n"
                                f'    "{full_url("/api/v1/panel/groups/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    json=payload,\n"
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PanelGroupWritePartialInput"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Grupo atualizado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelGroupEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Payload inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                                }
                            },
                        },
                        "404": {
                            "description": "Grupo não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "delete": {
                    "tags": ["Grupos do painel"],
                    "summary": "Excluir grupo",
                    "description": "Remove um grupo editável do painel.",
                    "operationId": "api_groups_delete",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/groups/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X DELETE {full_url('/api/v1/panel/groups/1/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.delete(\n"
                                f'    "{full_url("/api/v1/panel/groups/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "204": {
                            "description": "Grupo removido.",
                        },
                        "404": {
                            "description": "Grupo não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
            },
            "/api/v1/panel/modules/": {
                "get": {
                    "tags": ["Módulos do painel"],
                    "summary": "Listar módulos",
                    "description": "Lista módulos do dashboard com filtros por grupo, status e permissão.",
                    "operationId": "api_modules_list",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/modules/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/panel/modules/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/panel/modules/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "search", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "slug", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "menu_group", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "is_active", "in": "query", "required": False, "schema": {"type": "boolean"}},
                        {"name": "permission_id", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "ordering", "in": "query", "required": False, "schema": {"type": "string", "enum": ["name", "-name", "slug", "-slug", "menu_group", "-menu_group", "order", "-order", "id", "-id"]}},
                        {"name": "page", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "page_size", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 100}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Lista de módulos.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelModuleListEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Filtro, paginação ou ordenação inválidos.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "post": {
                    "tags": ["Módulos do painel"],
                    "summary": "Criar módulo",
                    "description": "Cria um módulo do dashboard com rota e permissão opcionais.",
                    "operationId": "api_modules_create",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/modules/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X POST {full_url('/api/v1/panel/modules/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
                                '  -H "Content-Type: application/json" \\\n'
                                '  -d "{\\"name\\":\\"Módulo API\\",\\"slug\\":\\"modulo-api\\",\\"url_name\\":\\"module_entry\\",\\"show_in_dashboard\\":true,\\"show_in_sidebar\\":true}"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "payload = {\n"
                                '    "name": "Módulo API",\n'
                                '    "slug": "modulo-api",\n'
                                '    "url_name": "module_entry",\n'
                                '    "show_in_dashboard": True,\n'
                                '    "show_in_sidebar": True,\n'
                                "}\n\n"
                                "response = requests.post(\n"
                                f'    "{full_url("/api/v1/panel/modules/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    json=payload,\n"
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PanelModuleWriteInput"
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Módulo criado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelModuleEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Payload inválido.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                                }
                            },
                        },
                    },
                },
            },
            "/api/v1/panel/modules/{id}/": {
                "get": {
                    "tags": ["Módulos do painel"],
                    "summary": "Detalhar módulo",
                    "description": "Retorna um módulo do dashboard com metadados operacionais.",
                    "operationId": "api_modules_detail",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/modules/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/panel/modules/1/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/panel/modules/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Módulo encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelModuleEnvelope"}
                                }
                            },
                        },
                        "404": {
                            "description": "Módulo não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "patch": {
                    "tags": ["Módulos do painel"],
                    "summary": "Atualizar módulo",
                    "description": "Atualiza um módulo do dashboard, incluindo permissão e estado de publicação.",
                    "operationId": "api_modules_update",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/modules/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X PATCH {full_url('/api/v1/panel/modules/1/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN" \\\n'
                                '  -H "Content-Type: application/json" \\\n'
                                '  -d "{\\"description\\":\\"Módulo ajustado via API\\",\\"is_active\\":false,\\"show_in_sidebar\\":false}"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "payload = {\n"
                                '    "description": "Módulo ajustado via API",\n'
                                '    "is_active": False,\n'
                                '    "show_in_sidebar": False,\n'
                                "}\n\n"
                                "response = requests.patch(\n"
                                f'    "{full_url("/api/v1/panel/modules/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    json=payload,\n"
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PanelModuleWritePartialInput"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Módulo atualizado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PanelModuleEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Payload inválido ou exclusão não permitida.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                                }
                            },
                        },
                        "404": {
                            "description": "Módulo não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
                "delete": {
                    "tags": ["Módulos do painel"],
                    "summary": "Excluir módulo",
                    "description": "Remove um módulo customizado e inativo do dashboard.",
                    "operationId": "api_modules_delete",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/panel/modules/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f"curl -X DELETE {full_url('/api/v1/panel/modules/1/')} \\\n"
                                '  -H "Authorization: Bearer SEU_TOKEN"'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.delete(\n"
                                f'    "{full_url("/api/v1/panel/modules/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "204": {"description": "Módulo removido."},
                        "400": {
                            "description": "Exclusão não permitida pelo ciclo de vida do módulo.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                        "404": {
                            "description": "Módulo não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                },
            },
            "/api/v1/core/audit-logs/": {
                "get": {
                    "tags": ["Logs de auditoria"],
                    "summary": "Listar logs de auditoria",
                    "description": "Lista eventos de auditoria com filtros opcionais e paginação simples.",
                    "operationId": "api_audit_logs_list",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/core/audit-logs/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/core/audit-logs/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/core/audit-logs/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "search", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "action", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "app_label", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "model", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "actor", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "object_id", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "path", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "date_from", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}},
                        {"name": "date_to", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}},
                        {"name": "ordering", "in": "query", "required": False, "schema": {"type": "string", "enum": ["created_at", "-created_at", "action", "-action", "actor", "-actor", "object", "-object", "id", "-id"]}},
                        {"name": "page", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "page_size", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 100}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Lista paginada de logs de auditoria.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AuditLogListEnvelope"}
                                }
                            },
                        },
                        "400": {
                            "description": "Filtro, paginação ou ordenação inválidos.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/v1/core/audit-logs/{id}/": {
                "get": {
                    "tags": ["Logs de auditoria"],
                    "summary": "Detalhar log de auditoria",
                    "description": "Retorna o payload completo de um evento individual da auditoria.",
                    "operationId": "api_audit_log_detail",
                    "security": [{"BearerAuth": []}],
                    "x-base-url": "/api/v1/core/audit-logs/",
                    "x-codeSamples": [
                        {
                            "lang": "curl",
                            "source": (
                                f'curl -H "Authorization: Bearer SEU_TOKEN" {full_url("/api/v1/core/audit-logs/1/")}'
                            ),
                        },
                        {
                            "lang": "python",
                            "source": (
                                "import requests\n\n"
                                "response = requests.get(\n"
                                f'    "{full_url("/api/v1/core/audit-logs/1/")}",\n'
                                '    headers={"Authorization": "Bearer SEU_TOKEN"},\n'
                                "    timeout=30,\n"
                                ")\n\n"
                                "print(response.status_code)\n"
                                "print(response.json())"
                            ),
                        },
                    ],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Log de auditoria encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AuditLogDetailEnvelope"}
                                }
                            },
                        },
                        "404": {
                            "description": "Log de auditoria não encontrado.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        },
                    },
                }
            },
        }
    )

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "BaseApp API",
            "version": "1.0.0",
            "description": (
                "API versionada da BaseApp para introspecção da conta, gestão de usuários "
                "grupos e módulos do painel, além da leitura dos logs de auditoria."
            ),
        },
        "servers": [
            {
                "url": base_url,
                "description": "Instância atual da aplicação",
            }
        ],
        "security": [{"BearerAuth": []}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "Token",
                }
            },
            "schemas": {
                "GroupSummary": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                    "required": ["id", "name"],
                },
                "CurrentUser": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "username": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "is_active": {"type": "boolean"},
                        "groups": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/GroupSummary"},
                        },
                    },
                    "required": ["id", "username", "first_name", "last_name", "email", "is_active", "groups"],
                },
                "ApiPermission": {
                    "type": "object",
                    "properties": {
                        "resource": {"type": "string"},
                        "label": {"type": "string"},
                        "can_create": {"type": "boolean"},
                        "can_read": {"type": "boolean"},
                        "can_update": {"type": "boolean"},
                        "can_delete": {"type": "boolean"},
                    },
                    "required": ["resource", "label", "can_create", "can_read", "can_update", "can_delete"],
                },
                "TokenStatus": {
                    "type": "object",
                    "properties": {
                        "api_enabled": {"type": "boolean"},
                        "token": {
                            "type": "object",
                            "properties": {
                                "token_prefix": {"type": "string"},
                                "issued_at": {"type": ["string", "null"], "format": "date-time"},
                                "last_used_at": {"type": ["string", "null"], "format": "date-time"},
                                "revoked_at": {"type": ["string", "null"], "format": "date-time"},
                                "is_active": {"type": "boolean"},
                            },
                            "required": ["token_prefix", "issued_at", "last_used_at", "revoked_at", "is_active"],
                        },
                        "permissions": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ApiPermission"},
                        },
                    },
                    "required": ["api_enabled", "token", "permissions"],
                },
                "HealthPayload": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "timezone": {"type": "string"},
                        "rate_limit": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "requests": {"type": "integer"},
                                "window_seconds": {"type": "integer"},
                            },
                            "required": ["enabled", "requests", "window_seconds"],
                        },
                    },
                    "required": ["status", "timestamp", "timezone", "rate_limit"],
                },
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "username": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "is_active": {"type": "boolean"},
                        "groups": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/GroupSummary"},
                        },
                    },
                    "required": ["id", "username", "first_name", "last_name", "email", "is_active", "groups"],
                },
                "UserListResponse": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "results": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"},
                        },
                    },
                    "required": ["count", "results"],
                },
                "UserWriteInput": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string"},
                        "is_active": {"type": "boolean"},
                        "groups": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["username", "email", "password"],
                },
                "UserWritePartialInput": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string"},
                        "is_active": {"type": "boolean"},
                        "groups": {"type": "array", "items": {"type": "integer"}},
                    },
                },
                "GroupPermissionSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "codename": {"type": "string"},
                        "name": {"type": "string"},
                        "app_label": {"type": "string"},
                        "model": {"type": "string"},
                    },
                    "required": ["id", "codename", "name", "app_label", "model"],
                },
                "PanelGroup": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "permissions_count": {"type": "integer"},
                        "permissions": {
                            "type": "array",
                            "items": {
                                "$ref": "#/components/schemas/GroupPermissionSummary"
                            },
                        },
                    },
                    "required": ["id", "name", "permissions_count", "permissions"],
                },
                "PanelGroupWriteInput": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "permissions": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["name"],
                },
                "PanelGroupWritePartialInput": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "permissions": {"type": "array", "items": {"type": "integer"}},
                    },
                },
                "ModulePermissionSummary": {
                    "type": ["object", "null"],
                    "properties": {
                        "id": {"type": "integer"},
                        "codename": {"type": "string"},
                        "name": {"type": "string"},
                        "app_label": {"type": "string"},
                        "model": {"type": "string"},
                    },
                },
                "PanelModule": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "slug": {"type": "string"},
                        "description": {"type": "string"},
                        "icon": {"type": "string"},
                        "url_name": {"type": "string"},
                        "menu_group": {"type": "string"},
                        "order": {"type": "integer"},
                        "is_active": {"type": "boolean"},
                        "show_in_dashboard": {"type": "boolean"},
                        "show_in_sidebar": {"type": "boolean"},
                        "uses_generic_entry": {"type": "boolean"},
                        "resolved_url": {"type": "string"},
                        "full_permission": {"type": "string"},
                        "permission_label": {"type": "string"},
                        "permission": {
                            "$ref": "#/components/schemas/ModulePermissionSummary"
                        },
                        "is_initial_module": {"type": "boolean"},
                        "can_delete": {"type": "boolean"},
                        "delete_block_reason": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "name",
                        "slug",
                        "description",
                        "icon",
                        "url_name",
                        "menu_group",
                        "order",
                        "is_active",
                        "show_in_dashboard",
                        "show_in_sidebar",
                        "uses_generic_entry",
                        "resolved_url",
                        "full_permission",
                        "permission_label",
                        "permission",
                        "is_initial_module",
                        "can_delete",
                        "delete_block_reason",
                    ],
                },
                "PanelModuleWriteInput": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "slug": {"type": "string"},
                        "description": {"type": "string"},
                        "icon": {"type": "string"},
                        "url_name": {"type": "string"},
                        "menu_group": {"type": "string"},
                        "order": {"type": "integer"},
                        "is_active": {"type": "boolean"},
                        "show_in_dashboard": {"type": "boolean"},
                        "show_in_sidebar": {"type": "boolean"},
                        "permission": {"type": ["integer", "null"]},
                    },
                    "required": ["name", "slug", "url_name"],
                },
                "PanelModuleWritePartialInput": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "slug": {"type": "string"},
                        "description": {"type": "string"},
                        "icon": {"type": "string"},
                        "url_name": {"type": "string"},
                        "menu_group": {"type": "string"},
                        "order": {"type": "integer"},
                        "is_active": {"type": "boolean"},
                        "show_in_dashboard": {"type": "boolean"},
                        "show_in_sidebar": {"type": "boolean"},
                        "permission": {"type": ["integer", "null"]},
                    },
                },
                "AuditActor": {
                    "type": ["object", "null"],
                    "properties": {"id": {"type": "integer"}, "username": {"type": "string"}},
                },
                "AuditLogSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "action": {"type": "string"},
                        "action_label": {"type": "string"},
                        "actor": {"$ref": "#/components/schemas/AuditActor"},
                        "actor_identifier": {"type": "string"},
                        "app_label": {"type": "string"},
                        "model": {"type": "string"},
                        "object_verbose_name": {"type": "string"},
                        "object_id": {"type": "string"},
                        "object_repr": {"type": "string"},
                        "path": {"type": "string"},
                        "request_method": {"type": "string"},
                        "ip_address": {"type": ["string", "null"]},
                    },
                    "required": [
                        "id",
                        "created_at",
                        "action",
                        "action_label",
                        "actor",
                        "actor_identifier",
                        "app_label",
                        "model",
                        "object_verbose_name",
                        "object_id",
                        "object_repr",
                        "path",
                        "request_method",
                        "ip_address",
                    ],
                },
                "AuditLogDetail": {
                    "allOf": [
                        {"$ref": "#/components/schemas/AuditLogSummary"},
                        {
                            "type": "object",
                            "properties": {
                                "before": {"type": "object"},
                                "after": {"type": "object"},
                                "changes": {"type": "object"},
                                "metadata": {"type": "object"},
                            },
                            "required": ["before", "after", "changes", "metadata"],
                        },
                    ]
                },
                "AuditLogListResponse": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "results": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/AuditLogSummary"},
                        },
                    },
                    "required": ["count", "page", "page_size", "results"],
                },
                "ApiMeta": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "string"},
                        "version": {"type": "string"},
                        "path": {"type": "string"},
                        "method": {"type": "string"},
                    },
                    "required": ["request_id", "version", "path", "method"],
                },
                "ApiCollectionMeta": {
                    "allOf": [
                        {"$ref": "#/components/schemas/ApiMeta"},
                        {
                            "type": "object",
                            "properties": {
                                "pagination": {
                                    "type": "object",
                                    "properties": {
                                        "page": {"type": "integer"},
                                        "page_size": {"type": "integer"},
                                        "total_items": {"type": "integer"},
                                        "total_pages": {"type": "integer"},
                                        "has_previous": {"type": "boolean"},
                                        "has_next": {"type": "boolean"},
                                        "previous_page": {"type": ["integer", "null"]},
                                        "next_page": {"type": ["integer", "null"]},
                                    },
                                    "required": [
                                        "page",
                                        "page_size",
                                        "total_items",
                                        "total_pages",
                                        "has_previous",
                                        "has_next",
                                        "previous_page",
                                        "next_page",
                                    ],
                                },
                                "ordering": {"type": "string"},
                                "filters": {"type": "object"},
                            },
                            "required": ["pagination"],
                        },
                    ]
                },
                "HealthEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/HealthPayload"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "CurrentUserEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/CurrentUser"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "TokenStatusEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/TokenStatus"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "UserEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/User"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "UserListEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"},
                        },
                        "meta": {"$ref": "#/components/schemas/ApiCollectionMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "PanelGroupEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/PanelGroup"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "PanelGroupListEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/PanelGroup"},
                        },
                        "meta": {"$ref": "#/components/schemas/ApiCollectionMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "PanelModuleEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/PanelModule"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "PanelModuleListEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/PanelModule"},
                        },
                        "meta": {"$ref": "#/components/schemas/ApiCollectionMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "AuditLogDetailEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/AuditLogDetail"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "AuditLogListEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/AuditLogSummary"},
                        },
                        "meta": {"$ref": "#/components/schemas/ApiCollectionMeta"},
                    },
                    "required": ["data", "meta"],
                },
                "ErrorPayload": {
                    "type": "object",
                    "properties": {"detail": {"type": "string"}, "code": {"type": "string"}},
                    "required": ["detail", "code"],
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"$ref": "#/components/schemas/ErrorPayload"},
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["error", "meta"],
                },
                "ValidationErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "allOf": [
                                {"$ref": "#/components/schemas/ErrorPayload"},
                                {
                                    "type": "object",
                                    "properties": {"fields": {"type": "object"}},
                                    "required": ["fields"],
                                },
                            ]
                        },
                        "meta": {"$ref": "#/components/schemas/ApiMeta"},
                    },
                    "required": ["error", "meta"],
                },
            },
        },
        "paths": paths,
    }


def build_docs_sections(schema: dict[str, object]) -> list[DocsSection]:
    """Converte a spec OpenAPI em seções simples para a documentação HTML."""

    sections_map: OrderedDict[str, DocsSection] = OrderedDict(
        (
            tag,
            {
                "id": f"section-{_slugify_label(tag)}",
                "label": tag,
                "base_url": "",
                "operations": [],
            },
        )
        for tag in TAG_ORDER
    )

    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return []

    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue

        for method, operation in methods.items():
            if not isinstance(method, str) or not isinstance(operation, dict):
                continue

            tags = operation.get("tags", [])
            if not isinstance(tags, list) or not tags or not isinstance(tags[0], str):
                continue

            tag = tags[0]
            section = sections_map.setdefault(
                tag,
                {
                    "id": f"section-{_slugify_label(tag)}",
                    "label": tag,
                    "base_url": "",
                    "operations": [],
                },
            )
            if not section["base_url"]:
                base_url = operation.get("x-base-url", path)
                section["base_url"] = base_url if isinstance(base_url, str) else path

            code_samples: dict[str, str] = {}
            raw_samples = operation.get("x-codeSamples", [])
            if isinstance(raw_samples, list):
                for sample in raw_samples:
                    if not isinstance(sample, dict):
                        continue
                    lang = sample.get("lang")
                    source = sample.get("source")
                    if isinstance(lang, str) and isinstance(source, str):
                        code_samples[lang.lower()] = source

            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str):
                operation_id = f"{method}_{path}"

            summary = operation.get("summary", "")
            if not isinstance(summary, str):
                summary = ""

            docs_operation: DocsOperation = {
                "id": operation_id.replace("_", "-"),
                "method": method.upper(),
                "path": path,
                "summary": summary,
                "code_samples": code_samples,
            }
            section["operations"].append(
                docs_operation
            )

    return [section for section in sections_map.values() if section["operations"]]
