"""Views do domínio de usuários do painel."""

from __future__ import annotations

from core.auth.services import send_password_recovery_email
from core.htmx import htmx_location, is_htmx_request, render_page
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..dual_list import build_dual_list_choices
from .forms import PanelUserForm
from .services import (
    UserInvitationDeliveryError,
    create_user_with_first_access_invitation,
)


def _redirect_users_list(request: HttpRequest) -> HttpResponse:
    """Redireciona para a listagem, respeitando navegação HTMX quando ativa."""

    if is_htmx_request(request):
        return htmx_location(reverse("panel_users_list"))
    return redirect("panel_users_list")


def _user_password_reset_block_reason(user: User) -> str:
    """Explica por que o disparo de recuperação não pode acontecer."""

    if not str(user.email or "").strip():
        return "O usuário precisa ter um e-mail cadastrado para receber a recuperação."
    return ""


@login_required
@permission_required("auth.view_user", raise_exception=True)
def users_list(request):
    """Lista usuarios nao superusuarios com filtro de busca textual."""

    query = request.GET.get("q", "").strip()

    users = (
        User.objects.filter(is_superuser=False)
        .prefetch_related("groups")
        .order_by("username")
    )

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    return render_page(
        request,
        "panel/users_list.html",
        "panel/partials/users_list_content.html",
        {
            "page_title": "Usuários",
            "users": users,
            "query": query,
        },
    )


@login_required
@permission_required("auth.add_user", raise_exception=True)
def user_create(request):
    """Cria um novo usuario comum e envia convite de primeiro acesso."""

    form = PanelUserForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            create_user_with_first_access_invitation(form, request)
        except UserInvitationDeliveryError as exc:
            form.add_error(None, str(exc))
        else:
            return _redirect_users_list(request)

    available, chosen = build_dual_list_choices(form, "groups")

    return render_page(
        request,
        "panel/user_form.html",
        "panel/partials/user_form_content.html",
        {
            "page_title": "Novo usuário",
            "form": form,
            "api_permission_rows": form.get_api_permission_rows(),
            "groups_available": available,
            "groups_chosen": chosen,
        },
    )


@login_required
@permission_required("auth.change_user", raise_exception=True)
def user_update(request, pk: int):
    """Edita um usuario comum existente, sem expor superusuarios."""

    user_obj = get_object_or_404(User, pk=pk, is_superuser=False)
    form = PanelUserForm(request.POST or None, instance=user_obj)

    if request.method == "POST" and form.is_valid():
        form.save()
        return _redirect_users_list(request)

    available, chosen = build_dual_list_choices(form, "groups")

    return render_page(
        request,
        "panel/user_form.html",
        "panel/partials/user_form_content.html",
        {
            "page_title": f"Editar usuário: {user_obj.username}",
            "form": form,
            "api_permission_rows": form.get_api_permission_rows(),
            "user_obj": user_obj,
            "groups_available": available,
            "groups_chosen": chosen,
        },
    )


@login_required
@permission_required("auth.change_user", raise_exception=True)
@require_POST
def user_activate(request: HttpRequest, pk: int) -> HttpResponse:
    """Ativa um usuário comum existente."""

    user_obj = get_object_or_404(User, pk=pk, is_superuser=False)
    if not user_obj.is_active:
        user_obj.is_active = True
        user_obj.save(update_fields=["is_active"])
    return _redirect_users_list(request)


@login_required
@permission_required("auth.change_user", raise_exception=True)
@require_POST
def user_deactivate(request: HttpRequest, pk: int) -> HttpResponse:
    """Inativa um usuário comum existente."""

    user_obj = get_object_or_404(User, pk=pk, is_superuser=False)
    if user_obj.is_active:
        user_obj.is_active = False
        user_obj.save(update_fields=["is_active"])
    return _redirect_users_list(request)


@login_required
@permission_required("auth.delete_user", raise_exception=True)
def user_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Confirma e executa a exclusão de um usuário comum do painel."""

    user_obj = get_object_or_404(User, pk=pk, is_superuser=False)

    if request.method == "POST":
        user_obj.delete()
        return _redirect_users_list(request)

    return render_page(
        request,
        "panel/user_delete_confirm.html",
        "panel/partials/user_delete_confirm_content.html",
        {
            "page_title": f"Excluir usuário: {user_obj.username}",
            "user_obj": user_obj,
        },
    )


@login_required
@permission_required("auth.change_user", raise_exception=True)
def user_send_password_reset(request: HttpRequest, pk: int) -> HttpResponse:
    """Confirma e envia um e-mail de recuperação para um usuário comum."""

    user_obj = get_object_or_404(User, pk=pk, is_superuser=False)
    block_reason = _user_password_reset_block_reason(user_obj)

    if request.method == "POST":
        if block_reason:
            raise PermissionDenied(block_reason)
        send_password_recovery_email(request, user_obj)
        return _redirect_users_list(request)

    return render_page(
        request,
        "panel/user_password_reset_confirm.html",
        "panel/partials/user_password_reset_confirm_content.html",
        {
            "page_title": f"Enviar recuperação de senha: {user_obj.username}",
            "user_obj": user_obj,
            "block_reason": block_reason,
        },
    )
