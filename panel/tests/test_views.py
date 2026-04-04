"""Testes dos fluxos HTML do painel."""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class PanelViewTests(TestCase):
    """Valida permissões e fluxos HTMX do painel interno."""

    def _login_with_permissions(self, *codenames: str) -> AbstractUser:
        """Autentica um operador com o conjunto informado de permissões."""

        user = User.objects.create_user(
            username="operador",
            email="operador@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(Permission.objects.filter(codename__in=codenames))
        user.user_permissions.add(*permissions)
        self.client.force_login(user)
        return user

    def test_users_list_requires_view_permission(self) -> None:
        """Usuário autenticado sem permissão não pode listar usuários."""

        self._login_with_permissions()

        response = self.client.get(reverse("panel_users_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_users_list_filters_results_and_renders_partial_for_htmx(self) -> None:
        """A listagem deve filtrar por busca e devolver partial no HTMX."""

        self._login_with_permissions("view_user")
        User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_user(
            username="bruno",
            email="bruno@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.get(
            reverse("panel_users_list"),
            {"q": "ana"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Usuários"', html=False)
        self.assertContains(response, "ana")
        self.assertNotContains(response, "bruno")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_users_list_excludes_staff_accounts_from_common_area(self) -> None:
        """Contas administrativas não devem reaparecer na área de usuários comuns."""

        self._login_with_permissions("view_user")
        User.objects.create_user(
            username="comum",
            email="comum@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_user(
            username="staff-area",
            email="staff-area@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )

        response = self.client.get(reverse("panel_users_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "comum")
        self.assertNotContains(response, "staff-area")

    def test_users_list_renders_disabled_actions_without_management_permissions(self) -> None:
        """A listagem deve exibir ações desabilitadas quando faltar permissão."""

        self._login_with_permissions("view_user")
        User.objects.create_user(
            username="ativo",
            email="ativo@example.com",
            password="SenhaSegura@123",
            is_active=True,
        )
        User.objects.create_user(
            username="inativo",
            email="inativo@example.com",
            password="SenhaSegura@123",
            is_active=False,
        )

        response = self.client.get(reverse("panel_users_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-teste="users-create-disabled"', html=False)
        self.assertContains(response, 'data-teste="user-edit-disabled"', html=False)
        self.assertContains(response, 'data-teste="user-toggle-disabled"', html=False)
        self.assertContains(response, "Inativar")
        self.assertContains(response, "Ativar")
        self.assertContains(response, 'data-teste="user-password-reset-disabled"', html=False)
        self.assertContains(response, 'data-teste="user-delete-disabled"', html=False)

    def test_users_list_renders_enabled_actions_with_management_permissions(self) -> None:
        """A listagem deve expor ações reais quando o operador tiver permissão."""

        self._login_with_permissions("view_user", "add_user", "change_user", "delete_user")
        User.objects.create_user(
            username="ativo",
            email="ativo@example.com",
            password="SenhaSegura@123",
            is_active=True,
        )
        User.objects.create_user(
            username="inativo",
            email="inativo@example.com",
            password="SenhaSegura@123",
            is_active=False,
        )

        response = self.client.get(reverse("panel_users_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-teste="users-create-link"', html=False)
        self.assertContains(response, 'data-teste="user-edit-link"', html=False)
        self.assertContains(response, 'data-teste="user-deactivate-submit"', html=False)
        self.assertContains(response, 'data-teste="user-activate-submit"', html=False)
        self.assertContains(response, 'data-teste="user-password-reset-link"', html=False)
        self.assertContains(response, 'data-teste="user-delete-link"', html=False)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_user_password_reset_confirmation_and_send_email(self) -> None:
        """O painel deve confirmar e disparar o e-mail de recuperação do usuário."""

        self._login_with_permissions("change_user")
        user_obj = User.objects.create_user(
            username="recuperavel",
            email="recuperavel@example.com",
            password="SenhaSegura@123",
        )

        confirm_response = self.client.get(
            reverse("panel_user_send_password_reset", args=[user_obj.pk]),
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(
            confirm_response,
            'data-teste="user-password-reset-confirm-submit"',
            html=False,
        )
        self.assertContains(confirm_response, "recuperavel@example.com")

        send_response = self.client.post(
            reverse("panel_user_send_password_reset", args=[user_obj.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(send_response.status_code, 204)
        payload = json.loads(send_response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_users_list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Recuperação de senha", mail.outbox[0].subject)
        self.assertIn("/recuperar-senha/confirmar/", mail.outbox[0].body)
        self.assertIn("recuperavel@example.com", mail.outbox[0].to)

    def test_user_password_reset_confirmation_is_disabled_without_email(self) -> None:
        """Sem e-mail cadastrado, o botão de confirmação deve permanecer desabilitado."""

        self._login_with_permissions("change_user")
        user_obj = User.objects.create_user(
            username="sem-email-reset",
            email="",
            password="SenhaSegura@123",
        )

        response = self.client.get(
            reverse("panel_user_send_password_reset", args=[user_obj.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-teste="user-password-reset-disabled-submit"',
            html=False,
        )
        self.assertContains(
            response,
            "O usuário precisa ter um e-mail cadastrado para receber a recuperação.",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_user_create_htmx_creates_user_and_sends_first_access_invite(self) -> None:
        """Criar usuário via HTMX deve persistir e disparar o convite inicial."""

        self._login_with_permissions("add_user")
        group = Group.objects.create(name="Operação")

        response = self.client.post(
            reverse("panel_user_create"),
            {
                "username": "novo-painel",
                "first_name": "Novo",
                "last_name": "Usuário",
                "email": "novo@example.com",
                "is_active": "on",
                "groups": [str(group.pk)],
                "auto_refresh_interval": "30",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_users_list"))

        created_user = User.objects.get(username="novo-painel")
        self.assertTrue(created_user.groups.filter(pk=group.pk).exists())
        self.assertFalse(created_user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Primeiro acesso", mail.outbox[0].subject)
        self.assertIn("/recuperar-senha/confirmar/", mail.outbox[0].body)
        self.assertIn("novo@example.com", mail.outbox[0].to)

    def test_user_create_rejects_group_above_operator_scope(self) -> None:
        """O operador não pode criar usuário em grupo acima da própria conta."""

        self._login_with_permissions("add_user")
        blocked_group = Group.objects.create(name="Grupo acima do teto")
        blocked_group.permissions.add(Permission.objects.get(codename="delete_group"))

        response = self.client.post(
            reverse("panel_user_create"),
            {
                "username": "excesso-grupo",
                "first_name": "Excesso",
                "last_name": "Grupo",
                "email": "excesso-grupo@example.com",
                "is_active": "on",
                "groups": [str(blocked_group.pk)],
                "auto_refresh_interval": "30",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Faça uma escolha válida.")
        self.assertFalse(User.objects.filter(username="excesso-grupo").exists())

    def test_user_deactivate_and_activate_toggle_state(self) -> None:
        """A listagem deve permitir inativar e reativar usuários com POST."""

        self._login_with_permissions("change_user")
        user_obj = User.objects.create_user(
            username="alternar",
            email="alternar@example.com",
            password="SenhaSegura@123",
            is_active=True,
        )

        deactivate_response = self.client.post(
            reverse("panel_user_deactivate", args=[user_obj.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(deactivate_response.status_code, 204)
        user_obj.refresh_from_db()
        self.assertFalse(user_obj.is_active)

        activate_response = self.client.post(
            reverse("panel_user_activate", args=[user_obj.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(activate_response.status_code, 204)
        user_obj.refresh_from_db()
        self.assertTrue(user_obj.is_active)

    def test_user_activate_and_deactivate_require_change_permission(self) -> None:
        """As ações rápidas devem respeitar a permissão de alteração do usuário."""

        self._login_with_permissions("view_user")
        user_obj = User.objects.create_user(
            username="bloqueado",
            email="bloqueado@example.com",
            password="SenhaSegura@123",
        )

        deactivate_response = self.client.post(reverse("panel_user_deactivate", args=[user_obj.pk]))
        activate_response = self.client.post(reverse("panel_user_activate", args=[user_obj.pk]))

        self.assertEqual(deactivate_response.status_code, 403)
        self.assertEqual(activate_response.status_code, 403)

    def test_user_activate_and_deactivate_reject_get_requests(self) -> None:
        """As ações rápidas de status devem aceitar apenas POST."""

        self._login_with_permissions("change_user")
        user_obj = User.objects.create_user(
            username="somente-post",
            email="somente-post@example.com",
            password="SenhaSegura@123",
        )

        deactivate_response = self.client.get(reverse("panel_user_deactivate", args=[user_obj.pk]))
        activate_response = self.client.get(reverse("panel_user_activate", args=[user_obj.pk]))

        self.assertEqual(deactivate_response.status_code, 405)
        self.assertEqual(activate_response.status_code, 405)

    def test_user_delete_requires_delete_permission(self) -> None:
        """A exclusão deve respeitar a permissão de delete do usuário."""

        self._login_with_permissions("view_user")
        user_obj = User.objects.create_user(
            username="sem-delete",
            email="sem-delete@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.get(reverse("panel_user_delete", args=[user_obj.pk]))

        self.assertEqual(response.status_code, 403)

    def test_user_delete_confirmation_renders_for_common_user(self) -> None:
        """A tela de confirmação deve abrir para um usuário comum."""

        self._login_with_permissions("delete_user")
        user_obj = User.objects.create_user(
            username="descartavel",
            email="descartavel@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.get(reverse("panel_user_delete", args=[user_obj.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-page-title="Excluir usuário: descartavel"',
            html=False,
        )
        self.assertContains(response, "Esta ação remove o usuário do painel.")
        self.assertContains(response, "Excluir usuário")

    def test_user_delete_removes_common_user(self) -> None:
        """Usuários comuns podem ser excluídos pelo painel com POST."""

        self._login_with_permissions("delete_user")
        user_obj = User.objects.create_user(
            username="remover",
            email="remover@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.post(
            reverse("panel_user_delete", args=[user_obj.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=user_obj.pk).exists())

    def test_common_user_routes_reject_staff_accounts(self) -> None:
        """A área comum não deve editar nem excluir contas administrativas."""

        self._login_with_permissions("change_user", "delete_user")
        staff_user = User.objects.create_user(
            username="staff-restrito",
            email="staff-restrito@example.com",
            password="SenhaSegura@123",
            is_staff=True,
        )

        update_response = self.client.get(
            reverse("panel_user_update", args=[staff_user.pk]),
        )
        password_reset_response = self.client.get(
            reverse("panel_user_send_password_reset", args=[staff_user.pk]),
        )
        delete_response = self.client.get(
            reverse("panel_user_delete", args=[staff_user.pk]),
        )

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(password_reset_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)

    def test_users_list_disables_actions_for_profile_above_operator_scope(self) -> None:
        """A listagem deve manter visível, porém travado, um perfil acima do operador."""

        self._login_with_permissions("view_user", "change_user", "delete_user")
        blocked_group = Group.objects.create(name="Gestão total")
        blocked_group.permissions.add(Permission.objects.get(codename="delete_group"))
        restricted_user = User.objects.create_user(
            username="perfil-superior",
            email="perfil-superior@example.com",
            password="SenhaSegura@123",
        )
        restricted_user.groups.add(blocked_group)

        response = self.client.get(reverse("panel_users_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "perfil-superior")
        self.assertContains(
            response,
            'data-teste="user-edit-disabled"',
            html=False,
        )
        self.assertContains(
            response,
            "Você não pode criar ou editar um perfil com autonomia maior do que a da sua própria conta.",
        )
        self.assertNotContains(
            response,
            reverse("panel_user_update", args=[restricted_user.pk]),
        )

    def test_user_update_rejects_profile_above_operator_scope(self) -> None:
        """O operador não pode editar um usuário com autonomia acima da sua conta."""

        self._login_with_permissions("change_user")
        blocked_group = Group.objects.create(name="Financeiro total")
        blocked_group.permissions.add(Permission.objects.get(codename="delete_group"))
        restricted_user = User.objects.create_user(
            username="usuario-superior",
            email="usuario-superior@example.com",
            password="SenhaSegura@123",
        )
        restricted_user.groups.add(blocked_group)

        response = self.client.get(
            reverse("panel_user_update", args=[restricted_user.pk]),
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_groups_list_excludes_protected_groups(self) -> None:
        """A listagem de grupos deve ocultar grupos protegidos do painel."""

        self._login_with_permissions("view_group")
        Group.objects.create(name="Root")
        Group.objects.create(name="Analistas")

        response = self.client.get(reverse("panel_groups_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analistas")
        self.assertNotContains(response, "Root")

    def test_groups_list_renders_disabled_actions_without_management_permissions(self) -> None:
        """A listagem deve manter ações visíveis, porém desabilitadas, em modo leitura."""

        self._login_with_permissions("view_group")
        Group.objects.create(name="Analistas")

        response = self.client.get(reverse("panel_groups_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-teste="groups-create-disabled"', html=False)
        self.assertContains(response, 'data-teste="group-edit-disabled"', html=False)
        self.assertContains(response, 'data-teste="group-delete-disabled"', html=False)

    def test_groups_list_renders_enabled_actions_with_management_permissions(self) -> None:
        """A listagem deve expor editar e excluir quando o operador puder gerenciar grupos."""

        self._login_with_permissions("view_group", "add_group", "change_group", "delete_group")
        Group.objects.create(name="Analistas")

        response = self.client.get(reverse("panel_groups_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-teste="groups-create-link"', html=False)
        self.assertContains(response, 'data-teste="group-edit-link"', html=False)
        self.assertContains(response, 'data-teste="group-delete-link"', html=False)

    def test_group_create_htmx_creates_group_and_permissions(self) -> None:
        """Criar grupo via HTMX deve persistir permissões e redirecionar."""

        self._login_with_permissions("add_group")
        permission = Permission.objects.get(codename="add_group")

        response = self.client.post(
            reverse("panel_group_create"),
            {
                "name": "Suporte",
                "permissions": [str(permission.pk)],
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_groups_list"))

        group = Group.objects.get(name="Suporte")
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())

    def test_group_create_rejects_permissions_above_operator_scope(self) -> None:
        """O operador não pode criar grupo com permissão acima da própria conta."""

        self._login_with_permissions("add_group")
        blocked_permission = Permission.objects.get(codename="delete_user")

        response = self.client.post(
            reverse("panel_group_create"),
            {
                "name": "Grupo acima do teto",
                "permissions": [str(blocked_permission.pk)],
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Faça uma escolha válida.")
        self.assertFalse(Group.objects.filter(name="Grupo acima do teto").exists())

    def test_group_delete_requires_delete_permission(self) -> None:
        """A exclusão deve respeitar a permissão de delete do grupo."""

        self._login_with_permissions("view_group")
        group = Group.objects.create(name="Descartável")

        response = self.client.get(reverse("panel_group_delete", args=[group.pk]))

        self.assertEqual(response.status_code, 403)

    def test_group_delete_confirmation_renders_for_editable_group(self) -> None:
        """A confirmação deve abrir para grupos editáveis do painel."""

        self._login_with_permissions("delete_group")
        group = Group.objects.create(name="Legado")

        response = self.client.get(reverse("panel_group_delete", args=[group.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-page-title="Excluir grupo: Legado"',
            html=False,
        )
        self.assertContains(response, "Esta ação remove o grupo do painel.")
        self.assertContains(response, "Excluir grupo")

    def test_group_delete_removes_editable_group(self) -> None:
        """Grupos editáveis podem ser excluídos com POST pelo painel."""

        self._login_with_permissions("delete_group")
        group = Group.objects.create(name="Temporário")

        response = self.client.post(
            reverse("panel_group_delete", args=[group.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_group_delete_rejects_protected_group(self) -> None:
        """Grupos protegidos continuam fora da superfície de exclusão do painel."""

        self._login_with_permissions("delete_group")
        protected_group = Group.objects.create(name="Root")

        response = self.client.get(reverse("panel_group_delete", args=[protected_group.pk]))

        self.assertEqual(response.status_code, 404)

    def test_groups_list_disables_actions_for_group_above_operator_scope(self) -> None:
        """A listagem deve desabilitar ações quando o grupo exceder o operador."""

        self._login_with_permissions("view_group", "change_group", "delete_group")
        restricted_group = Group.objects.create(name="Grupo superior")
        restricted_group.permissions.add(Permission.objects.get(codename="delete_user"))

        response = self.client.get(reverse("panel_groups_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grupo superior")
        self.assertContains(
            response,
            'data-teste="group-edit-disabled"',
            html=False,
        )
        self.assertContains(
            response,
            "Você não pode atribuir ao grupo permissões que a sua própria conta não possui.",
        )
        self.assertNotContains(
            response,
            reverse("panel_group_update", args=[restricted_group.pk]),
        )

    def test_group_update_rejects_group_above_operator_scope(self) -> None:
        """O operador não pode editar grupo com permissões acima da própria conta."""

        self._login_with_permissions("change_group")
        restricted_group = Group.objects.create(name="Grupo inacessível")
        restricted_group.permissions.add(Permission.objects.get(codename="delete_user"))

        response = self.client.get(
            reverse("panel_group_update", args=[restricted_group.pk]),
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )
