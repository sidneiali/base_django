"""Testes unitarios das regras de path usadas pelos middlewares."""

from django.test import SimpleTestCase

from core.middleware.paths import (
    is_json_api_request,
    is_operational_health_path,
    is_rate_limited_path,
)


class MiddlewarePathRulesTests(SimpleTestCase):
    """Garante a classificacao correta das rotas publicas e protegidas."""

    def test_docs_and_non_api_routes_stay_out_of_json_api_detection(self) -> None:
        """Docs, OpenAPI e telas HTML nao devem entrar nos middlewares JSON."""

        public_paths = [
            "/",
            "/dashboard/",
            "/painel/usuarios/",
            "/api/docs/",
            "/api/docs/postman.json",
            "/api/docs/redoc/",
            "/api/openapi.json",
            "/api/v1/openapi.json",
        ]

        for path in public_paths:
            with self.subTest(path=path):
                self.assertFalse(is_json_api_request(path))
                self.assertFalse(is_rate_limited_path(path))
                self.assertFalse(is_operational_health_path(path))

    def test_operational_health_paths_are_public_json_but_skip_rate_limit(
        self,
    ) -> None:
        """Healthchecks do core seguem publicos e fora do bucket de limite."""

        health_paths = [
            "/api/core/health/",
            "/api/v1/core/health/",
        ]

        for path in health_paths:
            with self.subTest(path=path):
                self.assertTrue(is_json_api_request(path))
                self.assertTrue(is_operational_health_path(path))
                self.assertFalse(is_rate_limited_path(path))

    def test_protected_api_paths_remain_subject_to_rate_limit(self) -> None:
        """Rotas protegidas ou operacionais nao leves continuam controladas."""

        protected_paths = [
            "/api/core/me/",
            "/api/core/audit-logs/",
            "/api/panel/users/",
            "/api/panel/groups/1/",
            "/api/v1/core/me/",
            "/api/v1/panel/modules/2/",
        ]

        for path in protected_paths:
            with self.subTest(path=path):
                self.assertTrue(is_json_api_request(path))
                self.assertFalse(is_operational_health_path(path))
                self.assertTrue(is_rate_limited_path(path))
