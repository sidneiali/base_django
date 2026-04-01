"""Testes das páginas da conta autenticada."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import ApiAccessProfile, ApiToken, AuditLog

User = get_user_model()


class AccountPasswordChangeTests(TestCase):
    """Valida a tela de troca da propria senha pelo usuario logado."""

    def test_login_is_required(self):
        """A pagina deve redirecionar anonimos para o login."""

        response = self.client.get(reverse("account_password_change"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_password_change_updates_password_and_creates_audit_entry(self):
        """Troca a senha e registra o evento como alteracao de senha."""

        user = User.objects.create_user(
            username="joao",
            email="joao@example.com",
            password="senha-antiga-forte",
        )
        self.client.force_login(user)
        AuditLog.objects.all().delete()

        response = self.client.post(
            reverse("account_password_change"),
            {
                "old_password": "senha-antiga-forte",
                "new_password1": "NovaSenhaForte@123",
                "new_password2": "NovaSenhaForte@123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("account_password_change"))

        user.refresh_from_db()
        self.assertTrue(user.check_password("NovaSenhaForte@123"))

        password_logs = [
            log
            for log in AuditLog.objects.filter(
                action=AuditLog.ACTION_UPDATE,
                object_id=str(user.pk),
            )
            if log.metadata.get("event") == "password_changed"
        ]
        self.assertTrue(password_logs)
        self.assertEqual(password_logs[0].path, reverse("account_password_change"))

    def test_account_page_can_issue_api_token_when_access_is_enabled(self):
        """O usuario deve conseguir gerar o proprio token quando a API estiver habilitada."""

        user = User.objects.create_user(
            username="apiowner",
            email="apiowner@example.com",
            password="SenhaSegura@123",
        )
        ApiAccessProfile.objects.create(user=user, api_enabled=True)
        self.client.force_login(user)

        response = self.client.post(
            reverse("account_password_change"),
            {"action": "issue_api_token"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        token = ApiToken.objects.get(user=user)
        self.assertTrue(token.is_active)
        self.assertContains(response, "Copie este token agora")
        self.assertContains(response, "Copiar token")
        self.assertContains(response, reverse("api_docs"))

    def test_account_page_can_revoke_api_token(self):
        """O usuario deve conseguir revogar o proprio token ativo."""

        user = User.objects.create_user(
            username="revoga",
            email="revoga@example.com",
            password="SenhaSegura@123",
        )
        ApiAccessProfile.objects.create(user=user, api_enabled=True)
        token, _raw_token = ApiToken.issue_for_user(user)
        self.client.force_login(user)

        response = self.client.post(
            reverse("account_password_change"),
            {"action": "revoke_api_token"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertFalse(token.is_active)
        self.assertContains(response, "Seu token da API foi revogado.")
