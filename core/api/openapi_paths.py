"""Builders dos paths OpenAPI da API publica."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, cast

BASE_URL_PLACEHOLDER = "__BASE_URL__"

OPERACIONAL_PATHS_TEMPLATE: dict[str, Any] = {
    "/api/v1/core/health/": {
        "get": {
            "tags": ["Operacional"],
            "summary": "Health check",
            "description": "Retorna o status operacional da API, com "
            "informações básicas de timezone e rate limit.",
            "operationId": "api_health",
            "security": [],
            "x-base-url": "/api/v1/core/health/",
            "x-codeSamples": [
                {"lang": "curl", "source": "curl __BASE_URL__/api/v1/core/health/"},
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/core/health/",\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
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
    }
}

ACCESS_PATHS_TEMPLATE: dict[str, Any] = {
    "/api/v1/core/me/": {
        "get": {
            "tags": ["Acesso à API"],
            "summary": "Conta autenticada",
            "description": "Exibe os dados básicos do usuário vinculado ao "
            "Bearer token atual.",
            "operationId": "api_me",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/core/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": 'curl -H "Authorization: Bearer '
                    'SEU_TOKEN" '
                    "__BASE_URL__/api/v1/core/me/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    '    "__BASE_URL__/api/v1/core/me/",\n'
                    '    headers={"Authorization": "Bearer '
                    'SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "responses": {
                "200": {
                    "description": "Usuário autenticado.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CurrentUserEnvelope"
                            }
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
            "description": "Retorna o status do token atual e a matriz de "
            "permissões efetivas da API para a conta "
            "autenticada.",
            "operationId": "api_token_status",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/core/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": 'curl -H "Authorization: Bearer '
                    'SEU_TOKEN" '
                    "__BASE_URL__/api/v1/core/token/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/core/token/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "responses": {
                "200": {
                    "description": "Status do token atual.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/TokenStatusEnvelope"
                            }
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
}

USERS_PATHS_TEMPLATE: dict[str, Any] = {
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
                    "source": 'curl -H "Authorization: Bearer '
                    'SEU_TOKEN" '
                    "__BASE_URL__/api/v1/panel/users/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/users/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "search",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "username",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "email",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "is_active",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "boolean"},
                },
                {
                    "name": "group_id",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "ordering",
                    "in": "query",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": [
                            "username",
                            "-username",
                            "email",
                            "-email",
                            "date_joined",
                            "-date_joined",
                            "id",
                            "-id",
                        ],
                    },
                },
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                },
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
                },
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
                    "source": "curl -X POST "
                    "__BASE_URL__/api/v1/panel/users/ "
                    "\\\n"
                    '  -H "Authorization: Bearer '
                    'SEU_TOKEN" \\\n'
                    '  -H "Content-Type: '
                    'application/json" \\\n'
                    "  -d "
                    '"{\\"username\\":\\"api-user\\",\\"email\\":\\"api@example.com\\",\\"password\\":\\"SenhaSegura@123\\",\\"is_active\\":true}"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "payload = {\n"
                    '    "username": "api-user",\n'
                    '    "email": "api@example.com",\n'
                    '    "password": '
                    '"SenhaSegura@123",\n'
                    '    "is_active": True,\n'
                    "}\n"
                    "\n"
                    "response = requests.post(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/users/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    json=payload,\n"
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
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
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
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
                    "source": 'curl -H "Authorization: '
                    'Bearer SEU_TOKEN" '
                    "__BASE_URL__/api/v1/panel/users/1/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/users/1/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
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
                    "source": "curl -X PATCH "
                    "__BASE_URL__/api/v1/panel/users/1/ "
                    "\\\n"
                    '  -H "Authorization: Bearer '
                    'SEU_TOKEN" \\\n'
                    '  -H "Content-Type: '
                    'application/json" \\\n'
                    "  -d "
                    '"{\\"email\\":\\"alterado@example.com\\"}"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "payload = {\n"
                    '    "email": '
                    '"alterado@example.com",\n'
                    "}\n"
                    "\n"
                    "response = requests.patch(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/users/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    json=payload,\n"
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
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
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
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
                    "source": "curl -X DELETE "
                    "__BASE_URL__/api/v1/panel/users/1/ "
                    "\\\n"
                    '  -H "Authorization: '
                    'Bearer SEU_TOKEN"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = "
                    "requests.delete(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/users/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "responses": {
                "200": {
                    "description": "Usuário removido.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DeleteEnvelope"}
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
    },
}

GROUPS_PATHS_TEMPLATE: dict[str, Any] = {
    "/api/v1/panel/groups/": {
        "get": {
            "tags": ["Grupos do painel"],
            "summary": "Listar grupos",
            "description": "Lista grupos editáveis do painel, excluindo "
            "grupos protegidos.",
            "operationId": "api_groups_list",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/panel/groups/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": 'curl -H "Authorization: Bearer '
                    'SEU_TOKEN" '
                    "__BASE_URL__/api/v1/panel/groups/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/groups/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "search",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "name",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "permission_id",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "ordering",
                    "in": "query",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": ["name", "-name", "id", "-id"],
                    },
                },
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            ],
            "responses": {
                "200": {
                    "description": "Lista de grupos.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PanelGroupListEnvelope"
                            }
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
                    "source": "curl -X POST "
                    "__BASE_URL__/api/v1/panel/groups/ "
                    "\\\n"
                    '  -H "Authorization: Bearer '
                    'SEU_TOKEN" \\\n'
                    '  -H "Content-Type: '
                    'application/json" \\\n'
                    '  -d "{\\"name\\":\\"Grupo '
                    'API\\",\\"permissions\\":[1]}"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "payload = {\n"
                    '    "name": "Grupo API",\n'
                    '    "permissions": [1],\n'
                    "}\n"
                    "\n"
                    "response = requests.post(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/groups/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    json=payload,\n"
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/PanelGroupWriteInput"}
                    }
                },
            },
            "responses": {
                "201": {
                    "description": "Grupo criado.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PanelGroupEnvelope"
                            }
                        }
                    },
                },
                "400": {
                    "description": "Payload inválido.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
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
                    "source": 'curl -H "Authorization: '
                    'Bearer SEU_TOKEN" '
                    "__BASE_URL__/api/v1/panel/groups/1/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/groups/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "responses": {
                "200": {
                    "description": "Grupo encontrado.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PanelGroupEnvelope"
                            }
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
                    "source": "curl -X PATCH "
                    "__BASE_URL__/api/v1/panel/groups/1/ "
                    "\\\n"
                    '  -H "Authorization: '
                    'Bearer SEU_TOKEN" \\\n'
                    '  -H "Content-Type: '
                    'application/json" \\\n'
                    '  -d "{\\"name\\":\\"Grupo '
                    "API "
                    'Atualizado\\",\\"permissions\\":[1]}"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "payload = {\n"
                    '    "name": "Grupo API '
                    'Atualizado",\n'
                    '    "permissions": [1],\n'
                    "}\n"
                    "\n"
                    "response = "
                    "requests.patch(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/groups/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    json=payload,\n"
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
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
                            "schema": {
                                "$ref": "#/components/schemas/PanelGroupEnvelope"
                            }
                        }
                    },
                },
                "400": {
                    "description": "Payload inválido.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
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
                    "source": "curl -X DELETE "
                    "__BASE_URL__/api/v1/panel/groups/1/ "
                    "\\\n"
                    '  -H "Authorization: '
                    'Bearer SEU_TOKEN"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = "
                    "requests.delete(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/groups/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "responses": {
                "200": {
                    "description": "Grupo removido.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DeleteEnvelope"}
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
    },
}

MODULES_PATHS_TEMPLATE: dict[str, Any] = {
    "/api/v1/panel/modules/": {
        "get": {
            "tags": ["Módulos do painel"],
            "summary": "Listar módulos",
            "description": "Lista módulos do dashboard com filtros por "
            "grupo, status e permissão.",
            "operationId": "api_modules_list",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/panel/modules/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": 'curl -H "Authorization: Bearer '
                    'SEU_TOKEN" '
                    "__BASE_URL__/api/v1/panel/modules/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/modules/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "search",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "slug",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "menu_group",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "is_active",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "boolean"},
                },
                {
                    "name": "permission_id",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "ordering",
                    "in": "query",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": [
                            "name",
                            "-name",
                            "slug",
                            "-slug",
                            "menu_group",
                            "-menu_group",
                            "order",
                            "-order",
                            "id",
                            "-id",
                        ],
                    },
                },
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            ],
            "responses": {
                "200": {
                    "description": "Lista de módulos.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PanelModuleListEnvelope"
                            }
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
            "description": "Cria um módulo do dashboard com rota e "
            "permissão opcionais.",
            "operationId": "api_modules_create",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/panel/modules/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": "curl -X POST "
                    "__BASE_URL__/api/v1/panel/modules/ "
                    "\\\n"
                    '  -H "Authorization: Bearer '
                    'SEU_TOKEN" \\\n'
                    '  -H "Content-Type: '
                    'application/json" \\\n'
                    '  -d "{\\"name\\":\\"Módulo '
                    'API\\",\\"slug\\":\\"modulo-api\\",\\"url_name\\":\\"module_entry\\",\\"show_in_dashboard\\":true,\\"show_in_sidebar\\":true}"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "payload = {\n"
                    '    "name": "Módulo API",\n'
                    '    "slug": "modulo-api",\n'
                    '    "url_name": '
                    '"module_entry",\n'
                    '    "show_in_dashboard": True,\n'
                    '    "show_in_sidebar": True,\n'
                    "}\n"
                    "\n"
                    "response = requests.post(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/modules/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    json=payload,\n"
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/PanelModuleWriteInput"}
                    }
                },
            },
            "responses": {
                "201": {
                    "description": "Módulo criado.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PanelModuleEnvelope"
                            }
                        }
                    },
                },
                "400": {
                    "description": "Payload inválido.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
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
                    "source": 'curl -H "Authorization: '
                    'Bearer SEU_TOKEN" '
                    "__BASE_URL__/api/v1/panel/modules/1/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/modules/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "responses": {
                "200": {
                    "description": "Módulo encontrado.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PanelModuleEnvelope"
                            }
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
            "description": "Atualiza um módulo do dashboard, "
            "incluindo permissão e estado de "
            "publicação.",
            "operationId": "api_modules_update",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/panel/modules/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": "curl -X PATCH "
                    "__BASE_URL__/api/v1/panel/modules/1/ "
                    "\\\n"
                    '  -H "Authorization: '
                    'Bearer SEU_TOKEN" \\\n'
                    '  -H "Content-Type: '
                    'application/json" \\\n'
                    "  -d "
                    '"{\\"description\\":\\"Módulo '
                    "ajustado via "
                    'API\\",\\"is_active\\":false,\\"show_in_sidebar\\":false}"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "payload = {\n"
                    '    "description": '
                    '"Módulo ajustado via '
                    'API",\n'
                    '    "is_active": False,\n'
                    '    "show_in_sidebar": '
                    "False,\n"
                    "}\n"
                    "\n"
                    "response = "
                    "requests.patch(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/modules/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    json=payload,\n"
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
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
                            "schema": {
                                "$ref": "#/components/schemas/PanelModuleEnvelope"
                            }
                        }
                    },
                },
                "400": {
                    "description": "Payload inválido ou exclusão não permitida.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
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
                    "source": "curl -X DELETE "
                    "__BASE_URL__/api/v1/panel/modules/1/ "
                    "\\\n"
                    '  -H "Authorization: '
                    'Bearer SEU_TOKEN"',
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = "
                    "requests.delete(\n"
                    "    "
                    '"__BASE_URL__/api/v1/panel/modules/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "responses": {
                "200": {
                    "description": "Módulo removido.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DeleteEnvelope"}
                        }
                    },
                },
                "400": {
                    "description": "Exclusão não "
                    "permitida pelo "
                    "ciclo de vida do "
                    "módulo.",
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
}

AUDIT_PATHS_TEMPLATE: dict[str, Any] = {
    "/api/v1/core/audit-logs/": {
        "get": {
            "tags": ["Logs de auditoria"],
            "summary": "Listar logs de auditoria",
            "description": "Lista eventos de auditoria com filtros "
            "opcionais e paginação simples.",
            "operationId": "api_audit_logs_list",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/core/audit-logs/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": 'curl -H "Authorization: Bearer '
                    'SEU_TOKEN" '
                    "__BASE_URL__/api/v1/core/audit-logs/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/core/audit-logs/",\n'
                    '    headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "search",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "action",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "app_label",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "model",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "actor",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "object_id",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "path",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "date_from",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "format": "date"},
                },
                {
                    "name": "date_to",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "format": "date"},
                },
                {
                    "name": "ordering",
                    "in": "query",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": [
                            "created_at",
                            "-created_at",
                            "action",
                            "-action",
                            "actor",
                            "-actor",
                            "object",
                            "-object",
                            "id",
                            "-id",
                        ],
                    },
                },
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1},
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            ],
            "responses": {
                "200": {
                    "description": "Lista paginada de logs de auditoria.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/AuditLogListEnvelope"
                            }
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
        }
    },
    "/api/v1/core/audit-logs/{id}/": {
        "get": {
            "tags": ["Logs de auditoria"],
            "summary": "Detalhar log de auditoria",
            "description": "Retorna o payload completo de um evento "
            "individual da auditoria.",
            "operationId": "api_audit_log_detail",
            "security": [{"BearerAuth": []}],
            "x-base-url": "/api/v1/core/audit-logs/",
            "x-codeSamples": [
                {
                    "lang": "curl",
                    "source": 'curl -H "Authorization: '
                    'Bearer SEU_TOKEN" '
                    "__BASE_URL__/api/v1/core/audit-logs/1/",
                },
                {
                    "lang": "python",
                    "source": "import requests\n"
                    "\n"
                    "response = requests.get(\n"
                    "    "
                    '"__BASE_URL__/api/v1/core/audit-logs/1/",\n'
                    "    "
                    'headers={"Authorization": '
                    '"Bearer SEU_TOKEN"},\n'
                    "    timeout=30,\n"
                    ")\n"
                    "\n"
                    "print(response.status_code)\n"
                    "print(response.json())",
                },
            ],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "responses": {
                "200": {
                    "description": "Log de auditoria encontrado.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/AuditLogDetailEnvelope"
                            }
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

OPENAPI_PATH_TEMPLATES: tuple[dict[str, Any], ...] = (
    OPERACIONAL_PATHS_TEMPLATE,
    ACCESS_PATHS_TEMPLATE,
    USERS_PATHS_TEMPLATE,
    MODULES_PATHS_TEMPLATE,
    AUDIT_PATHS_TEMPLATE,
)


def build_openapi_paths(base_url: str) -> OrderedDict[str, dict[str, Any]]:
    """Materializa os paths versionados da API com a URL base atual."""

    paths: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for template in OPENAPI_PATH_TEMPLATES:
        materialized = _replace_base_url(template, base_url)
        paths.update(cast(dict[str, dict[str, Any]], materialized))
    return paths


def _replace_base_url(value: Any, base_url: str) -> Any:
    """Substitui a URL base placeholder pelos valores da instancia atual."""

    if isinstance(value, str):
        return value.replace(BASE_URL_PLACEHOLDER, base_url)
    if isinstance(value, list):
        return [_replace_base_url(item, base_url) for item in value]
    if isinstance(value, dict):
        return {key: _replace_base_url(item, base_url) for key, item in value.items()}
    return value
