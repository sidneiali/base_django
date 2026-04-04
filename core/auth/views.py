"""Views e respostas do fluxo publico de autenticacao."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import views as auth_views
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import Resolver404, resolve

from .forms import LoginForm

AXES_LOCKOUT_MESSAGE = (
    "Muitas tentativas de login falharam neste IP. Aguarde alguns minutos e tente novamente."
)


class PublicLoginView(auth_views.LoginView):
    """Tela publica de login do projeto com formulario customizado."""

    authentication_form = LoginForm
    redirect_authenticated_user = True
    template_name = "registration/login.html"


def axes_lockout_response(
    request: HttpRequest,
    original_response: HttpResponse | None = None,
    credentials: dict[str, object] | None = None,
) -> HttpResponse:
    """Renderiza lockout no login publico sem perder o layout do projeto."""

    status_code = int(getattr(settings, "AXES_HTTP_RESPONSE_CODE", 429))

    try:
        url_name = resolve(request.path_info).url_name
    except Resolver404:
        url_name = None

    if url_name != "login":
        if original_response is not None:
            return original_response
        return HttpResponse(
            AXES_LOCKOUT_MESSAGE,
            status=status_code,
        )

    form = LoginForm(request=request, data=request.POST or None)
    redirect_field_value = (
        request.POST.get(REDIRECT_FIELD_NAME)
        or request.GET.get(REDIRECT_FIELD_NAME, "")
    )

    return render(
        request,
        "registration/login.html",
        {
            "form": form,
            "redirect_field_name": REDIRECT_FIELD_NAME,
            "redirect_field_value": redirect_field_value,
            "axes_locked_out": True,
            "axes_locked_out_message": AXES_LOCKOUT_MESSAGE,
            "credentials": credentials or {},
        },
        status=status_code,
    )
