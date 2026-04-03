"""Componentes OpenAPI compartilhados pela documentacao publica da API."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

OPENAPI_COMPONENTS_TEMPLATE: dict[str, Any] = {
    "securitySchemes": {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "Token"}
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
            "required": [
                "id",
                "username",
                "first_name",
                "last_name",
                "email",
                "is_active",
                "groups",
            ],
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
            "required": [
                "resource",
                "label",
                "can_create",
                "can_read",
                "can_update",
                "can_delete",
            ],
        },
        "TokenStatus": {
            "type": "object",
            "properties": {
                "api_enabled": {"type": "boolean"},
                "token": {
                    "type": "object",
                    "properties": {
                        "token_prefix": {"type": "string"},
                        "issued_at": {
                            "type": ["string", "null"],
                            "format": "date-time",
                        },
                        "last_used_at": {
                            "type": ["string", "null"],
                            "format": "date-time",
                        },
                        "revoked_at": {
                            "type": ["string", "null"],
                            "format": "date-time",
                        },
                        "is_active": {"type": "boolean"},
                    },
                    "required": [
                        "token_prefix",
                        "issued_at",
                        "last_used_at",
                        "revoked_at",
                        "is_active",
                    ],
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
            "required": [
                "id",
                "username",
                "first_name",
                "last_name",
                "email",
                "is_active",
                "groups",
            ],
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
                    "items": {"$ref": "#/components/schemas/GroupPermissionSummary"},
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
                "permission": {"$ref": "#/components/schemas/ModulePermissionSummary"},
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
        "DeletePayload": {
            "type": "object",
            "properties": {
                "deleted": {"type": "boolean"},
                "resource": {"type": "string"},
                "id": {"type": "integer"},
            },
            "required": ["deleted", "resource", "id"],
        },
        "DeleteEnvelope": {
            "type": "object",
            "properties": {
                "data": {"$ref": "#/components/schemas/DeletePayload"},
                "meta": {"$ref": "#/components/schemas/ApiMeta"},
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
}


def build_openapi_components() -> dict[str, Any]:
    """Retorna uma copia isolada dos componentes da especificacao OpenAPI."""

    return deepcopy(OPENAPI_COMPONENTS_TEMPLATE)
