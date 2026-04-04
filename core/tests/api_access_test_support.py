"""Suporte compartilhado para testes de acesso à API.

Fornece factories e helpers para criar tokens com diferentes permissões,
reutilizáveis entre testes de documentação, auditoria e introspecção.
"""

from __future__ import annotations

from typing import Protocol

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken
from core.tests.factories import GroupFactory, UserFactory


class TokenIssueParams(Protocol):
    """Parâmetros para criação de token com permissões."""

    resources: list[tuple[str, bool, bool]] | None
    """Lista de (resource, can_read, can_create) a configurar."""

    api_enabled: bool
    """Se o acesso à API está habilitado para o usuário."""

    username: str
    """Nome de usuário."""

    email: str
    """Email do usuário."""

    groups: list[str] | None
    """Nomes dos grupos a adicionar ao usuário."""


class ApiAccessFactory:
    """Factory para criar usuários, tokens e permissões de API em testes."""

    @staticmethod
    def issue_token_with_resource_permissions(
        *,
        resources: list[tuple[str, bool, bool]] | None = None,
        api_enabled: bool = True,
        username: str = "api-user",
        email: str = "api@example.com",
        groups: list[str] | None = None,
    ) -> tuple[object, str]:
        """Cria um usuário com token e permissões de recurso específicas.

        Args:
            resources: Lista de (resource, can_read, can_create). Exemplo:
                [
                    (ApiResourcePermission.Resource.CORE_AUDIT_LOGS, True, False),
                    (ApiResourcePermission.Resource.CORE_API_ACCESS, True, True),
                ]
            api_enabled: Se a API deve estar habilitada para o usuário.
            username: Nome de usuário único.
            email: Email do usuário.
            groups: Nomes de grupos a adicionar (criados se não existirem).

        Returns:
            Tupla (user, raw_token).
        """
        user = UserFactory.create(
            username=username,
            email=email,
        )

        if groups:
            for group_name in groups:
                group = GroupFactory.create(name=group_name)
                user.groups.add(group)

        access_profile = ApiAccessProfile.objects.create(
            user=user,
            api_enabled=api_enabled,
        )

        if resources:
            for resource, can_read, can_create in resources:
                ApiResourcePermission.objects.create(
                    access_profile=access_profile,
                    resource=resource,
                    can_read=can_read,
                    can_create=can_create,
                )

        _token, raw_token = ApiToken.issue_for_user(user)
        return user, raw_token

    @staticmethod
    def issue_token_with_single_resource(
        resource: str,
        *,
        can_read: bool = True,
        can_create: bool = False,
        api_enabled: bool = True,
        username: str = "api-user",
        email: str = "api@example.com",
    ) -> str:
        """Cria um usuário com token e permissão para um único recurso.

        Atalho para o caso comum de um recurso com uma permissão.

        Args:
            resource: O recurso (ex: ApiResourcePermission.Resource.CORE_AUDIT_LOGS).
            can_read: Se pode ler o recurso.
            can_create: Se pode criar no recurso.
            api_enabled: Se a API está habilitada.
            username: Nome de usuário único.
            email: Email do usuário.

        Returns:
            Raw token.
        """
        _user, raw_token = ApiAccessFactory.issue_token_with_resource_permissions(
            resources=[(resource, can_read, can_create)],
            api_enabled=api_enabled,
            username=username,
            email=email,
        )
        return raw_token

    @staticmethod
    def issue_token_without_permission(
        resource: str,
        *,
        username: str = "api-restricted",
        email: str = "restricted@example.com",
    ) -> str:
        """Cria um usuário com token mas SEM permissão para um recurso específico.

        Útil para testar bloqueio por falta de permissão.

        Args:
            resource: O recurso que será bloqueado.
            username: Nome de usuário único.
            email: Email do usuário.

        Returns:
            Raw token sem acesso ao recurso.
        """
        return ApiAccessFactory.issue_token_with_single_resource(
            resource,
            can_read=False,
            can_create=False,
            username=username,
            email=email,
        )

    @staticmethod
    def issue_token_with_api_disabled(
        *,
        username: str = "api-disabled",
        email: str = "disabled@example.com",
    ) -> str:
        """Cria um usuário com token mas com API desabilitada.

        Útil para testar bloqueio por API desabilitada.

        Args:
            username: Nome de usuário único.
            email: Email do usuário.

        Returns:
            Raw token sem acesso à API.
        """
        _user, raw_token = ApiAccessFactory.issue_token_with_resource_permissions(
            api_enabled=False,
            username=username,
            email=email,
        )
        return raw_token
