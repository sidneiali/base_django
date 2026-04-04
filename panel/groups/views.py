"""Views do domínio de grupos do painel."""

from django.contrib.auth.models import Group
from django.db.models import QuerySet
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..dual_list import build_dual_list_choices
from ..mixins import (
    PanelLoginRequiredMixin,
    PanelPageTemplateMixin,
    PanelPermissionRequiredMixin,
    PanelSuccessRedirectMixin,
)
from .forms import PanelGroupForm
from .services import delete_panel_group, editable_groups_queryset


class GroupListView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    ListView,
):
    """Lista grupos editáveis do sistema com filtro por nome."""

    model = Group
    context_object_name = "groups"
    permission_required = "auth.view_group"
    page_title = "Grupos"
    template_name = "panel/groups_list.html"
    partial_template_name = "panel/partials/groups_list_content.html"

    def get_query(self) -> str:
        """Normaliza o termo de busca textual da listagem."""

        return self.request.GET.get("q", "").strip()

    def get_queryset(self) -> QuerySet[Group]:
        """Filtra a listagem por grupos editáveis e busca textual."""

        groups = editable_groups_queryset().prefetch_related("permissions").order_by(
            "name"
        )
        query = self.get_query()

        if query:
            groups = groups.filter(name__icontains=query)

        return groups

    def get_context_data(self, **kwargs):
        """Expõe o termo de busca para o formulário HTMX da listagem."""

        context = super().get_context_data(**kwargs)
        context["query"] = self.get_query()
        return context


class GroupFormViewMixin(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
):
    """Base compartilhada entre criação e edição HTML de grupos."""

    def get_queryset(self) -> QuerySet[Group]:
        """Limita a edição à superfície de grupos editáveis."""

        return editable_groups_queryset()

    def get_form_context(self, form: PanelGroupForm) -> dict[str, object]:
        """Monta o contexto comum do formulário com a dual-list."""

        available, chosen = build_dual_list_choices(form, "permissions")
        return {
            "form": form,
            "perm_available": available,
            "perm_chosen": chosen,
        }

    def get_context_data(self, **kwargs):
        """Injeta o contexto expandido do formulário de grupos."""

        context = super().get_context_data(**kwargs)
        form = kwargs.get("form", self.get_form())
        context.update(self.get_form_context(form))
        return context

    def form_valid(self, form: PanelGroupForm) -> HttpResponse:
        """Persiste o grupo e devolve o redirect adequado ao shell."""

        form.save()
        return self.redirect_to_success_url()


class GroupCreateView(GroupFormViewMixin, CreateView):
    """Cria um grupo novo com seleção filtrada de permissões."""

    model = Group
    form_class = PanelGroupForm
    permission_required = "auth.add_group"
    page_title = "Novo grupo"
    template_name = "panel/group_form.html"
    partial_template_name = "panel/partials/group_form_content.html"
    success_url = reverse_lazy("panel_groups_list")


class GroupUpdateView(GroupFormViewMixin, UpdateView):
    """Edita um grupo existente, exceto os grupos protegidos."""

    model = Group
    form_class = PanelGroupForm
    permission_required = "auth.change_group"
    template_name = "panel/group_form.html"
    partial_template_name = "panel/partials/group_form_content.html"
    success_url = reverse_lazy("panel_groups_list")

    def get_page_title(self) -> str:
        """Monta o título contextual da edição atual."""

        return f"Editar grupo: {self.object.name}"

    def get_form_context(self, form: PanelGroupForm) -> dict[str, object]:
        """Expõe o grupo atual para o template manter o comportamento visual."""

        context = super().get_form_context(form)
        context["group"] = self.object
        return context


class GroupDeleteView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
    DeleteView,
):
    """Confirma e executa a exclusão de um grupo editável do painel."""

    model = Group
    context_object_name = "group"
    permission_required = "auth.delete_group"
    template_name = "panel/group_delete_confirm.html"
    partial_template_name = "panel/partials/group_delete_confirm_content.html"
    success_url = reverse_lazy("panel_groups_list")

    def get_queryset(self) -> QuerySet[Group]:
        """Limita a exclusão à superfície de grupos editáveis."""

        return editable_groups_queryset()

    def get_page_title(self) -> str:
        """Monta o título contextual da confirmação de exclusão."""

        return f"Excluir grupo: {self.object.name}"

    def post(self, request, *args, **kwargs) -> HttpResponse:
        """Exclui o grupo editável e retorna para a listagem."""

        self.object = self.get_object()
        delete_panel_group(self.object)
        return self.redirect_to_success_url()


groups_list = GroupListView.as_view()
group_create = GroupCreateView.as_view()
group_update = GroupUpdateView.as_view()
group_delete = GroupDeleteView.as_view()
