"""Testes dos handlers globais de erro do projeto."""

from __future__ import annotations

from django.test import Client, TestCase, override_settings
from django.urls import path

from core.views import not_found_view, server_error_view


def explode_view(request):
    """View auxiliar que força um 500 para validar o handler global."""

    raise RuntimeError("boom")


urlpatterns = [
    path("explode/", explode_view, name="explode"),
]

handler404 = not_found_view
handler500 = server_error_view


@override_settings(ROOT_URLCONF="core.tests.test_error_views", DEBUG=False)
class ErrorHandlersTests(TestCase):
    """Garante que os handlers 404/500 do projeto são realmente usados."""

    def test_not_found_handler_renders_custom_page(self) -> None:
        """Rotas inexistentes devem cair na página 404 do projeto."""

        response = self.client.get("/nao-existe/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "404", status_code=404)
        self.assertContains(
            response,
            "A página solicitada não foi encontrada.",
            status_code=404,
        )

    def test_not_found_handler_returns_partial_for_htmx(self) -> None:
        """Navegação HTMX deve receber só o conteúdo central do 404."""

        response = self.client.get("/nao-existe/", HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            'data-page-title="404 - Página não encontrada"',
            html=False,
            status_code=404,
        )
        self.assertNotContains(response, "<!doctype html>", html=False, status_code=404)

    def test_server_error_handler_renders_custom_page(self) -> None:
        """Erros internos devem usar o handler 500 do projeto."""

        client = Client(raise_request_exception=False)

        response = client.get("/explode/")

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "500", status_code=500)
        self.assertContains(
            response,
            "Ocorreu um erro inesperado ao processar sua solicitação.",
            status_code=500,
        )

    def test_server_error_handler_returns_partial_for_htmx(self) -> None:
        """Falhas HTMX devem manter a resposta parcial no handler 500."""

        client = Client(raise_request_exception=False)

        response = client.get("/explode/", HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 500)
        self.assertContains(
            response,
            'data-page-title="500 - Erro interno"',
            html=False,
            status_code=500,
        )
        self.assertNotContains(response, "<!doctype html>", html=False, status_code=500)
