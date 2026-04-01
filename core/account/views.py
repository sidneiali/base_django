"""Views da conta autenticada do usuário."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from core.api.access import (
    get_user_api_token_summary,
    issue_user_api_token,
    revoke_user_api_token,
)
from core.htmx import htmx_location, is_htmx_request, render_page

from .forms import SelfPasswordChangeForm


@login_required
def account_password_change(request):
    """Permite ao usuario atualizar a senha e gerenciar o token da API."""

    generated_api_token = request.session.pop("generated_api_token", "")

    if request.method == "POST":
        action = request.POST.get("action", "password_change")

        if action == "issue_api_token":
            raw_token = issue_user_api_token(request.user)
            if raw_token:
                request.session["generated_api_token"] = raw_token
                messages.success(
                    request,
                    "Seu token da API foi gerado. Copie agora, ele não será exibido novamente.",
                )
            else:
                messages.error(
                    request,
                    "Não foi possível gerar o token da API para sua conta.",
                )

            if is_htmx_request(request):
                return htmx_location(reverse("account_password_change"))
            return redirect("account_password_change")

        if action == "revoke_api_token":
            if revoke_user_api_token(request.user):
                messages.success(request, "Seu token da API foi revogado.")
            else:
                messages.error(
                    request,
                    "Não foi possível revogar o token da API no momento.",
                )

            if is_htmx_request(request):
                return htmx_location(reverse("account_password_change"))
            return redirect("account_password_change")

        form = SelfPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Sua senha foi atualizada com sucesso.")

            if is_htmx_request(request):
                return htmx_location(reverse("account_password_change"))
            return redirect("account_password_change")
    else:
        form = SelfPasswordChangeForm(request.user)

    return render_page(
        request,
        "account/password_change.html",
        "partials/account_password_change_content.html",
        {
            "page_title": "Minha senha",
            "form": form,
            "api_token": get_user_api_token_summary(request.user),
            "generated_api_token": generated_api_token,
        },
    )
