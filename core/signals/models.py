"""Sinais de modelo usados para criar eventos de auditoria."""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from ..audit import build_changes, build_instance_snapshot, create_audit_log
from ..models import AuditLog
from .shared import is_tracked_model


@receiver(pre_save, dispatch_uid="core.audit.capture_pre_save_state")
def capture_pre_save_state(sender, instance, raw=False, **kwargs):
    """Captura o estado atual do objeto antes da persistencia."""

    if raw or not is_tracked_model(sender):
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

    if raw or not is_tracked_model(sender):
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

    if not is_tracked_model(sender):
        return

    before_state, _ = build_instance_snapshot(instance)
    instance._audit_before_delete_state = before_state
    instance._audit_before_delete_object_id = str(instance.pk)


@receiver(post_delete, dispatch_uid="core.audit.log_deleted_instance")
def log_deleted_instance(sender, instance, **kwargs):
    """Registra exclusoes em models monitorados."""

    if not is_tracked_model(sender):
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
