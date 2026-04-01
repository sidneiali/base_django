"""Campos compartilhados para configurar acesso a API em formularios de usuario."""

from __future__ import annotations

from typing import cast

from django import forms
from django.utils.text import format_lazy

from ..models import ApiResourcePermission
from .access import get_user_api_access_values, save_user_api_access
from .types import (
    ApiAccessValues,
    ApiActionOption,
    ApiPermissionFlags,
    ApiPermissionMatrix,
    ApiResourceOption,
    DisplayLabel,
)

API_RESOURCE_OPTIONS = cast(
    tuple[ApiResourceOption, ...],
    tuple(ApiResourcePermission.Resource.choices),
)
API_ACTION_OPTIONS: tuple[ApiActionOption, ...] = (
    ("create", "Criar", "can_create"),
    ("read", "Ler", "can_read"),
    ("update", "Editar", "can_update"),
    ("delete", "Excluir", "can_delete"),
)
API_RESOURCE_ALLOWED_ACTIONS: dict[str, set[str]] = {
    ApiResourcePermission.Resource.PANEL_USERS: {"create", "read", "update", "delete"},
    ApiResourcePermission.Resource.PANEL_GROUPS: {"create", "read", "update", "delete"},
    ApiResourcePermission.Resource.CORE_API_ACCESS: {"read"},
    ApiResourcePermission.Resource.CORE_AUDIT_LOGS: {"read"},
}


def build_api_enabled_field() -> forms.BooleanField:
    """Cria o campo de habilitacao global do acesso a API."""

    return forms.BooleanField(
        required=False,
        label="API habilitada",
        help_text="Quando desabilitada, o token deixa de autorizar chamadas.",
    )


def build_api_permission_field(
    resource_label: DisplayLabel,
    action_label: DisplayLabel,
) -> forms.BooleanField:
    """Cria um checkbox para uma combinacao recurso x acao CRUD."""

    return forms.BooleanField(
        required=False,
        label=format_lazy("{}: {}", resource_label, action_label),
    )


def build_api_permission_field_name(resource: str, action: str) -> str:
    """Converte um recurso e uma acao num nome de campo estavel."""

    return f"api_{resource.replace('.', '_')}_{action}"


def resource_supports_action(resource: str, action: str) -> bool:
    """Indica se um recurso realmente expõe a ação CRUD informada."""

    return action in API_RESOURCE_ALLOWED_ACTIONS.get(resource, set())


API_PERMISSION_FIELD_ROWS = tuple(
    tuple(
        build_api_permission_field_name(resource, action)
        for action, _, _ in API_ACTION_OPTIONS
    )
    for resource, _ in API_RESOURCE_OPTIONS
)


class ApiAccessFormMixin(forms.Form):
    """Adiciona ao formulario os campos de habilitacao e CRUD da API."""

    api_enabled = build_api_enabled_field()

    for _resource, _resource_label in API_RESOURCE_OPTIONS:
        for _action, _action_label, _permission_key in API_ACTION_OPTIONS:
            locals()[build_api_permission_field_name(_resource, _action)] = (
                build_api_permission_field(_resource_label, _action_label)
            )

    del _resource
    del _resource_label
    del _action
    del _action_label
    del _permission_key

    def __init__(self, *args, **kwargs):
        """Preenche os campos de API com os valores atuais do usuario."""

        super().__init__(*args, **kwargs)

        for resource, _resource_label in API_RESOURCE_OPTIONS:
            for action, _action_label, _permission_key in API_ACTION_OPTIONS:
                if resource_supports_action(resource, action):
                    continue

                field_name = build_api_permission_field_name(resource, action)
                field = self.fields[field_name]
                field.disabled = True
                field.initial = False
                field.widget.attrs.update(
                    {
                        "disabled": True,
                        "data-api-disabled": "true",
                    }
                )

        if self.is_bound:
            return

        values = get_user_api_access_values(getattr(self, "instance", None))
        self.fields["api_enabled"].initial = values["api_enabled"]

        permission_matrix = values["permissions"]
        for resource, _ in API_RESOURCE_OPTIONS:
            for action, _, permission_key in API_ACTION_OPTIONS:
                field_name = build_api_permission_field_name(resource, action)
                self.fields[field_name].initial = permission_matrix[resource][
                    permission_key
                ]

    def get_api_permission_rows(self) -> list[dict[str, object]]:
        """Monta linhas prontas para a tabela de permissoes da API."""

        rows: list[dict[str, object]] = []
        for resource, resource_label in API_RESOURCE_OPTIONS:
            fields = []
            for action, action_label, _permission_key in API_ACTION_OPTIONS:
                fields.append(
                    {
                        "label": action_label,
                        "field": self[
                            build_api_permission_field_name(resource, action)
                        ],
                        "is_supported": resource_supports_action(resource, action),
                    }
                )
            rows.append({"label": resource_label, "fields": fields})
        return rows

    def build_api_access_payload(self) -> ApiAccessValues:
        """Converte os campos do formulario no payload persistido em banco."""

        permissions: ApiPermissionMatrix = {}
        for resource, _ in API_RESOURCE_OPTIONS:
            resource_permissions: ApiPermissionFlags = {
                "can_create": False,
                "can_read": False,
                "can_update": False,
                "can_delete": False,
            }
            for action, _action_label, permission_key in API_ACTION_OPTIONS:
                field_name = build_api_permission_field_name(resource, action)
                if not resource_supports_action(resource, action):
                    continue
                is_allowed = bool(self.cleaned_data.get(field_name, False))
                if permission_key == "can_create":
                    resource_permissions["can_create"] = is_allowed
                elif permission_key == "can_read":
                    resource_permissions["can_read"] = is_allowed
                elif permission_key == "can_update":
                    resource_permissions["can_update"] = is_allowed
                elif permission_key == "can_delete":
                    resource_permissions["can_delete"] = is_allowed
            permissions[resource] = resource_permissions

        return {
            "api_enabled": bool(self.cleaned_data.get("api_enabled", False)),
            "permissions": permissions,
        }

    def save_api_access_settings(self, user) -> bool:
        """Persiste a configuracao de acesso a API para o usuario salvo."""

        payload = self.build_api_access_payload()
        return save_user_api_access(
            user,
            api_enabled=bool(payload["api_enabled"]),
            permissions=payload["permissions"],
        )
