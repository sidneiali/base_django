"""Views do domínio de módulos do painel."""

from __future__ import annotations

from core.models import Module
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from ..mixins import (
    PanelLoginRequiredMixin,
    PanelPageTemplateMixin,
    PanelPermissionRequiredMixin,
    PanelSuccessRedirectMixin,
)
from .forms import PanelModuleForm
from .services import (
    ModuleDeletionBlockedError,
    delete_panel_module,
    set_module_active_state,
)


class ModuleListView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    ListView,
):
    """Lista módulos do dashboard com busca textual simples."""

    model = Module
    context_object_name = "modules"
    permission_required = "core.view_module"
    page_title = "Módulos"
    template_name = "panel/modules_list.html"
    partial_template_name = "panel/partials/modules_list_content.html"

    def get_query(self) -> str:
        """Normaliza o termo de busca textual da listagem."""

        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        """Filtra a listagem por campos operacionais do módulo."""

        modules = Module.objects.order_by("menu_group", "order", "name")
        query = self.get_query()

        if query:
            modules = modules.filter(
                Q(name__icontains=query)
                | Q(slug__icontains=query)
                | Q(description__icontains=query)
                | Q(url_name__icontains=query)
                | Q(menu_group__icontains=query)
            )

        return modules

    def get_context_data(self, **kwargs):
        """Expõe o termo de busca para o formulário HTMX da listagem."""

        context = super().get_context_data(**kwargs)
        context["query"] = self.get_query()
        return context


class ModuleFormViewMixin(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
):
    """Base compartilhada entre criação e edição HTML de módulos."""

    def form_valid(self, form: PanelModuleForm) -> HttpResponse:
        """Persiste o módulo e devolve o redirect adequado ao shell."""

        form.save()
        return self.redirect_to_success_url()


class ModuleCreateView(ModuleFormViewMixin, CreateView):
    """Cria um módulo novo para o dashboard do shell autenticado."""

    model = Module
    form_class = PanelModuleForm
    permission_required = "core.add_module"
    page_title = "Novo módulo"
    template_name = "panel/module_form.html"
    partial_template_name = "panel/partials/module_form_content.html"
    success_url = reverse_lazy("panel_modules_list")


class ModuleUpdateView(ModuleFormViewMixin, UpdateView):
    """Edita um módulo existente do dashboard."""

    model = Module
    form_class = PanelModuleForm
    permission_required = "core.change_module"
    template_name = "panel/module_form.html"
    partial_template_name = "panel/partials/module_form_content.html"
    success_url = reverse_lazy("panel_modules_list")

    def get_page_title(self) -> str:
        """Monta o título contextual da edição atual."""

        return f"Editar módulo: {self.object.name}"


class ModuleStateUpdateView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelSuccessRedirectMixin,
    SingleObjectMixin,
    View,
):
    """Base compartilhada para ativar ou inativar módulos via POST."""

    model = Module
    permission_required = "core.change_module"
    success_url = reverse_lazy("panel_modules_list")
    active_state = True
    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Atualiza o estado ativo do módulo e volta para a listagem."""

        self.object = self.get_object()
        set_module_active_state(self.object, is_active=self.active_state)
        return self.redirect_to_success_url()


class ModuleActivateView(ModuleStateUpdateView):
    """Ativa um módulo existente do dashboard."""

    active_state = True


class ModuleDeactivateView(ModuleStateUpdateView):
    """Inativa um módulo existente do dashboard."""

    active_state = False


class ModuleDeleteView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
    DeleteView,
):
    """Confirma e executa a exclusão segura de um módulo do dashboard."""

    model = Module
    context_object_name = "module"
    permission_required = "core.delete_module"
    template_name = "panel/module_delete_confirm.html"
    partial_template_name = "panel/partials/module_delete_confirm_content.html"
    success_url = reverse_lazy("panel_modules_list")

    def get_page_title(self) -> str:
        """Monta o título contextual da confirmação de exclusão."""

        return f"Excluir módulo: {self.object.name}"

    def get_context_data(self, **kwargs):
        """Expõe o motivo de bloqueio quando a exclusão não é permitida."""

        context = super().get_context_data(**kwargs)
        context["delete_block_reason"] = self.object.delete_block_reason
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Tenta excluir o módulo, rerenderizando a tela se houver bloqueio."""

        self.object = self.get_object()

        try:
            delete_panel_module(self.object)
        except ModuleDeletionBlockedError:
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context, status=400)

        return self.redirect_to_success_url()


modules_list = ModuleListView.as_view()
module_create = ModuleCreateView.as_view()
module_update = ModuleUpdateView.as_view()
module_activate = ModuleActivateView.as_view()
module_deactivate = ModuleDeactivateView.as_view()
module_delete = ModuleDeleteView.as_view()
