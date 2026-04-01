"""Views do domínio de módulos do painel."""

from __future__ import annotations

from core.htmx import htmx_location, is_htmx_request, render_page
from core.models import Module
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import PanelModuleForm


def _redirect_modules_list(request: HttpRequest) -> HttpResponse:
    """Redireciona para a listagem, respeitando navegação HTMX quando ativa."""

    if is_htmx_request(request):
        return htmx_location(reverse("panel_modules_list"))
    return redirect("panel_modules_list")


@login_required
@permission_required("core.view_module", raise_exception=True)
def modules_list(request):
    """Lista módulos do dashboard com busca textual simples."""

    query = request.GET.get("q", "").strip()
    modules = Module.objects.order_by("menu_group", "order", "name")

    if query:
        modules = modules.filter(
            Q(name__icontains=query)
            | Q(slug__icontains=query)
            | Q(description__icontains=query)
            | Q(url_name__icontains=query)
            | Q(menu_group__icontains=query)
        )

    return render_page(
        request,
        "panel/modules_list.html",
        "panel/partials/modules_list_content.html",
        {
            "page_title": "Módulos",
            "modules": modules,
            "query": query,
        },
    )


@login_required
@permission_required("core.add_module", raise_exception=True)
def module_create(request):
    """Cria um módulo novo para o dashboard do shell autenticado."""

    form = PanelModuleForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        if is_htmx_request(request):
            return htmx_location(reverse("panel_modules_list"))
        return redirect("panel_modules_list")

    return render_page(
        request,
        "panel/module_form.html",
        "panel/partials/module_form_content.html",
        {
            "page_title": "Novo módulo",
            "form": form,
        },
    )


@login_required
@permission_required("core.change_module", raise_exception=True)
def module_update(request, pk: int):
    """Edita um módulo existente do dashboard."""

    module = get_object_or_404(Module, pk=pk)
    form = PanelModuleForm(request.POST or None, instance=module)

    if request.method == "POST" and form.is_valid():
        form.save()
        return _redirect_modules_list(request)

    return render_page(
        request,
        "panel/module_form.html",
        "panel/partials/module_form_content.html",
        {
            "page_title": f"Editar módulo: {module.name}",
            "form": form,
            "module": module,
        },
    )


@login_required
@permission_required("core.change_module", raise_exception=True)
@require_POST
def module_activate(request: HttpRequest, pk: int) -> HttpResponse:
    """Ativa um módulo existente do dashboard."""

    module = get_object_or_404(Module, pk=pk)
    if not module.is_active:
        module.is_active = True
        module.save(update_fields=["is_active"])
    return _redirect_modules_list(request)


@login_required
@permission_required("core.change_module", raise_exception=True)
@require_POST
def module_deactivate(request: HttpRequest, pk: int) -> HttpResponse:
    """Inativa um módulo existente do dashboard."""

    module = get_object_or_404(Module, pk=pk)
    if module.is_active:
        module.is_active = False
        module.save(update_fields=["is_active"])
    return _redirect_modules_list(request)


@login_required
@permission_required("core.delete_module", raise_exception=True)
def module_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Confirma e executa a exclusão segura de um módulo do dashboard."""

    module = get_object_or_404(Module, pk=pk)
    block_reason = module.delete_block_reason

    if request.method == "POST" and not block_reason:
        module.delete()
        return _redirect_modules_list(request)

    status = 400 if request.method == "POST" and block_reason else 200
    return render_page(
        request,
        "panel/module_delete_confirm.html",
        "panel/partials/module_delete_confirm_content.html",
        {
            "page_title": f"Excluir módulo: {module.name}",
            "module": module,
            "delete_block_reason": block_reason,
        },
        status=status,
    )
