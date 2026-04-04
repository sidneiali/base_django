"""Sinais de autenticação auditados pelo app core."""

from __future__ import annotations

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models import Q
from django.dispatch import receiver

from ..audit import build_instance_snapshot, create_audit_log
from ..models import AuditLog
from .shared import User, sanitize_credentials


@receiver(user_logged_in, dispatch_uid="core.audit.log_user_login")
def log_user_login(sender, request, user, **kwargs):
    """Registra logins bem-sucedidos."""

    after_state, _ = build_instance_snapshot(user)
    create_audit_log(
        AuditLog.ACTION_LOGIN,
        instance=user,
        actor=user,
        after=after_state,
        metadata={"event": "user_logged_in"},
    )


@receiver(user_logged_out, dispatch_uid="core.audit.log_user_logout")
def log_user_logout(sender, request, user, **kwargs):
    """Registra logouts do sistema."""

    if user is None:
        return

    before_state, _ = build_instance_snapshot(user)
    create_audit_log(
        AuditLog.ACTION_LOGOUT,
        instance=user,
        actor=user,
        before=before_state,
        metadata={"event": "user_logged_out"},
    )


@receiver(user_login_failed, dispatch_uid="core.audit.log_failed_login")
def log_failed_login(sender, credentials, request, **kwargs):
    """Registra tentativas de login que falharam."""

    safe_credentials = sanitize_credentials(credentials)
    identifier = str(
        safe_credentials.get("username")
        or safe_credentials.get("email")
        or safe_credentials.get("identifier")
        or ""
    )
    target_user = None

    if identifier:
        target_user = User._default_manager.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()

    create_audit_log(
        AuditLog.ACTION_LOGIN_FAILED,
        instance=target_user,
        actor_identifier=identifier,
        metadata={"credentials": safe_credentials, "event": "user_login_failed"},
        object_repr=identifier or "Falha de login",
    )
