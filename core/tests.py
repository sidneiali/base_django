"""Testes principais do app core e da infraestrutura de auditoria."""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core import mail
from django.utils import timezone
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .api.access import get_user_api_access_values
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

    def test_api_access_values_ignore_legacy_resources(self):
        """Recursos antigos sem endpoint não devem quebrar a matriz atual."""

        user = User.objects.create_user(username="legacy-api", password="senha-forte")
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource="panel.groups",
            can_read=True,
        )

        values = get_user_api_access_values(user)

        self.assertTrue(values["api_enabled"])
        self.assertIn(ApiResourcePermission.Resource.PANEL_USERS, values["permissions"])
        self.assertIn(ApiResourcePermission.Resource.CORE_API_ACCESS, values["permissions"])
        self.assertIn(
            ApiResourcePermission.Resource.CORE_AUDIT_LOGS,
            values["permissions"],
        )


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
        self.assertContains(response, reverse("api_v1_openapi"))
        self.assertContains(response, "/api/v1/core/health/")
        self.assertContains(response, "/api/v1/core/me/")
        self.assertContains(response, "/api/v1/core/token/")
        self.assertContains(response, "/api/v1/panel/users/{id}/")
        self.assertContains(response, "/api/v1/core/audit-logs/{id}/")
        self.assertContains(response, "Authorization: Bearer SEU_TOKEN")
        self.assertContains(response, "X-Request-ID")
        self.assertContains(response, "invalid_token")
        self.assertContains(response, "forbidden")
        self.assertContains(response, "rate_limited")
        self.assertContains(response, "python scripts/api_request.py --help")
        self.assertContains(response, "python scripts/api_request.py --list-routes")
        self.assertContains(response, 'id="api-tabs-curl"', html=False)
        self.assertContains(response, 'id="api-tabs-python"', html=False)
        self.assertContains(response, 'id="api-tabs-postman"', html=False)
        self.assertContains(response, 'data-endpoint-link="api-health"', html=False)
        self.assertContains(response, 'data-endpoint-link="api-me"', html=False)
        self.assertContains(response, 'data-endpoint-link="api-users-list"', html=False)

    def test_openapi_json_is_public_and_versioned(self):
        """A spec pública deve expor os paths versionados da API."""

        response = self.client.get(reverse("api_openapi"))

        self.assertEqual(response.status_code, 200)
        schema = json.loads(response.content)
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertEqual(schema["info"]["title"], "BaseApp API")
        self.assertIn("/api/v1/core/health/", schema["paths"])
        self.assertIn("/api/v1/core/me/", schema["paths"])
        self.assertIn("/api/v1/panel/users/", schema["paths"])
        self.assertIn("/api/v1/core/audit-logs/{id}/", schema["paths"])
        self.assertEqual(schema["servers"][0]["url"], "http://testserver")

    def test_api_docs_postman_download_is_public(self):
        """A coleção Postman deve estar disponível para download público."""

        response = self.client.get(reverse("api_docs_postman"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])

        collection = json.loads(response.content)
        self.assertEqual(collection["info"]["name"], "BaseApp API")
        self.assertEqual(collection["variable"][1]["key"], "token")
        self.assertEqual(collection["variable"][3]["key"], "audit_log_id")
        self.assertEqual(collection["item"][0]["name"], "Operacional")
        self.assertEqual(collection["item"][1]["name"], "Acesso à API")
        self.assertEqual(collection["item"][3]["name"], "Logs de auditoria")


class AuditLogApiTests(TestCase):
    """Valida os endpoints Bearer para leitura dos logs de auditoria."""

    def _issue_token(self, *, can_read: bool = True) -> str:
        """Cria um usuário com acesso habilitado ao recurso de auditoria."""

        user = User.objects.create_user(
            username="audit-api",
            email="audit-api@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.CORE_AUDIT_LOGS,
            can_read=can_read,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return raw_token

    def test_audit_logs_collection_requires_read_permission(self):
        """A listagem deve bloquear tokens sem leitura do recurso."""

        raw_token = self._issue_token(can_read=False)

        response = self.client.get(
            reverse("api_core_audit_logs_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_audit_logs_collection_lists_and_filters_events(self):
        """A listagem deve aceitar filtros simples por ação e ator."""

        actor = User.objects.create_user(username="auditor", password="SenhaSegura@123")
        AuditLog.objects.all().delete()
        create_log = AuditLog.objects.create(
            actor=actor,
            actor_identifier=actor.username,
            action=AuditLog.ACTION_CREATE,
            object_id="10",
            object_repr="maria",
            object_verbose_name="usuário",
            request_method="POST",
            path="/painel/usuarios/novo/",
            created_at=timezone.now(),
        )
        AuditLog.objects.create(
            actor_identifier="cli",
            action=AuditLog.ACTION_DELETE,
            object_id="11",
            object_repr="grupo antigo",
            object_verbose_name="grupo",
            request_method="DELETE",
            path="/painel/grupos/11/excluir/",
            created_at=timezone.now(),
        )
        raw_token = self._issue_token()

        response = self.client.get(
            reverse("api_core_audit_logs_collection"),
            {
                "action": AuditLog.ACTION_CREATE,
                "actor": actor.username,
                "page_size": 10,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 1)
        self.assertEqual(payload["meta"]["pagination"]["page"], 1)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 10)
        self.assertEqual(payload["meta"]["filters"]["action"], AuditLog.ACTION_CREATE)
        self.assertEqual(payload["meta"]["filters"]["actor"], actor.username)
        self.assertEqual(payload["meta"]["ordering"], "-created_at")
        self.assertEqual(payload["data"][0]["id"], create_log.pk)
        self.assertEqual(payload["data"][0]["actor"]["username"], actor.username)

    def test_audit_logs_collection_supports_ordering_and_page_errors(self):
        """A listagem deve validar ordering e páginas fora do intervalo."""

        raw_token = self._issue_token()
        AuditLog.objects.all().delete()
        AuditLog.objects.create(
            actor_identifier="bbb",
            action=AuditLog.ACTION_CREATE,
            object_id="1",
            object_repr="segundo",
            object_verbose_name="usuário",
            request_method="POST",
            path="/a/",
        )
        AuditLog.objects.create(
            actor_identifier="aaa",
            action=AuditLog.ACTION_UPDATE,
            object_id="2",
            object_repr="primeiro",
            object_verbose_name="usuário",
            request_method="POST",
            path="/b/",
        )

        ordered_response = self.client.get(
            reverse("api_core_audit_logs_collection"),
            {"ordering": "actor", "page_size": 1},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(ordered_response.status_code, 200)
        ordered_payload = ordered_response.json()
        self.assertEqual(ordered_payload["meta"]["ordering"], "actor")
        self.assertEqual(ordered_payload["meta"]["pagination"]["total_pages"], 2)
        self.assertEqual(ordered_payload["data"][0]["actor_identifier"], "aaa")

        invalid_page_response = self.client.get(
            reverse("api_core_audit_logs_collection"),
            {"page": 5, "page_size": 1},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(invalid_page_response.status_code, 400)
        self.assertEqual(
            invalid_page_response.json()["error"]["code"],
            "page_out_of_range",
        )

    def test_audit_log_detail_returns_full_payload(self):
        """O detalhe deve expor os campos before/after/changes/metadata."""

        raw_token = self._issue_token()
        audit_log = AuditLog.objects.create(
            actor_identifier="admin",
            action=AuditLog.ACTION_UPDATE,
            object_id="7",
            object_repr="joao",
            object_verbose_name="usuário",
            before={"email": "antes@example.com"},
            after={"email": "depois@example.com"},
            changes={"email": {"before": "antes@example.com", "after": "depois@example.com"}},
            metadata={"event": "manual_update"},
            path="/painel/usuarios/7/editar/",
            request_method="POST",
        )

        response = self.client.get(
            reverse("api_core_audit_log_detail", args=[audit_log.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["id"], audit_log.pk)
        self.assertEqual(payload["data"]["before"]["email"], "antes@example.com")
        self.assertEqual(payload["data"]["after"]["email"], "depois@example.com")
        self.assertEqual(payload["data"]["metadata"]["event"], "manual_update")


class ApiAccessEndpointsTests(TestCase):
    """Valida os endpoints de introspecção da conta e do token atuais."""

    def _issue_token(self, *, can_read: bool = True) -> tuple[User, str]:
        """Cria um usuário com acesso habilitado ao recurso de introspecção."""

        user = User.objects.create_user(
            username="self-api",
            email="self-api@example.com",
            password="SenhaSegura@123",
            first_name="Self",
            last_name="Api",
        )
        group = Group.objects.create(name="Integrações")
        user.groups.add(group)
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.CORE_API_ACCESS,
            can_read=can_read,
        )
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.CORE_AUDIT_LOGS,
            can_read=True,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return user, raw_token

    def test_me_requires_api_access_permission(self):
        """A conta atual também precisa respeitar a permissão de leitura."""

        _user, raw_token = self._issue_token(can_read=False)

        response = self.client.get(
            reverse("api_core_me"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_me_returns_authenticated_user_payload(self):
        """O endpoint /me deve devolver a identidade do usuário autenticado."""

        user, raw_token = self._issue_token()

        response = self.client.get(
            reverse("api_core_me"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["id"], user.pk)
        self.assertEqual(payload["data"]["username"], user.username)
        self.assertEqual(payload["data"]["email"], user.email)
        self.assertEqual(payload["data"]["groups"][0]["name"], "Integrações")
        self.assertEqual(payload["meta"]["version"], "v1")

    def test_token_status_returns_current_token_and_permissions(self):
        """O endpoint /token deve expor o status do token atual e os acessos."""

        user, raw_token = self._issue_token()

        response = self.client.get(
            reverse("api_core_token"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["data"]["api_enabled"])
        self.assertEqual(
            payload["data"]["token"]["token_prefix"],
            raw_token[: ApiToken.PREFIX_LENGTH],
        )
        permissions = {item["resource"]: item for item in payload["data"]["permissions"]}
        self.assertTrue(permissions[ApiResourcePermission.Resource.CORE_API_ACCESS]["can_read"])
        self.assertFalse(permissions[ApiResourcePermission.Resource.CORE_API_ACCESS]["can_create"])
        self.assertEqual(user.username, "self-api")


@override_settings(API_RATE_LIMIT_REQUESTS=1, API_RATE_LIMIT_WINDOW_SECONDS=60)
class ApiOperationalSecurityTests(TestCase):
    """Valida health check, rate limit e trilha de falhas da API."""

    def setUp(self):
        """Limpa o cache antes de cada cenário de rate limit."""

        super().setUp()
        cache.clear()

    def tearDown(self):
        """Evita que buckets de teste vazem para outros cenários."""

        cache.clear()
        super().tearDown()

    def _issue_token(self) -> str:
        """Cria um token com leitura do recurso de introspecção."""

        user = User.objects.create_user(
            username="operacao-api",
            email="operacao-api@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=ApiResourcePermission.Resource.CORE_API_ACCESS,
            can_read=True,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return raw_token

    def test_health_endpoint_is_public(self):
        """O health check deve responder sem autenticação."""

        response = self.client.get(reverse("api_core_health"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response)
        payload = response.json()
        self.assertEqual(payload["data"]["status"], "ok")
        self.assertTrue(payload["data"]["timestamp"].endswith("-03:00"))
        self.assertTrue(payload["data"]["rate_limit"]["enabled"])
        self.assertEqual(payload["meta"]["request_id"], response["X-Request-ID"])

    def test_invalid_token_attempt_is_logged(self):
        """Token inválido deve gerar 401 e log de acesso negado."""

        AuditLog.objects.all().delete()

        response = self.client.get(
            reverse("api_core_me"),
            HTTP_AUTHORIZATION="Bearer token-invalido",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "invalid_token")
        self.assertIn("X-Request-ID", response)

        log = AuditLog.objects.filter(action=AuditLog.ACTION_API_ACCESS_DENIED).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata["reason_code"], "invalid_token")
        self.assertEqual(log.metadata["resource"], "core.api_access")
        self.assertEqual(log.metadata["request_id"], response["X-Request-ID"])

    def test_rate_limit_blocks_second_request_and_logs_event(self):
        """A segunda chamada no mesmo bucket deve retornar 429."""

        raw_token = self._issue_token()
        AuditLog.objects.all().delete()

        first_response = self.client.get(
            reverse("api_core_me"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        second_response = self.client.get(
            reverse("api_core_me"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertEqual(second_response.json()["error"]["code"], "rate_limited")
        self.assertEqual(second_response["Retry-After"], "60")
        self.assertEqual(second_response["X-RateLimit-Limit"], "1")
        self.assertIn("X-Request-ID", second_response)

        log = AuditLog.objects.filter(action=AuditLog.ACTION_RATE_LIMITED).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata["event"], "api_rate_limited")
        self.assertEqual(log.metadata["path"], reverse("api_core_me"))
        self.assertEqual(log.metadata["request_id"], second_response["X-Request-ID"])


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
