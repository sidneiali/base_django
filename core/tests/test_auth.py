"""Testes dos fluxos públicos de autenticação."""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.models import AuditLog

User = get_user_model()


class LoginFlowTests(TestCase):
    """Valida o fluxo público de login do sistema."""

    def test_login_page_loads_customized_template(self):
        """A tela de login deve exibir o layout e textos customizados."""

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrar na sua conta")
        self.assertContains(response, "Esqueci minha senha")
        self.assertContains(response, "Sessão autenticada")

    def test_successful_login_redirects_to_dashboard_and_creates_audit_entry(self):
        """Login válido deve autenticar o usuário e registrar auditoria."""

        user = User.objects.create_user(
            username="lucas",
            email="lucas@example.com",
            password="SenhaSegura@123",
        )
        AuditLog.objects.all().delete()

        response = self.client.post(
            reverse("login"),
            {"username": "lucas", "password": "SenhaSegura@123"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(user.pk))

        login_log = AuditLog.objects.get(
            action=AuditLog.ACTION_LOGIN,
            object_id=str(user.pk),
        )
        self.assertEqual(login_log.actor, user)
        self.assertEqual(login_log.metadata.get("event"), "user_logged_in")

    def test_failed_login_creates_sanitized_audit_entry(self):
        """Falha de login deve registrar auditoria sem expor a senha bruta."""

        user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="SenhaSegura@123",
        )
        AuditLog.objects.all().delete()

        response = self.client.post(
            reverse("login"),
            {"username": "ana", "password": "SenhaIncorreta@123"},
        )

        self.assertEqual(response.status_code, 200)

        failed_log = AuditLog.objects.get(action=AuditLog.ACTION_LOGIN_FAILED)
        self.assertEqual(failed_log.object_id, str(user.pk))
        self.assertEqual(failed_log.actor_identifier, "ana")
        self.assertEqual(failed_log.metadata.get("event"), "user_login_failed")
        self.assertEqual(failed_log.metadata["credentials"]["username"], "ana")
        self.assertNotIn("password", failed_log.metadata["credentials"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordRecoveryTests(TestCase):
    """Valida o fluxo externo de recuperacao de senha."""

    def test_password_reset_form_loads(self):
        """A tela publica de recuperar senha precisa abrir normalmente."""

        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Esqueceu sua senha?")

    def test_password_reset_request_sends_email(self):
        """Enviar um e-mail cadastrado deve disparar a mensagem de recuperacao."""

        User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.post(
            reverse("password_reset"),
            {"email": "maria@example.com"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Recuperação de senha", mail.outbox[0].subject)
        self.assertIn("/recuperar-senha/confirmar/", mail.outbox[0].body)

    def test_password_reset_confirm_changes_password(self):
        """O token valido deve redefinir a senha e registrar o evento."""

        user = User.objects.create_user(
            username="carlos",
            email="carlos@example.com",
            password="SenhaSegura@123",
        )
        AuditLog.objects.all().delete()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        confirm_url = reverse("password_reset_confirm", args=[uid, token])

        confirm_response = self.client.get(confirm_url)
        self.assertEqual(confirm_response.status_code, 302)

        response = self.client.post(
            confirm_response["Location"],
            {
                "new_password1": "OutraSenhaSegura@123",
                "new_password2": "OutraSenhaSegura@123",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("OutraSenhaSegura@123"))

        password_log = next(
            (
                log
                for log in AuditLog.objects.filter(
                    action=AuditLog.ACTION_UPDATE,
                    object_id=str(user.pk),
                )
                if log.metadata.get("event") == "password_changed"
            ),
            None,
        )
        self.assertIsNotNone(password_log)
        self.assertEqual(
            password_log.path,
            confirm_response["Location"],
        )
