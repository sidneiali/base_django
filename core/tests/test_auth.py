"""Testes dos fluxos públicos de autenticação."""

from datetime import timedelta
from unittest.mock import patch

from axes.utils import reset  # type: ignore[import-untyped]
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
        self.assertContains(response, "E-mail")

    def test_successful_login_by_email_redirects_to_dashboard_and_creates_audit_entry(
        self,
    ):
        """Login válido por e-mail deve autenticar o usuário e registrar auditoria."""

        user = User.objects.create_user(
            username="lucas",
            email="lucas@example.com",
            password="SenhaSegura@123",
        )
        AuditLog.objects.all().delete()

        response = self.client.post(
            reverse("login"),
            {"username": "lucas@example.com", "password": "SenhaSegura@123"},
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
            {"username": "ana@example.com", "password": "SenhaIncorreta@123"},
        )

        self.assertEqual(response.status_code, 200)

        failed_log = AuditLog.objects.get(action=AuditLog.ACTION_LOGIN_FAILED)
        self.assertEqual(failed_log.object_id, str(user.pk))
        self.assertEqual(failed_log.actor_identifier, "ana@example.com")
        self.assertEqual(failed_log.metadata.get("event"), "user_login_failed")
        self.assertEqual(
            failed_log.metadata["credentials"]["username"],
            "ana@example.com",
        )
        self.assertNotIn("password", failed_log.metadata["credentials"])

    def test_duplicate_email_does_not_authenticate_ambiguously(self):
        """Quando houver mais de um usuário com o mesmo e-mail, o login deve falhar."""

        User.objects.create_user(
            username="duplicado-1",
            email="duplicado@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_user(
            username="duplicado-2",
            email="duplicado@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "duplicado@example.com", "password": "SenhaSegura@123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Por favor, entre com um e-mail e senha corretos.")
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(
    AXES_FAILURE_LIMIT=2,
    AXES_COOLOFF_TIME=timedelta(minutes=5),
)
class LoginLockoutTests(TestCase):
    """Valida o bloqueio temporario do login HTML por IP."""

    def setUp(self):
        """Limpa tentativas anteriores do Axes entre os cenarios."""

        super().setUp()
        reset()

    def tearDown(self):
        """Evita que buckets do Axes vazem para outros testes."""

        reset()
        super().tearDown()

    def test_lockout_reuses_login_template_and_blocks_even_valid_credentials(self):
        """O login precisa travar no proprio HTML apos repetidas falhas."""

        User.objects.create_user(
            username="travado",
            email="travado@example.com",
            password="SenhaSegura@123",
        )
        AuditLog.objects.all().delete()

        first_response = self.client.post(
            reverse("login"),
            {"username": "travado@example.com", "password": "errada"},
        )
        second_response = self.client.post(
            reverse("login"),
            {"username": "travado@example.com", "password": "errada"},
        )
        locked_response = self.client.post(
            reverse("login"),
            {"username": "travado@example.com", "password": "SenhaSegura@123"},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertEqual(locked_response.status_code, 429)
        self.assertContains(
            locked_response,
            "Muitas tentativas de login falharam neste IP",
            status_code=429,
        )
        self.assertContains(
            locked_response,
            "data-teste=\"login-locked-out\"",
            status_code=429,
        )
        self.assertContains(
            locked_response,
            "disabled aria-disabled=\"true\"",
            status_code=429,
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(
            AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN).exists()
        )
        self.assertGreaterEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_FAILED).count(),
            2,
        )


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

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_password_reset_request_enqueues_background_task(self):
        """Com eager desligado, o formulário deve delegar o envio ao Celery."""

        User.objects.create_user(
            username="fila-publica",
            email="fila-publica@example.com",
            password="SenhaSegura@123",
        )

        with patch("core.auth.tasks.send_password_recovery_email_task.delay") as delay:
            response = self.client.post(
                reverse("password_reset"),
                {"email": "fila-publica@example.com"},
            )

        self.assertRedirects(response, reverse("password_reset_done"))
        delay.assert_called_once()
        self.assertEqual(len(mail.outbox), 0)

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
