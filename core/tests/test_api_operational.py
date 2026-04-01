"""Testes operacionais e de segurança da API do app core."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken, AuditLog

User = get_user_model()


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
