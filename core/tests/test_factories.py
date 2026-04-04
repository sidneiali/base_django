"""Testes de baixo nível das factories compartilhadas."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from core.tests.factories import (
    AuditLogFactory,
    GroupFactory,
    ModuleFactory,
    UserFactory,
)


class SharedFactoriesTests(TestCase):
    """Garante o contrato básico das factories reutilizadas pelo projeto."""

    def test_user_factory_hashes_password_and_links_groups_and_permissions(self) -> None:
        """A factory de usuário deve persistir senha usável e relacionamentos."""

        group = GroupFactory.create(name="Operacao")
        permission = Permission.objects.get(codename="view_user")

        user = UserFactory.create(
            username="factory-user",
            password="SenhaNova@123",
            groups=[group],
            user_permissions=[permission],
        )

        self.assertTrue(user.check_password("SenhaNova@123"))
        self.assertTrue(user.groups.filter(pk=group.pk).exists())
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())

    def test_audit_log_factory_allows_created_at_override_and_request_id_metadata(self) -> None:
        """A factory de auditoria deve preservar request_id e sobrescrever `created_at`."""

        expected_created_at = timezone.now() - timedelta(days=1)

        audit_log = AuditLogFactory.create(
            actor=None,
            actor_identifier="factory-auditor",
            request_id="req-factory",
            created_at=expected_created_at,
        )

        self.assertEqual(audit_log.metadata["request_id"], "req-factory")
        self.assertEqual(audit_log.created_at, expected_created_at)

    def test_module_factory_generates_unique_defaults(self) -> None:
        """A factory de módulo deve gerar nomes e slugs distintos sem boilerplate."""

        first_module = ModuleFactory.create()
        second_module = ModuleFactory.create()

        self.assertNotEqual(first_module.name, second_module.name)
        self.assertNotEqual(first_module.slug, second_module.slug)
