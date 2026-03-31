"""Testes principais do app core e da infraestrutura de auditoria."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import AuditLog, Module

User = get_user_model()


class AuditLogTests(TestCase):
    """Valida os sinais e eventos da trilha de auditoria."""

    def _build_module(self) -> Module:
        """Cria um modulo valido para os testes de CRUD."""

        return Module.objects.create(
            name="Usuários",
            slug="usuarios",
            description="Gestão de usuários",
            icon="ti ti-users",
            url_name="panel_users_list",
            app_label="auth",
            permission_codename="view_user",
            menu_group="Configurações",
            order=10,
            is_active=True,
        )

    def test_module_crud_generates_audit_logs(self):
        """Cria, altera e exclui modulo gerando eventos distintos."""

        module = self._build_module()
        module_id = str(module.pk)

        create_log = AuditLog.objects.get(
            action=AuditLog.ACTION_CREATE,
            object_id=module_id,
        )
        self.assertEqual(create_log.object_repr, module.name)

        module.description = "Gestão central de usuários"
        module.save()

        update_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_UPDATE,
            object_id=module_id,
        ).first()
        self.assertIsNotNone(update_log)
        self.assertIn("description", update_log.changes)

        module.delete()

        delete_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_DELETE,
            object_id=module_id,
        ).first()
        self.assertIsNotNone(delete_log)
        self.assertEqual(delete_log.before["name"], "Usuários")

    def test_group_membership_changes_are_logged(self):
        """Registra alteracoes de grupos em usuarios como update."""

        user = User.objects.create_user(username="maria", password="senha-forte")
        group = Group.objects.create(name="Equipe")
        AuditLog.objects.all().delete()

        user.groups.add(group)

        log = AuditLog.objects.get(action=AuditLog.ACTION_UPDATE)
        self.assertEqual(log.object_id, str(user.pk))
        self.assertEqual(log.changes["groups"]["operation"], "post_add")
        self.assertEqual(
            log.changes["groups"]["changed_items"],
            [{"id": str(group.pk), "repr": group.name}],
        )

    def test_authentication_events_are_logged(self):
        """Loga login, logout e falha de login no banco de auditoria."""

        user = User.objects.create_user(username="ana", password="senha-forte")
        AuditLog.objects.all().delete()

        login_response = self.client.post(
            reverse("login"),
            {"username": "ana", "password": "senha-forte"},
        )
        self.assertEqual(login_response.status_code, 302)

        logout_response = self.client.post(reverse("logout"))
        self.assertEqual(logout_response.status_code, 302)

        failed_login_response = self.client.post(
            reverse("login"),
            {"username": "ana", "password": "senha-incorreta"},
        )
        self.assertEqual(failed_login_response.status_code, 200)

        actions = list(
            AuditLog.objects.order_by("created_at", "id").values_list("action", flat=True)
        )
        self.assertIn(AuditLog.ACTION_LOGIN, actions)
        self.assertIn(AuditLog.ACTION_LOGOUT, actions)
        self.assertIn(AuditLog.ACTION_LOGIN_FAILED, actions)

        failed_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN_FAILED
        ).first()
        self.assertIsNotNone(failed_log)
        self.assertEqual(failed_log.actor_identifier, user.username)


class UserAdminTests(TestCase):
    """Garante compatibilidade do admin customizado com o Django 6."""

    def test_admin_user_add_view_loads(self):
        """A tela de criação de usuário no admin precisa abrir sem FieldError."""

        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="senha-forte",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:auth_user_add"))

        self.assertEqual(response.status_code, 200)


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
