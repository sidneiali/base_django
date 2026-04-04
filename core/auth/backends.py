"""Backends usados pelo fluxo publico de autenticacao."""

from __future__ import annotations

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameModelBackend(ModelBackend):
    """Permite autenticar por e-mail no login publico sem quebrar username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Tenta resolver por e-mail; em fallback, usa o username tradicional."""

        identifier = (kwargs.get("email") or username or "").strip()
        if not identifier or password is None:
            return None

        email_matches = list(
            User._default_manager.filter(email__iexact=identifier)[:2]
        )
        if len(email_matches) == 1:
            user = email_matches[0]
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None

        return super().authenticate(
            request,
            username=identifier,
            password=password,
            **kwargs,
        )

    def get_user(self, user_id):
        """Preserva a recuperacao padrao do usuário por PK."""

        return super().get_user(user_id)
