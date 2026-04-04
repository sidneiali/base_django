"""Servicos do fluxo publico de autenticacao."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def _build_password_recovery_context(request, user: User) -> dict[str, str | User]:
    """Monta o contexto comum usado pelos e-mails com token de redefinição."""

    protocol = "https" if request.is_secure() else "http"
    domain = request.get_host()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_path = reverse("password_reset_confirm", args=[uid, token])
    return {
        "user": user,
        "email": user.email,
        "domain": domain,
        "protocol": protocol,
        "site_name": "BaseApp",
        "uid": uid,
        "token": token,
        "reset_url": f"{protocol}://{domain}{reset_path}",
    }


def send_first_access_invitation_email(request, user: User) -> None:
    """Envia o convite de primeiro acesso usando o fluxo de definir senha."""

    context = _build_password_recovery_context(request, user)
    subject = render_to_string(
        "registration/first_access_subject.txt",
        context,
    ).strip()
    message = render_to_string("registration/first_access_email.txt", context)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_recovery_email(request, user: User) -> None:
    """Envia o e-mail padrão de recuperação de senha para um usuário específico."""

    context = _build_password_recovery_context(request, user)
    subject = render_to_string(
        "registration/password_reset_subject.txt",
        context,
    ).strip()
    message = render_to_string(
        "registration/password_reset_email.html",
        context,
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
