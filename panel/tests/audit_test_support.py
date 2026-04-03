"""Apoio compartilhado para cenários HTML e E2E da auditoria do painel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from core.models import AuditLog
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@dataclass(frozen=True, slots=True)
class RelatedAuditScenario:
    """Agrupa o cenário recorrente de eventos relacionados da auditoria."""

    target_log: AuditLog
    actor_related_log: AuditLog
    request_related_log: AuditLog
    unrelated_log: AuditLog | None = None


class AuditTestDataFactory:
    """Factory pequena para reduzir setup repetido nos cenários de auditoria."""

    def __init__(
        self,
        *,
        default_password: str = "SenhaSegura@123",
        default_object_verbose_name: str = "Evento",
        default_request_method: str = "GET",
        default_path: str = "/painel/auditoria/",
    ) -> None:
        self.default_password = default_password
        self.default_object_verbose_name = default_object_verbose_name
        self.default_request_method = default_request_method
        self.default_path = default_path

    def create_actor(
        self,
        username: str,
        *,
        email: str | None = None,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
    ) -> Any:
        """Cria um ator previsível para cenários de auditoria."""

        return User.objects.create_user(
            username=username,
            email=email or f"{username}@example.com",
            password=password or self.default_password,
            first_name=first_name,
            last_name=last_name,
        )

    def create_log(
        self,
        *,
        action: str,
        actor_identifier: str,
        object_repr: str,
        request_id: str,
        actor: Any | None = None,
        created_at: datetime | None = None,
        object_verbose_name: str | None = None,
        request_method: str | None = None,
        path: str | None = None,
        object_id: str = "",
        ip_address: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Cria um log de auditoria com defaults consistentes para os testes."""

        payload_metadata = {"request_id": request_id}
        if metadata:
            payload_metadata.update(metadata)

        audit_log = AuditLog.objects.create(
            action=action,
            actor=actor,
            actor_identifier=actor_identifier,
            object_repr=object_repr,
            object_verbose_name=object_verbose_name or self.default_object_verbose_name,
            object_id=object_id,
            request_method=request_method or self.default_request_method,
            path=path or self.default_path,
            ip_address=ip_address,
            before={} if before is None else before,
            after={} if after is None else after,
            changes={} if changes is None else changes,
            metadata=payload_metadata,
        )

        if created_at is not None:
            AuditLog.objects.filter(pk=audit_log.pk).update(created_at=created_at)
            audit_log.refresh_from_db()

        return audit_log

    def create_related_scenario(
        self,
        *,
        actor: Any,
        actor_identifier: str,
        other_actor: Any,
        other_actor_identifier: str,
        target_object_repr: str,
        request_id: str,
        actor_related_object_repr: str,
        actor_related_request_id: str,
        request_related_object_repr: str,
        unrelated_object_repr: str | None = None,
        target_action: str = AuditLog.ACTION_UPDATE,
        actor_related_action: str = AuditLog.ACTION_LOGIN,
        request_related_action: str = AuditLog.ACTION_DELETE,
        unrelated_action: str = AuditLog.ACTION_LOGIN_FAILED,
        unrelated_request_id: str = "req-unrelated",
        now: datetime | None = None,
    ) -> RelatedAuditScenario:
        """Cria o bundle recorrente de previews e atalhos relacionados."""

        base_time = now or timezone.now()
        target_log = self.create_log(
            action=target_action,
            actor=actor,
            actor_identifier=actor_identifier,
            object_repr=target_object_repr,
            request_id=request_id,
            created_at=base_time,
        )
        actor_related_log = self.create_log(
            action=actor_related_action,
            actor=actor,
            actor_identifier=actor_identifier,
            object_repr=actor_related_object_repr,
            request_id=actor_related_request_id,
            created_at=base_time - timedelta(minutes=1),
        )
        request_related_log = self.create_log(
            action=request_related_action,
            actor=other_actor,
            actor_identifier=other_actor_identifier,
            object_repr=request_related_object_repr,
            request_id=request_id,
            created_at=base_time - timedelta(minutes=2),
        )

        unrelated_log = None
        if unrelated_object_repr is not None:
            unrelated_log = self.create_log(
                action=unrelated_action,
                actor=other_actor,
                actor_identifier=other_actor_identifier,
                object_repr=unrelated_object_repr,
                request_id=unrelated_request_id,
                created_at=base_time - timedelta(minutes=3),
            )

        return RelatedAuditScenario(
            target_log=target_log,
            actor_related_log=actor_related_log,
            request_related_log=request_related_log,
            unrelated_log=unrelated_log,
        )
