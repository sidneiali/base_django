"""Testes dos endpoints de acesso e documentação da API."""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken, AuditLog

User = get_user_model()


class ApiDocsTests(TestCase):
    """Valida as superfícies públicas de documentação da API."""

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

    def _issue_token(self, *, can_read: bool = True) -> tuple[object, str]:
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
