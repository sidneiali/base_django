"""Apoio compartilhado pelos testes da API JSON do painel."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken
from core.tests.factories import UserFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.urls import reverse

User = get_user_model()


class PanelApiTokenMixin:
    """Expõe helpers mínimos para emissão de tokens Bearer nos testes."""

    def _issue_token(
        self,
        *,
        resource: str = ApiResourcePermission.Resource.PANEL_USERS,
        username: str | None = None,
        email: str | None = None,
        **permissions: bool,
    ) -> tuple[AbstractUser, str]:
        """Cria um usuário de API com token ativo e permissão configurável."""

        resolved_username = username or "api-client"
        if username is None and User.objects.filter(username=resolved_username).exists():
            resolved_username = f"{resolved_username}-{User.objects.count()}"
        user = UserFactory.create(
            username=resolved_username,
            email=email or f"{resolved_username}@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=resource,
            **permissions,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return user, raw_token

    def _issue_raw_token(
        self,
        *,
        resource: str = ApiResourcePermission.Resource.PANEL_USERS,
        username: str | None = None,
        email: str | None = None,
        **permissions: bool,
    ) -> str:
        """Atalho para os cenários que só precisam do token bruto."""

        _user, raw_token = self._issue_token(
            resource=resource,
            username=username,
            email=email,
            **permissions,
        )
        return raw_token


class HasPk(Protocol):
    """Contrato mínimo para objetos usados nos detalhes dos testes."""

    pk: int


ResourceFactory = Callable[[], HasPk]


@dataclass(frozen=True, slots=True)
class PanelApiResourceCase:
    """Define um recurso do painel com URLs e payloads reutilizáveis."""

    label: str
    resource: str
    collection_url_name: str
    detail_url_name: str
    factory: ResourceFactory
    create_payload: dict[str, object]
    update_payload: dict[str, object]

    @property
    def collection_url(self) -> str:
        """Materializa a URL da coleção do recurso."""

        return reverse(self.collection_url_name)

    def detail_url(self, pk: int) -> str:
        """Materializa a URL de detalhe do recurso."""

        return reverse(self.detail_url_name, args=[pk])


def build_panel_api_resource_cases(
    *,
    user_factory: ResourceFactory,
    group_factory: ResourceFactory,
    module_factory: ResourceFactory,
) -> tuple[PanelApiResourceCase, ...]:
    """Retorna a matriz compartilhada de recursos JSON do painel."""

    return (
        PanelApiResourceCase(
            label="usuarios",
            resource=ApiResourcePermission.Resource.PANEL_USERS,
            collection_url_name="api_panel_users_collection",
            detail_url_name="api_panel_user_detail",
            factory=user_factory,
            create_payload={
                "username": "novo-operacional",
                "email": "novo-operacional@example.com",
                "password": "SenhaSegura@123",
            },
            update_payload={
                "email": "atualizado-operacional@example.com",
            },
        ),
        PanelApiResourceCase(
            label="grupos",
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            collection_url_name="api_panel_groups_collection",
            detail_url_name="api_panel_group_detail",
            factory=group_factory,
            create_payload={
                "name": "Grupo Operacional",
            },
            update_payload={
                "name": "Grupo Operacional Atualizado",
            },
        ),
        PanelApiResourceCase(
            label="modulos",
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            collection_url_name="api_panel_modules_collection",
            detail_url_name="api_panel_module_detail",
            factory=module_factory,
            create_payload={
                "name": "Módulo Operacional",
                "slug": "modulo-operacional",
                "url_name": "module_entry",
            },
            update_payload={
                "description": "Módulo atualizado via teste operacional",
            },
        ),
    )
