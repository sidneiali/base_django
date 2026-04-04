"""Regras operacionais para contas administrativas no painel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet


class AdminAccountOperationBlockedError(Exception):
    """Erro funcional para ações bloqueadas na superfície administrativa."""


@dataclass(frozen=True, slots=True)
class AdminAccountListRow:
    """Estado renderizável de uma linha da listagem de contas administrativas."""

    user: User
    toggle_block_reason: str
    delete_block_reason: str


def administrative_users_queryset() -> QuerySet[User]:
    """Retorna apenas as contas administrativas gerenciáveis no painel."""

    return User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))


def count_other_active_superusers(user: User) -> int:
    """Conta quantos superusuários ativos existem além do usuário informado."""

    return administrative_users_queryset().filter(
        is_superuser=True,
        is_active=True,
    ).exclude(pk=user.pk).count()


def get_admin_account_transition_block_reason(
    user: User,
    *,
    acting_user: User | None,
    next_is_active: bool,
    next_is_staff: bool,
    next_is_superuser: bool,
) -> str:
    """Explica por que a conta administrativa não pode assumir o novo estado."""

    if not next_is_staff and not next_is_superuser:
        return (
            "A conta administrativa precisa manter pelo menos um dos papéis: "
            "staff ou superusuário."
        )

    if not user.pk:
        return ""

    if acting_user is not None and acting_user.pk == user.pk:
        if not next_is_active or not next_is_staff or not next_is_superuser:
            return (
                "Use outra conta administrativa para reduzir o acesso da sua própria conta."
            )

    if user.is_superuser and user.is_active:
        is_losing_last_active_superuser = (
            (not next_is_superuser or not next_is_active)
            and count_other_active_superusers(user) == 0
        )
        if is_losing_last_active_superuser:
            return "Mantenha pelo menos um superusuário ativo no sistema."

    return ""


def get_admin_account_delete_block_reason(
    user: User,
    *,
    acting_user: User | None,
) -> str:
    """Explica por que a conta administrativa não pode ser excluída."""

    if not user.pk:
        return ""

    if acting_user is not None and acting_user.pk == user.pk:
        return "Você não pode excluir sua própria conta administrativa pelo painel."

    if user.is_superuser and user.is_active and count_other_active_superusers(user) == 0:
        return "Mantenha pelo menos um superusuário ativo no sistema."

    return ""


def build_admin_account_list_rows(
    users: Iterable[User],
    *,
    acting_user: User | None,
) -> list[AdminAccountListRow]:
    """Anexa o estado operacional de toggle/delete para cada conta listada."""

    rows: list[AdminAccountListRow] = []
    for user in users:
        toggle_block_reason = ""
        if user.is_active:
            toggle_block_reason = get_admin_account_transition_block_reason(
                user,
                acting_user=acting_user,
                next_is_active=False,
                next_is_staff=user.is_staff,
                next_is_superuser=user.is_superuser,
            )
        rows.append(
            AdminAccountListRow(
                user=user,
                toggle_block_reason=toggle_block_reason,
                delete_block_reason=get_admin_account_delete_block_reason(
                    user,
                    acting_user=acting_user,
                ),
            )
        )
    return rows


def activate_admin_account(user: User) -> None:
    """Ativa uma conta administrativa sem regras adicionais."""

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])


def deactivate_admin_account(
    user: User,
    *,
    acting_user: User | None,
) -> None:
    """Inativa uma conta administrativa respeitando as travas operacionais."""

    reason = get_admin_account_transition_block_reason(
        user,
        acting_user=acting_user,
        next_is_active=False,
        next_is_staff=user.is_staff,
        next_is_superuser=user.is_superuser,
    )
    if reason:
        raise AdminAccountOperationBlockedError(reason)

    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])


def delete_admin_account(
    user: User,
    *,
    acting_user: User | None,
) -> None:
    """Exclui uma conta administrativa respeitando as travas operacionais."""

    reason = get_admin_account_delete_block_reason(user, acting_user=acting_user)
    if reason:
        raise AdminAccountOperationBlockedError(reason)
    user.delete()
