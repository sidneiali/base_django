"""Servicos do dominio de usuarios do painel."""

from __future__ import annotations

from core.auth.services import (
    send_first_access_invitation_email,
    send_password_recovery_email,
)
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet


class UserInvitationDeliveryError(Exception):
    """Erro funcional ao criar um usuario com convite de primeiro acesso."""


def common_users_queryset() -> QuerySet[User]:
    """Retorna apenas usuários comuns, fora da área administrativa."""

    return User.objects.filter(is_staff=False, is_superuser=False)


def save_common_user_form(form) -> User:
    """Persiste um formulário de usuário comum respeitando o fluxo atual."""

    return form.save()


def create_user_with_first_access_invitation(form, request):
    """Cria o usuário e envia o convite inicial como uma única operação."""

    try:
        with transaction.atomic():
            user = form.save()
            send_first_access_invitation_email(request, user)
    except Exception as exc:
        raise UserInvitationDeliveryError(
            "Não foi possível enviar o e-mail de primeiro acesso. "
            "Revise a configuração de e-mail e tente novamente."
        ) from exc

    return user


def set_common_user_active_state(user: User, *, is_active: bool) -> User:
    """Ativa ou inativa um usuário comum sem repetir lógica nas views."""

    if user.is_active != is_active:
        user.is_active = is_active
        user.save(update_fields=["is_active"])
    return user


def delete_common_user(user: User) -> None:
    """Remove um usuário comum do painel."""

    user.delete()


def get_common_user_password_reset_block_reason(user: User) -> str:
    """Explica por que a recuperação não pode ser enviada ao usuário."""

    if not str(user.email or "").strip():
        return "O usuário precisa ter um e-mail cadastrado para receber a recuperação."
    return ""


def send_common_user_password_reset(request, user: User) -> None:
    """Dispara o e-mail padrão de recuperação para um usuário comum."""

    send_password_recovery_email(request, user)
