"""Views do domínio de usuários do painel."""

from core.htmx import htmx_location, is_htmx_request, render_page
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from ..dual_list import build_dual_list_choices
from .forms import PanelUserForm


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
    """Cria um novo usuario comum e associa grupos selecionados."""

    form = PanelUserForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx_request(request):
            return htmx_location(reverse("panel_users_list"))
        return redirect("panel_users_list")

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
        if is_htmx_request(request):
            return htmx_location(reverse("panel_users_list"))
        return redirect("panel_users_list")

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
