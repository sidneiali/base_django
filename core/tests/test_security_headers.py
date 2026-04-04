"""Testes dos headers HTTP de segurança e consumo externo da API."""

from __future__ import annotations

from django.test import TestCase, override_settings
from django.urls import reverse


class ContentSecurityPolicyTests(TestCase):
    """Valida a política CSP aplicada fora do admin do Django."""

    def test_public_login_includes_enforced_csp_header(self) -> None:
        """A tela pública de login deve sair com uma CSP restritiva."""

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        csp_header = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp_header)
        self.assertIn("script-src 'self'", csp_header)
        self.assertIn("script-src-attr 'none'", csp_header)
        self.assertIn("style-src 'self'", csp_header)
        self.assertIn("style-src-elem 'self'", csp_header)
        self.assertIn("style-src-attr 'unsafe-inline'", csp_header)
        self.assertIn("connect-src 'self'", csp_header)
        self.assertIn("frame-ancestors 'none'", csp_header)
        self.assertIn("object-src 'none'", csp_header)
        self.assertNotIn("unsafe-eval", csp_header)

    def test_admin_login_stays_outside_csp_until_admin_specific_policy_exists(
        self,
    ) -> None:
        """O admin segue sem CSP própria para não quebrar a UI interna do Django."""

        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Security-Policy", response)


@override_settings(
    CORS_ALLOWED_ORIGINS=["https://frontend.example.com"],
    CORS_ALLOW_ALL_ORIGINS=False,
)
class CorsHeadersTests(TestCase):
    """Valida CORS opt-in e restrito à superfície `/api/`."""

    def test_public_openapi_json_exposes_cors_headers_for_allowed_origin(self) -> None:
        """Origens explícitas devem conseguir ler a OpenAPI pública via browser."""

        response = self.client.get(
            reverse("api_v1_openapi"),
            HTTP_ORIGIN="https://frontend.example.com",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["access-control-allow-origin"],
            "https://frontend.example.com",
        )
        self.assertEqual(response["access-control-expose-headers"], "X-Request-ID")

    def test_preflight_on_api_path_allows_authorization_and_request_id(self) -> None:
        """Pré-flight em `/api/` deve aceitar Authorization e X-Request-ID."""

        response = self.client.options(
            reverse("api_v1_openapi"),
            HTTP_ORIGIN="https://frontend.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,x-request-id",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["access-control-allow-origin"],
            "https://frontend.example.com",
        )
        allow_headers = response["access-control-allow-headers"].lower()
        self.assertIn("authorization", allow_headers)
        self.assertIn("x-request-id", allow_headers)

    def test_non_api_page_does_not_emit_cors_headers(self) -> None:
        """As páginas HTML não devem virar CORS-enabled por acidente."""

        response = self.client.get(
            reverse("login"),
            HTTP_ORIGIN="https://frontend.example.com",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response)

    def test_disallowed_origin_receives_no_cors_header(self) -> None:
        """Origens fora da allowlist devem continuar bloqueadas pelo browser."""

        response = self.client.get(
            reverse("api_v1_openapi"),
            HTTP_ORIGIN="https://nao-autorizado.example.com",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response)
