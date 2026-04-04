"""Testes da expiração de sessão por inatividade."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import GroupInterfacePreference, UserInterfacePreference

User = get_user_model()


class SessionIdleTimeoutTests(TestCase):
    """Garante a resolução da janela de sessão entre usuário e grupos."""

    def _assert_session_expiry_seconds(self, expected_seconds: int) -> None:
        """Valida a janela de expiração com pequena tolerância de execução."""

        expiry_age = int(self.client.session.get_expiry_age())
        self.assertGreaterEqual(expiry_age, expected_seconds - 5)
        self.assertLessEqual(expiry_age, expected_seconds)

    def test_user_specific_session_timeout_is_applied_to_authenticated_session(
        self,
    ) -> None:
        """A política do usuário deve definir a sessão quando existir."""

        user = User.objects.create_user(
            username="sessao-user",
            email="sessao-user@example.com",
            password="SenhaSegura@123",
        )
        UserInterfacePreference.objects.create(
            user=user,
            session_idle_timeout_minutes=45,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("account_password_change"))

        self.assertEqual(response.status_code, 200)
        self._assert_session_expiry_seconds(45 * 60)

    def test_group_session_timeout_is_applied_when_user_has_no_specific_value(
        self,
    ) -> None:
        """A política do grupo deve ser usada quando o usuário não tiver valor próprio."""

        group = Group.objects.create(name="Atendimento")
        GroupInterfacePreference.objects.create(
            group=group,
            session_idle_timeout_minutes=20,
        )
        user = User.objects.create_user(
            username="sessao-grupo",
            email="sessao-grupo@example.com",
            password="SenhaSegura@123",
        )
        user.groups.add(group)
        self.client.force_login(user)

        response = self.client.get(reverse("account_password_change"))

        self.assertEqual(response.status_code, 200)
        self._assert_session_expiry_seconds(20 * 60)

    def test_smallest_timeout_between_user_and_groups_wins(self) -> None:
        """Quando houver múltiplas regras, a menor janela configurada prevalece."""

        support_group = Group.objects.create(name="Suporte")
        operations_group = Group.objects.create(name="Operações")
        GroupInterfacePreference.objects.create(
            group=support_group,
            session_idle_timeout_minutes=25,
        )
        GroupInterfacePreference.objects.create(
            group=operations_group,
            session_idle_timeout_minutes=15,
        )
        user = User.objects.create_user(
            username="sessao-mista",
            email="sessao-mista@example.com",
            password="SenhaSegura@123",
        )
        user.groups.add(support_group, operations_group)
        UserInterfacePreference.objects.create(
            user=user,
            session_idle_timeout_minutes=30,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("account_password_change"))

        self.assertEqual(response.status_code, 200)
        self._assert_session_expiry_seconds(15 * 60)
