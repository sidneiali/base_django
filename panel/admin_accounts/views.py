"""Views HTML da superfície de contas administrativas do painel."""

from __future__ import annotations

from typing import cast

from core.htmx import htmx_location, is_htmx_request, render_page
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..dual_list import build_dual_list_choices
from ..users.services import (
    UserInvitationDeliveryError,
    create_user_with_first_access_invitation,
)
from .forms import PanelAdminAccountForm
from .services import (
    AdminAccountOperationBlockedError,
    activate_admin_account,
    administrative_users_queryset,
    build_admin_account_list_rows,
    deactivate_admin_account,
    delete_admin_account,
    get_admin_account_delete_block_reason,
)


def _ensure_admin_accounts_access(user: object) -> None:
    """Restringe a área de contas administrativas a superusuários."""

    if not getattr(user, "is_superuser", False):
        raise PermissionDenied("Você não tem permissão para acessar este recurso.")


def _admin_accounts_queryset():
    """Retorna a queryset padrão da área de contas administrativas."""

    return (
        administrative_users_queryset()
        .prefetch_related("groups", "user_permissions")
        .order_by("username")
    )


def _request_admin_user(request: HttpRequest) -> User:
    """Converte o usuário autenticado do request em `User` tipado."""

    return cast(User, request.user)


def _redirect_admin_accounts_list(request: HttpRequest) -> HttpResponse:
    """Redireciona para a listagem respeitando navegação HTMX."""

    if is_htmx_request(request):
        return htmx_location(reverse("panel_admin_accounts_list"))
    return redirect("panel_admin_accounts_list")


def _build_admin_account_form_context(
    *,
    form: PanelAdminAccountForm,
    page_title: str,
    admin_account: User | None = None,
) -> dict[str, object]:
    """Monta o contexto compartilhado do formulário administrativo."""

    groups_available, groups_chosen = build_dual_list_choices(form, "groups")
    permissions_available, permissions_chosen = build_dual_list_choices(
        form,
        "user_permissions",
    )
    return {
        "page_title": page_title,
        "form": form,
        "admin_account": admin_account,
        "api_permission_rows": form.get_api_permission_rows(),
        "groups_available": groups_available,
        "groups_chosen": groups_chosen,
        "permissions_available": permissions_available,
        "permissions_chosen": permissions_chosen,
    }


@login_required
def admin_accounts_list(request: HttpRequest) -> HttpResponse:
    """Lista contas staff/superuser com busca textual e estado operacional."""

    _ensure_admin_accounts_access(request.user)
    acting_user = _request_admin_user(request)

    query = str(request.GET.get("q", "") or "").strip()
    admin_accounts = _admin_accounts_queryset()

    if query:
        admin_accounts = admin_accounts.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    rows = build_admin_account_list_rows(
        admin_accounts,
        acting_user=acting_user,
    )

    return render_page(
        request,
        "panel/admin_account_list.html",
        "panel/partials/admin_account_list_content.html",
        {
            "page_title": "Contas administrativas",
            "query": query,
            "admin_account_rows": rows,
        },
    )


@login_required
def admin_account_create(request: HttpRequest) -> HttpResponse:
    """Cria uma nova conta administrativa e envia convite de primeiro acesso."""

    _ensure_admin_accounts_access(request.user)
    acting_user = _request_admin_user(request)
    form = PanelAdminAccountForm(
        request.POST or None,
        acting_user=acting_user,
    )

    if request.method == "POST" and form.is_valid():
        try:
            create_user_with_first_access_invitation(form, request)
        except UserInvitationDeliveryError as exc:
            form.add_error(None, str(exc))
        else:
            return _redirect_admin_accounts_list(request)

    return render_page(
        request,
        "panel/admin_account_form.html",
        "panel/partials/admin_account_form_content.html",
        _build_admin_account_form_context(
            form=form,
            page_title="Nova conta administrativa",
        ),
    )


@login_required
def admin_account_update(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita uma conta administrativa existente."""

    _ensure_admin_accounts_access(request.user)
    acting_user = _request_admin_user(request)
    admin_account = get_object_or_404(_admin_accounts_queryset(), pk=pk)
    form = PanelAdminAccountForm(
        request.POST or None,
        instance=admin_account,
        acting_user=acting_user,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        return _redirect_admin_accounts_list(request)

    return render_page(
        request,
        "panel/admin_account_form.html",
        "panel/partials/admin_account_form_content.html",
        _build_admin_account_form_context(
            form=form,
            page_title=f"Editar conta administrativa: {admin_account.username}",
            admin_account=admin_account,
        ),
    )


@login_required
@require_POST
def admin_account_activate(request: HttpRequest, pk: int) -> HttpResponse:
    """Ativa uma conta administrativa existente."""

    _ensure_admin_accounts_access(request.user)
    admin_account = get_object_or_404(_admin_accounts_queryset(), pk=pk)
    activate_admin_account(admin_account)
    return _redirect_admin_accounts_list(request)


@login_required
@require_POST
def admin_account_deactivate(request: HttpRequest, pk: int) -> HttpResponse:
    """Inativa uma conta administrativa, respeitando travas operacionais."""

    _ensure_admin_accounts_access(request.user)
    acting_user = _request_admin_user(request)
    admin_account = get_object_or_404(_admin_accounts_queryset(), pk=pk)
    try:
        deactivate_admin_account(admin_account, acting_user=acting_user)
    except AdminAccountOperationBlockedError as exc:
        raise PermissionDenied(str(exc)) from exc
    return _redirect_admin_accounts_list(request)


@login_required
def admin_account_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Confirma e executa a exclusão de uma conta administrativa."""

    _ensure_admin_accounts_access(request.user)
    acting_user = _request_admin_user(request)
    admin_account = get_object_or_404(_admin_accounts_queryset(), pk=pk)
    block_reason = get_admin_account_delete_block_reason(
        admin_account,
        acting_user=acting_user,
    )

    if request.method == "POST":
        try:
            delete_admin_account(admin_account, acting_user=acting_user)
        except AdminAccountOperationBlockedError as exc:
            raise PermissionDenied(str(exc)) from exc
        return _redirect_admin_accounts_list(request)

    return render_page(
        request,
        "panel/admin_account_delete_confirm.html",
        "panel/partials/admin_account_delete_confirm_content.html",
        {
            "page_title": (
                f"Excluir conta administrativa: {admin_account.username}"
            ),
            "admin_account": admin_account,
            "block_reason": block_reason,
        },
    )
