"""Servicos do dominio de usuarios do painel."""

from __future__ import annotations

from core.auth.services import send_first_access_invitation_email
from django.db import transaction


class UserInvitationDeliveryError(Exception):
    """Erro funcional ao criar um usuario com convite de primeiro acesso."""


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
