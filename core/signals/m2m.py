"""Sinais many-to-many auditados pelo app core."""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth.models import Group
from django.db.models import Model
from django.db.models.signals import m2m_changed

from ..audit import create_audit_log
from ..models import AuditLog
from .shared import User, build_m2m_change_payload

user_model = cast(Any, User)


def log_tracked_m2m_change(
    relation_name: str,
    instance: Model,
    action: str,
    reverse: bool,
    pk_set,
):
    """Registra alteracoes relevantes de relacionamentos M2M."""

    if reverse or action not in {"post_add", "post_remove", "post_clear"}:
        return

    create_audit_log(
        AuditLog.ACTION_UPDATE,
        instance=instance,
        changes=build_m2m_change_payload(instance, relation_name, action, pk_set),
        metadata={"relation": relation_name},
    )


def user_groups_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Audita a associacao de grupos em usuarios."""

    log_tracked_m2m_change("groups", instance, action, reverse, pk_set)


def user_permissions_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Audita permissoes individuais aplicadas a usuarios."""

    log_tracked_m2m_change("user_permissions", instance, action, reverse, pk_set)


def group_permissions_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Audita permissoes vinculadas a grupos."""

    log_tracked_m2m_change("permissions", instance, action, reverse, pk_set)


m2m_changed.connect(
    user_groups_changed,
    sender=user_model.groups.through,
    dispatch_uid="core.audit.user_groups_changed",
)
m2m_changed.connect(
    user_permissions_changed,
    sender=user_model.user_permissions.through,
    dispatch_uid="core.audit.user_permissions_changed",
)
m2m_changed.connect(
    group_permissions_changed,
    sender=Group.permissions.through,
    dispatch_uid="core.audit.group_permissions_changed",
)
