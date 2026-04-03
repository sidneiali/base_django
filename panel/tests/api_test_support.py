"""Apoio compartilhado pelos testes da API JSON do painel."""

from __future__ import annotations

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken
from django.contrib.auth import get_user_model

User = get_user_model()


class PanelApiTokenMixin:
    """Expõe helpers mínimos para emissão de tokens Bearer nos testes."""

    def _issue_token(
        self,
        *,
        resource: str = ApiResourcePermission.Resource.PANEL_USERS,
        username: str = "api-client",
        email: str | None = None,
        **permissions: bool,
    ) -> tuple[object, str]:
        """Cria um usuário de API com token ativo e permissão configurável."""

        user = User.objects.create_user(
            username=username,
            email=email or f"{username}@example.com",
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
