"""Views principais do dashboard, conta e documentação pública da API."""

import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .api_access import (get_user_api_token_summary, issue_user_api_token,
                         revoke_user_api_token)
from .htmx import htmx_location, is_htmx_request, render_page
from .forms import SelfPasswordChangeForm
from .models import Module
from .services import build_modules_for_user


def _build_public_base_url(request) -> str:
    """Retorna a URL base absoluta da instância atual sem barra final."""

    return request.build_absolute_uri("/").rstrip("/")


def _build_postman_collection(request) -> dict[str, object]:
    """Monta a coleção Postman pública dos recursos disponíveis da API."""

    base_url = _build_public_base_url(request)
    health_url = f"{base_url}{reverse('api_core_health')}"
    me_url = f"{base_url}{reverse('api_core_me')}"
    token_url = f"{base_url}{reverse('api_core_token')}"
    users_collection_url = f"{base_url}{reverse('api_panel_users_collection')}"
    user_detail_url = f"{base_url}/api/panel/users/:id/"
    audit_logs_collection_url = f"{base_url}{reverse('api_core_audit_logs_collection')}"
    audit_log_detail_url = f"{base_url}/api/core/audit-logs/:id/"

    return {
        "info": {
            "name": "BaseApp API",
            "description": (
                "Coleção pública da API protegida por Bearer token para usuários "
                "do painel e logs de auditoria."
            ),
            "schema": (
                "https://schema.getpostman.com/json/collection/v2.1.0/"
                "collection.json"
            ),
        },
        "variable": [
            {"key": "base_url", "value": base_url},
            {"key": "token", "value": "SEU_TOKEN"},
            {"key": "user_id", "value": "1"},
            {"key": "audit_log_id", "value": "1"},
        ],
        "item": [
            {
                "name": "Operacional",
                "item": [
                    {
                        "name": "Health check",
                        "request": {
                            "method": "GET",
                            "url": health_url,
                        },
                    },
                ],
            },
            {
                "name": "Acesso à API",
                "item": [
                    {
                        "name": "Minha conta",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": me_url,
                        },
                    },
                    {
                        "name": "Token atual",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": token_url,
                        },
                    },
                ],
            },
            {
                "name": "Usuários do painel",
                "item": [
                    {
                        "name": "Listar usuários",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": users_collection_url,
                        },
                    },
                    {
                        "name": "Criar usuário",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                },
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text",
                                },
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "username": "api-user",
                                        "email": "api@example.com",
                                        "password": "SenhaSegura@123",
                                        "is_active": True,
                                    },
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                            },
                            "url": users_collection_url,
                        },
                    },
                    {
                        "name": "Detalhar usuário",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": user_detail_url,
                        },
                    },
                    {
                        "name": "Atualizar usuário",
                        "request": {
                            "method": "PATCH",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                },
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text",
                                },
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {"email": "alterado@example.com"},
                                    ensure_ascii=False,
                                    indent=2,
                                ),
                            },
                            "url": user_detail_url.replace(":id", "{{user_id}}"),
                        },
                    },
                    {
                        "name": "Excluir usuário",
                        "request": {
                            "method": "DELETE",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": user_detail_url.replace(":id", "{{user_id}}"),
                        },
                    },
                ],
            },
            {
                "name": "Logs de auditoria",
                "item": [
                    {
                        "name": "Listar logs de auditoria",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": audit_logs_collection_url,
                        },
                    },
                    {
                        "name": "Detalhar log de auditoria",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{token}}",
                                    "type": "text",
                                }
                            ],
                            "url": audit_log_detail_url.replace(":id", "{{audit_log_id}}"),
                        },
                    },
                ],
            }
        ],
    }


@login_required
def dashboard(request):
    """Renderiza o dashboard com os modulos visiveis ao usuario logado."""

    modules = build_modules_for_user(request.user)
    return render_page(
        request,
        "dashboard.html",
        "partials/dashboard_content.html",
        {"modules": modules},
    )


@login_required
def module_entry(request, slug: str):
    """Abre a pagina de entrada de um modulo ativo e valida permissao."""

    module = get_object_or_404(Module, slug=slug, is_active=True)

    if module.full_permission:
        if not (
            request.user.is_superuser
            or request.user.has_perm(module.full_permission)
        ):
            raise PermissionDenied

    return render_page(
        request,
        "module_page.html",
        "partials/module_page_content.html",
        {"module": module},
    )


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


def api_docs(request):
    """Exibe a pagina publica de documentação/testes da API."""

    return render(
        request,
        "account/api_docs.html",
        {
            "page_title": "Swagger da API",
            "api_base_url": _build_public_base_url(request),
            "postman_download_url": reverse("api_docs_postman"),
        },
    )


def api_docs_postman(request):
    """Entrega a coleção Postman pública da API para download."""

    collection = _build_postman_collection(request)
    response = HttpResponse(
        json.dumps(collection, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = (
        'attachment; filename="baseapp-api-postman-collection.json"'
    )
    return response


def forbidden_view(request, exception=None):
    """Renderiza a pagina padrao de acesso negado do projeto."""

    return render_page(
        request,
        "forbidden.html",
        "partials/forbidden_content.html",
        {},
        status=403,
    )
