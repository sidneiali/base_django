"""Testes unitários do serviço de rate limit da API."""

from __future__ import annotations

from types import SimpleNamespace

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from core.services.rate_limit_service import (
    build_rate_limit_identifier,
    consume_rate_limit_slot,
    get_rate_limit_config,
)


class RateLimitIdentifierTests(SimpleTestCase):
    """Valida o identificador usado para os buckets da API."""

    def test_identifier_prefers_authenticated_token(self) -> None:
        """Quando houver token autenticado, o bucket deve usar o token."""

        request = SimpleNamespace(
            META={
                "HTTP_X_FORWARDED_FOR": "203.0.113.9",
                "REMOTE_ADDR": "127.0.0.1",
            },
            api_auth_result=SimpleNamespace(
                is_authenticated=True,
                token=SimpleNamespace(pk=7),
            ),
        )

        self.assertEqual(build_rate_limit_identifier(request), "token:7")

    def test_identifier_prefers_forwarded_for_before_remote_addr(self) -> None:
        """O IP encaminhado deve ter precedência sobre o REMOTE_ADDR."""

        request = SimpleNamespace(
            META={
                "HTTP_X_FORWARDED_FOR": "203.0.113.9, 10.0.0.1",
                "REMOTE_ADDR": "127.0.0.1",
            },
            api_auth_result=None,
        )

        self.assertEqual(build_rate_limit_identifier(request), "ip:203.0.113.9")

    def test_identifier_falls_back_to_unknown_when_ip_is_missing(self) -> None:
        """Sem token nem IP conhecido, o bucket deve cair no fallback seguro."""

        request = SimpleNamespace(META={}, api_auth_result=None)

        self.assertEqual(build_rate_limit_identifier(request), "ip:unknown")


@override_settings(API_RATE_LIMIT_REQUESTS=3, API_RATE_LIMIT_WINDOW_SECONDS=60)
class RateLimitBucketTests(TestCase):
    """Valida o consumo dos buckets em cache."""

    def setUp(self) -> None:
        """Limpa o cache para isolar os buckets do teste."""

        super().setUp()
        cache.clear()

    def tearDown(self) -> None:
        """Evita que buckets persistam para outros cenários."""

        cache.clear()
        super().tearDown()

    def test_get_rate_limit_config_normalizes_settings(self) -> None:
        """Os settings devem virar uma configuração pronta para o serviço."""

        config = get_rate_limit_config()

        self.assertEqual(config.limit, 3)
        self.assertEqual(config.window_seconds, 60)

    def test_consume_rate_limit_slot_increments_count_and_remaining(self) -> None:
        """O bucket deve subir o contador e reduzir o restante na mesma janela."""

        first_count, first_remaining = consume_rate_limit_slot("ip:127.0.0.1")
        second_count, second_remaining = consume_rate_limit_slot("ip:127.0.0.1")

        self.assertEqual(first_count, 1)
        self.assertEqual(first_remaining, 2)
        self.assertEqual(second_count, 2)
        self.assertEqual(second_remaining, 1)
