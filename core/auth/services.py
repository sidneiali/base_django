"""Servicos do fluxo publico de autenticacao."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def _build_password_recovery_context(
    *,
    user: User,
    protocol: str,
    domain: str,
) -> dict[str, str | User]:
    """Monta o contexto comum usado pelos e-mails com token de redefinição."""

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


def _resolve_request_origin(request) -> tuple[str, str]:
    """Extrai protocolo e domínio a partir do request atual."""

    return ("https" if request.is_secure() else "http", request.get_host())


def _deliver_password_recovery_email(
    *,
    user: User,
    protocol: str,
    domain: str,
    from_email: str,
) -> None:
    """Entrega sincronamente o e-mail padrão de recuperação."""

    context = _build_password_recovery_context(
        user=user,
        protocol=protocol,
        domain=domain,
    )
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
        from_email,
        [user.email],
        fail_silently=False,
    )


def queue_password_recovery_email(
    *,
    user: User,
    protocol: str,
    domain: str,
    from_email: str | None = None,
    on_commit: bool = False,
) -> None:
    """Enfileira o e-mail de recuperação para processamento assíncrono."""

    from .tasks import send_password_recovery_email_task

    def dispatch() -> None:
        send_password_recovery_email_task.delay(
            user_id=user.pk,
            protocol=protocol,
            domain=domain,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        )

    if on_commit:
        transaction.on_commit(dispatch)
        return
    dispatch()


def send_first_access_invitation_email(request, user: User) -> None:
    """Envia o convite de primeiro acesso usando o fluxo de definir senha."""

    protocol, domain = _resolve_request_origin(request)
    context = _build_password_recovery_context(
        user=user,
        protocol=protocol,
        domain=domain,
    )
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
    """Enfileira o e-mail de recuperação de senha para um usuário específico."""

    protocol, domain = _resolve_request_origin(request)
    queue_password_recovery_email(
        user=user,
        protocol=protocol,
        domain=domain,
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
