"""Mixins base para as views HTML do painel interno."""

from __future__ import annotations

from typing import Any

from core.htmx import htmx_location, is_htmx_request
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


class PanelLoginRequiredMixin(LoginRequiredMixin):
    """Garante autenticação antes de qualquer tela do painel."""

    login_url = "login"


class PanelPermissionRequiredMixin(PermissionRequiredMixin):
    """Padroniza a negação de permissão no painel com `403` explícito."""

    raise_exception = True


class PanelPageTemplateMixin:
    """Escolhe template completo ou parcial conforme a navegação HTMX."""

    request: HttpRequest
    partial_template_name: str | None = None
    page_title = ""

    def get_template_names(self) -> list[str]:
        """Resolve o template considerando renderização parcial via HTMX."""

        if is_htmx_request(self.request) and self.partial_template_name:
            return [self.partial_template_name]

        template_name = getattr(self, "template_name", None)
        if template_name is None:
            raise ImproperlyConfigured(
                "PanelPageTemplateMixin precisa de template_name ou get_template_names().",
            )

        if isinstance(template_name, (list, tuple)):
            return [str(item) for item in template_name]

        return [str(template_name)]

    def get_page_title(self) -> str:
        """Permite que subclasses calculem o título final da página."""

        return self.page_title

    def get_context_data(self, **kwargs):
        """Injeta o título calculado no contexto padrão do painel."""

        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", self.get_page_title())
        return context


class PanelSuccessRedirectMixin:
    """Devolve redirect clássico ou `HX-Location` no sucesso do painel."""

    request: HttpRequest
    success_url: str | Any | None = None

    def get_success_url(self) -> str:
        """Resolve a URL de retorno do fluxo atual."""

        if self.success_url is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa definir success_url.",
            )

        return str(self.success_url)

    def redirect_to_success_url(self) -> HttpResponse:
        """Redireciona respeitando navegação parcial quando o shell usa HTMX."""

        success_url = self.get_success_url()
        if is_htmx_request(self.request):
            return htmx_location(success_url)
        return redirect(success_url)
