"""Servicos do dominio de usuarios do painel."""

from __future__ import annotations

from dataclasses import dataclass

from core.auth.services import (
    send_first_access_invitation_email,
    send_password_recovery_email,
)
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet

from ..autonomy import PROFILE_SCOPE_BLOCK_REASON, user_within_actor_scope


class UserInvitationDeliveryError(Exception):
    """Erro funcional ao criar um usuario com convite de primeiro acesso."""


@dataclass(frozen=True, slots=True)
class CommonUserListRow:
    """Estado renderizável de uma linha da listagem de usuários comuns."""

    user: User
    management_block_reason: str
    password_reset_block_reason: str


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


def get_common_user_management_block_reason(
    user: User,
    *,
    acting_user: User | None,
) -> str:
    """Explica por que o usuário não pode ser operado por este operador."""

    if not user_within_actor_scope(user, acting_user=acting_user):
        return PROFILE_SCOPE_BLOCK_REASON
    return ""


def build_common_user_list_rows(
    users,
    *,
    acting_user: User | None,
) -> list[CommonUserListRow]:
    """Monta as linhas renderizáveis da listagem de usuários comuns."""

    rows: list[CommonUserListRow] = []
    for user in users:
        management_block_reason = get_common_user_management_block_reason(
            user,
            acting_user=acting_user,
        )
        rows.append(
            CommonUserListRow(
                user=user,
                management_block_reason=management_block_reason,
                password_reset_block_reason=(
                    management_block_reason
                    or get_common_user_password_reset_block_reason(user)
                ),
            )
        )
    return rows


def get_common_user_password_reset_block_reason(user: User) -> str:
    """Explica por que a recuperação não pode ser enviada ao usuário."""

    if not str(user.email or "").strip():
        return "O usuário precisa ter um e-mail cadastrado para receber a recuperação."
    return ""


def send_common_user_password_reset(request, user: User) -> None:
    """Dispara o e-mail padrão de recuperação para um usuário comum."""

    send_password_recovery_email(request, user)
