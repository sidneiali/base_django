"""Views do domínio de grupos do painel."""

from core.htmx import htmx_location, is_htmx_request, render_page
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from ..constants import PROTECTED_GROUP_NAMES
from ..dual_list import build_dual_list_choices
from .forms import PanelGroupForm


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

    available, chosen = build_dual_list_choices(form, "permissions")

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

    available, chosen = build_dual_list_choices(form, "permissions")

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
