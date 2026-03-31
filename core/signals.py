"""Sinais usados para registrar eventos relevantes de auditoria."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models import Model
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .audit import (
    build_changes,
    build_instance_snapshot,
    create_audit_log,
    serialize_related_queryset,
)
from .models import AuditLog

User = get_user_model()
TRACKED_MODEL_LABELS = {
    "auth.user",
    "auth.group",
    "core.apiaccessprofile",
    "core.apiresourcepermission",
    "core.apitoken",
    "core.module",
    "core.userinterfacepreference",
}


def _is_tracked_model(sender: type[Model]) -> bool:
    """Indica se o model deve gerar eventos de auditoria."""

    return sender._meta.label_lower in TRACKED_MODEL_LABELS


def _build_m2m_change_payload(instance: Model, relation_name: str, action: str, pk_set) -> dict:
    """Resume a mudanca aplicada a um relacionamento many-to-many."""

    manager = getattr(instance, relation_name)
    related_model = manager.model
    current_items = serialize_related_queryset(manager.all())
    changed_items = []

    if pk_set:
        changed_items = serialize_related_queryset(
            related_model._default_manager.filter(pk__in=pk_set)
        )

    return {
        relation_name: {
            "operation": action,
            "changed_items": changed_items,
            "current_items": current_items,
        }
    }


def _sanitize_credentials(credentials: dict[str, object]) -> dict[str, object]:
    """Remove valores sensiveis do payload recebido em falhas de login."""

    safe_credentials: dict[str, object] = {}
    for key, value in credentials.items():
        normalized_key = key.lower()
        if any(token in normalized_key for token in ("password", "token", "secret")):
            continue
        safe_credentials[key] = value
    return safe_credentials


@receiver(pre_save, dispatch_uid="core.audit.capture_pre_save_state")
def capture_pre_save_state(sender, instance, raw=False, **kwargs):
    """Captura o estado atual do objeto antes da persistencia."""

    if raw or not _is_tracked_model(sender):
        return

    if not instance.pk:
        instance._audit_before_state = {}
        instance._audit_before_comparison = {}
        return

    try:
        previous_instance = sender._default_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_before_state = {}
        instance._audit_before_comparison = {}
        return

    before_state, before_comparison = build_instance_snapshot(previous_instance)
    instance._audit_before_state = before_state
    instance._audit_before_comparison = before_comparison


@receiver(post_save, dispatch_uid="core.audit.log_saved_instance")
def log_saved_instance(sender, instance, created, raw=False, **kwargs):
    """Registra criacoes e alteracoes em models monitorados."""

    if raw or not _is_tracked_model(sender):
        return

    after_state, after_comparison = build_instance_snapshot(instance)

    if created:
        metadata = {}
        if instance._meta.label_lower == "core.apitoken":
            metadata["event"] = "api_token_issued"

        create_audit_log(
            AuditLog.ACTION_CREATE,
            instance=instance,
            after=after_state,
            changes=build_changes({}, after_state, {}, after_comparison),
            metadata=metadata,
        )
        return

    before_state = getattr(instance, "_audit_before_state", {})
    before_comparison = getattr(instance, "_audit_before_comparison", {})
    changes = build_changes(
        before_state,
        after_state,
        before_comparison,
        after_comparison,
    )

    if not changes:
        return

    metadata = {}
    if instance._meta.label_lower == "auth.user" and "password" in changes:
        metadata["event"] = "password_changed"
    if instance._meta.label_lower == "core.apitoken":
        if "revoked_at" in changes and after_state.get("revoked_at"):
            metadata["event"] = "api_token_revoked"
        elif "token_hash" in changes:
            metadata["event"] = "api_token_rotated"

    create_audit_log(
        AuditLog.ACTION_UPDATE,
        instance=instance,
        before=before_state,
        after=after_state,
        changes=changes,
        metadata=metadata,
    )


@receiver(pre_delete, dispatch_uid="core.audit.capture_pre_delete_state")
def capture_pre_delete_state(sender, instance, **kwargs):
    """Guarda o estado final do objeto antes da exclusao."""

    if not _is_tracked_model(sender):
        return

    before_state, _ = build_instance_snapshot(instance)
    instance._audit_before_delete_state = before_state
    instance._audit_before_delete_object_id = str(instance.pk)


@receiver(post_delete, dispatch_uid="core.audit.log_deleted_instance")
def log_deleted_instance(sender, instance, **kwargs):
    """Registra exclusoes em models monitorados."""

    if not _is_tracked_model(sender):
        return

    before_state = getattr(instance, "_audit_before_delete_state", None)
    if before_state is None:
        before_state, _ = build_instance_snapshot(instance)

    create_audit_log(
        AuditLog.ACTION_DELETE,
        instance=instance,
        object_id=getattr(instance, "_audit_before_delete_object_id", ""),
        before=before_state,
        changes=build_changes(before_state, {}),
    )


def _log_tracked_m2m_change(relation_name: str, instance: Model, action: str, reverse: bool, pk_set):
    """Registra alteracoes relevantes de relacionamentos M2M."""

    if reverse or action not in {"post_add", "post_remove", "post_clear"}:
        return

    create_audit_log(
        AuditLog.ACTION_UPDATE,
        instance=instance,
        changes=_build_m2m_change_payload(instance, relation_name, action, pk_set),
        metadata={"relation": relation_name},
    )


def _user_groups_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Audita a associacao de grupos em usuarios."""

    _log_tracked_m2m_change("groups", instance, action, reverse, pk_set)


def _user_permissions_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Audita permissoes individuais aplicadas a usuarios."""

    _log_tracked_m2m_change("user_permissions", instance, action, reverse, pk_set)


def _group_permissions_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Audita permissoes vinculadas a grupos."""

    _log_tracked_m2m_change("permissions", instance, action, reverse, pk_set)


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

    safe_credentials = _sanitize_credentials(credentials)
    identifier = str(
        safe_credentials.get("username")
        or safe_credentials.get("email")
        or safe_credentials.get("identifier")
        or ""
    )
    target_user = None

    if identifier:
        target_user = User._default_manager.filter(username=identifier).first()

    create_audit_log(
        AuditLog.ACTION_LOGIN_FAILED,
        instance=target_user,
        actor_identifier=identifier,
        metadata={"credentials": safe_credentials, "event": "user_login_failed"},
        object_repr=identifier or "Falha de login",
    )


m2m_changed.connect(
    _user_groups_changed,
    sender=User.groups.through,
    dispatch_uid="core.audit.user_groups_changed",
)
m2m_changed.connect(
    _user_permissions_changed,
    sender=User.user_permissions.through,
    dispatch_uid="core.audit.user_permissions_changed",
)
m2m_changed.connect(
    _group_permissions_changed,
    sender=Group.permissions.through,
    dispatch_uid="core.audit.group_permissions_changed",
)
