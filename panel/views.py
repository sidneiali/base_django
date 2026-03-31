"""Views de gestao de usuarios e grupos do painel interno."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from core.htmx import htmx_location, is_htmx_request, render_page
from .constants import PROTECTED_GROUP_NAMES
from .forms import PanelGroupForm, PanelUserForm


def _build_choices(form, field_name: str) -> tuple[list, list]:
    """
    Separa as opcoes disponiveis e selecionadas de um campo multiplo.

    Retorna duas listas no formato ``(pk, label)`` para facilitar a
    renderizacao customizada de widgets dual-list nos templates.
    """
    field = form.fields[field_name]
    current_ids = {str(v) for v in (form[field_name].value() or [])}

    available: list[tuple] = []
    chosen: list[tuple] = []
    for pk, label in field.choices:
        if not pk:
            continue
        (chosen if str(pk) in current_ids else available).append((pk, label))

    return available, chosen


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

    available, chosen = _build_choices(form, "groups")

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

    available, chosen = _build_choices(form, "groups")

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
@permission_required("auth.view_group", raise_exception=True)
def groups_list(request):
    """Lista grupos editaveis do sistema com filtro por nome."""

    query = request.GET.get("q", "").strip()

    groups = (
        Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES)
        .prefetch_related("permissions")
        .order_by("name")
    )

    if query:
        groups = groups.filter(name__icontains=query)

    return render_page(
        request,
        "panel/groups_list.html",
        "panel/partials/groups_list_content.html",
        {
            "page_title": "Grupos",
            "groups": groups,
            "query": query,
        },
    )


@login_required
@permission_required("auth.add_group", raise_exception=True)
def group_create(request):
    """Cria um grupo novo com selecao filtrada de permissoes."""

    form = PanelGroupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx_request(request):
            return htmx_location(reverse("panel_groups_list"))
        return redirect("panel_groups_list")

    available, chosen = _build_choices(form, "permissions")

    return render_page(
        request,
        "panel/group_form.html",
        "panel/partials/group_form_content.html",
        {
            "page_title": "Novo grupo",
            "form": form,
            "perm_available": available,
            "perm_chosen": chosen,
        },
    )


@login_required
@permission_required("auth.change_group", raise_exception=True)
def group_update(request, pk: int):
    """Edita um grupo existente, exceto os grupos protegidos."""

    group = get_object_or_404(
        Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES),
        pk=pk,
    )
    form = PanelGroupForm(request.POST or None, instance=group)

    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx_request(request):
            return htmx_location(reverse("panel_groups_list"))
        return redirect("panel_groups_list")

    available, chosen = _build_choices(form, "permissions")

    return render_page(
        request,
        "panel/group_form.html",
        "panel/partials/group_form_content.html",
        {
            "page_title": f"Editar grupo: {group.name}",
            "form": form,
            "group": group,
            "perm_available": available,
            "perm_chosen": chosen,
        },
    )
