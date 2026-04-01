"""Testes principais do app core e da infraestrutura de auditoria."""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import (ApiAccessProfile, ApiResourcePermission, ApiToken,
                     AuditLog, Module)

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


class ApiAccessModelTests(TestCase):
    """Valida a camada inicial de acesso e token da API."""

    def test_api_token_issue_stores_only_hash_and_redacts_audit_log(self):
        """Emitir um token deve persistir apenas o hash e mascarar o log."""

        user = User.objects.create_user(username="api-user", password="senha-forte")
        AuditLog.objects.all().delete()

        token, raw_token = ApiToken.issue_for_user(user)

        self.assertNotEqual(raw_token, token.token_hash)
        self.assertEqual(token.token_prefix, raw_token[: ApiToken.PREFIX_LENGTH])
        self.assertTrue(token.matches(raw_token))
        self.assertTrue(token.is_active)

        create_log = AuditLog.objects.get(
            action=AuditLog.ACTION_CREATE,
            content_type__app_label="core",
            content_type__model="apitoken",
            object_id=str(token.pk),
        )
        self.assertEqual(create_log.after["token_hash"], "[redacted]")
        self.assertEqual(
            create_log.changes["token_hash"]["after"],
            "[redacted]",
        )

    def test_api_resource_permission_maps_crud_actions(self):
        """As flags CRUD precisam refletir corretamente a autorizacao final."""

        user = User.objects.create_user(username="carol", password="senha-forte")
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        permission = ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.PANEL_USERS,
            can_read=True,
            can_update=True,
        )

        self.assertTrue(permission.has_any_permission())
        self.assertFalse(permission.allows("create"))
        self.assertTrue(permission.allows("read"))
        self.assertTrue(permission.allows("update"))
        self.assertFalse(permission.allows("delete"))


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

    def test_api_docs_page_is_public(self):
        """A documentação pública da API deve abrir sem autenticação."""

        response = self.client.get(reverse("api_docs"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Swagger da API")
        self.assertContains(response, "curl")
        self.assertContains(response, "Python")
        self.assertNotContains(response, ">Postman<", html=False)
        self.assertContains(response, reverse("api_docs_postman"))
        self.assertContains(response, "/api/panel/users/&lt;id&gt;/")

    def test_api_docs_postman_download_is_public(self):
        """A coleção Postman deve estar disponível para download público."""

        response = self.client.get(reverse("api_docs_postman"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])

        collection = json.loads(response.content)
        self.assertEqual(collection["info"]["name"], "BaseApp API")
        self.assertEqual(collection["variable"][1]["key"], "token")


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
