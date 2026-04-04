"""Views do domínio de usuários do painel."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin

from ..dual_list import build_dual_list_choices
from ..mixins import (
    PanelLoginRequiredMixin,
    PanelPageTemplateMixin,
    PanelPermissionRequiredMixin,
    PanelSuccessRedirectMixin,
)
from .forms import PanelUserForm
from .services import (
    UserInvitationDeliveryError,
    common_users_queryset,
    create_user_with_first_access_invitation,
    delete_common_user,
    get_common_user_password_reset_block_reason,
    save_common_user_form,
    send_common_user_password_reset,
    set_common_user_active_state,
)


class UserListView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    ListView,
):
    """Lista usuários comuns do sistema com filtro de busca textual."""

    model = User
    context_object_name = "users"
    permission_required = "auth.view_user"
    page_title = "Usuários"
    template_name = "panel/users_list.html"
    partial_template_name = "panel/partials/users_list_content.html"

    def get_query(self) -> str:
        """Normaliza o termo de busca textual da listagem."""

        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        """Filtra a listagem por campos operacionais do usuário comum."""

        users = common_users_queryset().prefetch_related("groups").order_by("username")
        query = self.get_query()

        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )

        return users

    def get_context_data(self, **kwargs):
        """Expõe o termo de busca para o formulário HTMX da listagem."""

        context = super().get_context_data(**kwargs)
        context["query"] = self.get_query()
        return context


class UserFormViewMixin(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
    TemplateResponseMixin,
):
    """Base compartilhada entre criação e edição HTML de usuários comuns."""

    def get_queryset(self):
        """Limita a edição à superfície de usuários comuns."""

        return common_users_queryset()

    def get_form_context(self, form: PanelUserForm) -> dict[str, object]:
        """Monta o contexto comum do formulário com API e dual-list."""

        available, chosen = build_dual_list_choices(form, "groups")
        return {
            "form": form,
            "api_permission_rows": form.get_api_permission_rows(),
            "groups_available": available,
            "groups_chosen": chosen,
        }

    def get_context_data(self, **kwargs):
        """Injeta o contexto expandido do formulário de usuários."""

        context = super().get_context_data(**kwargs)
        form = kwargs.get("form", self.get_form())
        context.update(self.get_form_context(form))
        return context

    def form_valid(self, form: PanelUserForm) -> HttpResponse:
        """Persiste o usuário comum e devolve o redirect adequado ao shell."""

        try:
            if getattr(self, "object", None) is None:
                create_user_with_first_access_invitation(form, self.request)
            else:
                save_common_user_form(form)
        except UserInvitationDeliveryError as exc:
            form.add_error(None, str(exc))
            return self.render_to_response(self.get_context_data(form=form))

        return self.redirect_to_success_url()


class UserCreateView(UserFormViewMixin, CreateView):
    """Cria um novo usuário comum e envia convite de primeiro acesso."""

    model = User
    form_class = PanelUserForm
    permission_required = "auth.add_user"
    page_title = "Novo usuário"
    template_name = "panel/user_form.html"
    partial_template_name = "panel/partials/user_form_content.html"
    success_url = reverse_lazy("panel_users_list")
    object = None


class UserUpdateView(UserFormViewMixin, UpdateView):
    """Edita um usuário comum existente, sem expor contas administrativas."""

    model = User
    form_class = PanelUserForm
    permission_required = "auth.change_user"
    template_name = "panel/user_form.html"
    partial_template_name = "panel/partials/user_form_content.html"
    success_url = reverse_lazy("panel_users_list")

    def get_page_title(self) -> str:
        """Monta o título contextual da edição atual."""

        return f"Editar usuário: {self.object.username}"

    def get_form_context(self, form: PanelUserForm) -> dict[str, object]:
        """Expõe o usuário atual para o template manter o comportamento visual."""

        context = super().get_form_context(form)
        context["user_obj"] = self.object
        return context


class UserStateUpdateView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelSuccessRedirectMixin,
    SingleObjectMixin,
    View,
):
    """Base compartilhada para ativar ou inativar usuários comuns via POST."""

    model = User
    permission_required = "auth.change_user"
    success_url = reverse_lazy("panel_users_list")
    active_state = True
    http_method_names = ["post"]

    def get_queryset(self):
        """Limita a ação rápida à superfície de usuários comuns."""

        return common_users_queryset()

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Atualiza o estado ativo do usuário e volta para a listagem."""

        self.object = self.get_object()
        set_common_user_active_state(self.object, is_active=self.active_state)
        return self.redirect_to_success_url()


class UserActivateView(UserStateUpdateView):
    """Ativa um usuário comum existente."""

    active_state = True


class UserDeactivateView(UserStateUpdateView):
    """Inativa um usuário comum existente."""

    active_state = False


class UserDeleteView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
    DeleteView,
):
    """Confirma e executa a exclusão de um usuário comum do painel."""

    model = User
    context_object_name = "user_obj"
    permission_required = "auth.delete_user"
    template_name = "panel/user_delete_confirm.html"
    partial_template_name = "panel/partials/user_delete_confirm_content.html"
    success_url = reverse_lazy("panel_users_list")

    def get_queryset(self):
        """Limita a exclusão à superfície de usuários comuns."""

        return common_users_queryset()

    def get_page_title(self) -> str:
        """Monta o título contextual da confirmação de exclusão."""

        return f"Excluir usuário: {self.object.username}"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Exclui o usuário comum e retorna para a listagem."""

        self.object = self.get_object()
        delete_common_user(self.object)
        return self.redirect_to_success_url()


class UserPasswordResetConfirmView(
    PanelLoginRequiredMixin,
    PanelPermissionRequiredMixin,
    PanelPageTemplateMixin,
    PanelSuccessRedirectMixin,
    SingleObjectMixin,
    TemplateResponseMixin,
    View,
):
    """Confirma e envia um e-mail de recuperação para um usuário comum."""

    model = User
    context_object_name = "user_obj"
    permission_required = "auth.change_user"
    template_name = "panel/user_password_reset_confirm.html"
    partial_template_name = "panel/partials/user_password_reset_confirm_content.html"
    success_url = reverse_lazy("panel_users_list")
    http_method_names = ["get", "post"]

    def get_queryset(self):
        """Limita a recuperação à superfície de usuários comuns."""

        return common_users_queryset()

    def get_page_title(self) -> str:
        """Monta o título contextual da confirmação atual."""

        return f"Enviar recuperação de senha: {self.object.username}"

    def get_context_data(self, **kwargs) -> dict[str, object]:
        """Expõe o usuário e o motivo de bloqueio no template de confirmação."""

        return {
            "page_title": self.get_page_title(),
            "user_obj": self.object,
            "block_reason": get_common_user_password_reset_block_reason(self.object),
        }

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Renderiza a confirmação da recuperação para um usuário comum."""

        self.object = self.get_object()
        return self.render_to_response(self.get_context_data())

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Dispara a recuperação se o usuário comum tiver e-mail válido."""

        self.object = self.get_object()
        block_reason = get_common_user_password_reset_block_reason(self.object)
        if block_reason:
            raise PermissionDenied(block_reason)
        send_common_user_password_reset(request, self.object)
        return self.redirect_to_success_url()


users_list = UserListView.as_view()
user_create = UserCreateView.as_view()
user_update = UserUpdateView.as_view()
user_activate = UserActivateView.as_view()
user_deactivate = UserDeactivateView.as_view()
user_delete = UserDeleteView.as_view()
user_send_password_reset = UserPasswordResetConfirmView.as_view()
