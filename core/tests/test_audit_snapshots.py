"""Testes unitarios dos snapshots e diffs de auditoria."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import cast
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Model
from django.test import SimpleTestCase

from core.audit.snapshots import build_changes, build_instance_snapshot

User = get_user_model()


class _FakeField:
    """Imita a interface minima de um field concreto do Django."""

    def __init__(self, name: str) -> None:
        self.name = name

    def value_from_object(self, instance: object) -> object:
        return getattr(instance, self.name)


class _FakeMeta:
    """Agrupa label e concrete_fields usados pelo serializer."""

    def __init__(self, label_lower: str, field_names: list[str]) -> None:
        self.label_lower = label_lower
        self.concrete_fields = [_FakeField(name) for name in field_names]


class _FakeModel:
    """Model fake suficiente para exercitar o snapshot sem banco."""

    def __init__(self, label_lower: str, **values: object) -> None:
        self._meta = _FakeMeta(label_lower, list(values))
        for name, value in values.items():
            setattr(self, name, value)


class AuditSnapshotTests(SimpleTestCase):
    """Valida serializacao estavel e mascaramento de snapshots."""

    def test_build_instance_snapshot_serializes_supported_value_types(self) -> None:
        """Datas, decimais, UUIDs, arquivos e relacionamentos viram JSON estavel."""

        upload = SimpleUploadedFile("reports/fechamento.csv", b"id,total\n1,10")
        instance = _FakeModel(
            "tests.snapshotcarrier",
            happened_on=date(2026, 4, 4),
            happened_at=datetime(2026, 4, 4, 15, 30, 45, tzinfo=timezone.utc),
            reminder_at=time(9, 45, 1),
            total=Decimal("19.90"),
            reference_uuid=UUID("8df6d810-89e7-4e86-ae57-b0a8c6c6a6da"),
            attachment=upload,
            storage_path=PurePosixPath("media/reports/2026/fechamento.csv"),
            owner=SimpleNamespace(pk=7),
            metadata={"attempts": 2, "labels": {"a", "b"}},
        )

        serialized, comparison = build_instance_snapshot(cast(Model, instance))

        self.assertEqual(serialized["happened_on"], "2026-04-04")
        self.assertEqual(serialized["happened_at"], "2026-04-04T15:30:45+00:00")
        self.assertEqual(serialized["reminder_at"], "09:45:01")
        self.assertEqual(serialized["total"], "19.90")
        self.assertEqual(
            serialized["reference_uuid"],
            "8df6d810-89e7-4e86-ae57-b0a8c6c6a6da",
        )
        self.assertEqual(serialized["attachment"], str(upload))
        self.assertEqual(
            serialized["storage_path"],
            "media/reports/2026/fechamento.csv",
        )
        self.assertEqual(serialized["owner"], "7")
        metadata = cast(dict[str, object], comparison["metadata"])

        self.assertEqual(metadata["attempts"], 2)
        self.assertCountEqual(cast(list[str], metadata["labels"]), ["a", "b"])

    def test_build_instance_snapshot_masks_sensitive_fields_and_skips_exclusions(
        self,
    ) -> None:
        """Campos sensiveis devem ser mascarados e exclusoes respeitadas."""

        user = User(username="ana", email="ana@example.com")
        user.set_password("SenhaSegura@123")
        user.last_login = datetime(2026, 4, 4, 18, 0, tzinfo=timezone.utc)

        serialized, comparison = build_instance_snapshot(user)

        self.assertNotIn("last_login", serialized)
        self.assertNotIn("last_login", comparison)
        self.assertEqual(serialized["password"], "[redacted]")
        self.assertEqual(comparison["password"], user.password)

        token_holder = _FakeModel(
            "tests.tokenholder",
            token_hash="hash-super-secreto",
            description="token de integracao",
        )
        token_serialized, token_comparison = build_instance_snapshot(
            cast(Model, token_holder)
        )

        self.assertEqual(token_serialized["token_hash"], "[redacted]")
        self.assertEqual(token_comparison["token_hash"], "hash-super-secreto")

    def test_build_changes_uses_comparison_values_but_keeps_redacted_payloads(
        self,
    ) -> None:
        """Differences devem usar a comparacao interna sem vazar segredos."""

        before_state: dict[str, object] = {
            "password": "[redacted]",
            "email": "ana@example.com",
            "status": "active",
        }
        after_state: dict[str, object] = {
            "password": "[redacted]",
            "email": "ana+novo@example.com",
            "status": "active",
        }
        before_comparison: dict[str, object] = {
            "password": "hash-antigo",
            "email": "ana@example.com",
            "status": "active",
        }
        after_comparison: dict[str, object] = {
            "password": "hash-novo",
            "email": "ana+novo@example.com",
            "status": "active",
        }

        changes = build_changes(
            before_state,
            after_state,
            before_comparison,
            after_comparison,
        )

        self.assertEqual(
            changes,
            {
                "email": {
                    "before": "ana@example.com",
                    "after": "ana+novo@example.com",
                },
                "password": {
                    "before": "[redacted]",
                    "after": "[redacted]",
                },
            },
        )
