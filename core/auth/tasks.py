"""Tarefas assíncronas do fluxo público de autenticação."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from celery import shared_task  # type: ignore[import-untyped]

from .services import _deliver_password_recovery_email

User = get_user_model()


@shared_task(
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def send_password_recovery_email_task(
    *,
    user_id: int,
    protocol: str,
    domain: str,
    from_email: str,
) -> None:
    """Entrega o e-mail de recuperação em worker dedicado."""

    user = User.objects.filter(pk=user_id).first()
    if user is None or not str(user.email or "").strip():
        return
    _deliver_password_recovery_email(
        user=user,
        protocol=protocol,
        domain=domain,
        from_email=from_email,
    )
