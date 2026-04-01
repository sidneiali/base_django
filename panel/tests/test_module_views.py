"""Testes dos fluxos HTML de módulos no painel."""

from __future__ import annotations

import json

from core.models import Module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PanelModuleViewTests(TestCase):
    """Valida permissões e fluxos HTMX dos módulos no painel."""

    def _login_with_permissions(self, *codenames: str) -> None:
        """Autentica um operador com permissões de módulos do app core."""

        user = User.objects.create_user(
            username="operador-modulos",
            email="operador-modulos@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(
            Permission.objects.filter(
                content_type__app_label="core",
                codename__in=codenames,
            )
        )
        user.user_permissions.add(*permissions)
        self.client.force_login(user)

    def test_modules_list_requires_view_permission(self) -> None:
        """Usuário autenticado sem permissão não pode listar módulos."""

        self._login_with_permissions()

        response = self.client.get(reverse("panel_modules_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_modules_list_filters_results_and_renders_partial_for_htmx(self) -> None:
        """A listagem deve filtrar módulos por texto e devolver partial no HTMX."""

        self._login_with_permissions("view_module")
        Module.objects.create(
            name="Financeiro",
            slug="financeiro",
            description="Painel financeiro",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )
        Module.objects.create(
            name="CRM",
            slug="crm",
            description="Relacionamento com clientes",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=20,
            is_active=True,
        )

        response = self.client.get(
            reverse("panel_modules_list"),
            {"q": "fin"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Módulos"', html=False)
        self.assertContains(response, "Financeiro")
        self.assertNotContains(response, "CRM")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_module_create_htmx_creates_module_and_redirects(self) -> None:
        """Criar módulo via HTMX deve persistir e responder com HX-Location."""

        self._login_with_permissions("add_module")
        permission = Permission.objects.get(
            content_type__app_label="core",
            codename="view_auditlog",
        )

        response = self.client.post(
            reverse("panel_module_create"),
            {
                "name": "Logs avançados",
                "slug": "logs-avancados",
                "description": "Acesso detalhado aos eventos",
                "icon": "ti ti-history",
                "url_name": "panel_audit_logs_list",
                "menu_group": "Segurança",
                "order": "45",
                "is_active": "on",
                "permission": str(permission.pk),
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        payload = json.loads(response["HX-Location"])
        self.assertEqual(payload["path"], reverse("panel_modules_list"))

        module = Module.objects.get(slug="logs-avancados")
        self.assertEqual(module.app_label, "core")
        self.assertEqual(module.permission_codename, "view_auditlog")
        self.assertEqual(module.url_name, "panel_audit_logs_list")
        self.assertTrue(module.is_active)

    def test_module_create_without_htmx_redirects_to_list(self) -> None:
        """Criar módulo sem HTMX deve redirecionar com 302 para a listagem."""

        self._login_with_permissions("add_module")

        response = self.client.post(
            reverse("panel_module_create"),
            {
                "name": "Novidades",
                "slug": "novidades",
                "description": "Painel de novidades",
                "icon": "ti ti-bell",
                "url_name": "module_entry",
                "menu_group": "Comunicação",
                "order": "15",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("panel_modules_list"))
        self.assertTrue(Module.objects.filter(slug="novidades").exists())

    def test_module_create_rejects_invalid_route_name(self) -> None:
        """O formulário deve bloquear rotas inexistentes ou que peçam argumentos."""

        self._login_with_permissions("add_module")

        response = self.client.post(
            reverse("panel_module_create"),
            {
                "name": "Destino quebrado",
                "slug": "destino-quebrado",
                "description": "Teste",
                "icon": "ti ti-alert-triangle",
                "url_name": "admin:app_list",
                "menu_group": "Teste",
                "order": "10",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Informe um nome de rota válido sem argumentos obrigatórios.",
        )
        self.assertFalse(Module.objects.filter(slug="destino-quebrado").exists())

    def test_module_create_invalid_htmx_keeps_form_without_redirect(self) -> None:
        """Submissão inválida via HTMX deve rerenderizar o fragmento do form."""

        self._login_with_permissions("add_module")

        response = self.client.post(
            reverse("panel_module_create"),
            {
                "name": "",
                "slug": "sem-nome",
                "description": "Teste",
                "icon": "ti ti-alert-triangle",
                "url_name": "module_entry",
                "menu_group": "Teste",
                "order": "10",
                "is_active": "on",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Location", response.headers)
        self.assertContains(response, 'data-page-title="Novo módulo"', html=False)
        self.assertContains(response, "Este campo é obrigatório.")

    def test_module_update_can_switch_to_generic_entry_and_clear_permission(self) -> None:
        """A edição deve permitir voltar para a entrada genérica sem permissão."""

        self._login_with_permissions("change_module")
        module = Module.objects.create(
            name="Auditoria operacional",
            slug="auditoria-operacional",
            description="Área pronta",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=30,
            is_active=True,
        )

        response = self.client.post(
            reverse("panel_module_update", args=[module.pk]),
            {
                "name": "Auditoria operacional",
                "slug": "auditoria-operacional",
                "description": "Área em reorganização",
                "icon": "ti ti-history",
                "url_name": "module_entry",
                "menu_group": "Segurança",
                "order": "35",
                "permission": "",
                "is_active": "on",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        module.refresh_from_db()
        self.assertTrue(module.uses_generic_entry)
        self.assertEqual(module.app_label, "")
        self.assertEqual(module.permission_codename, "")
        self.assertEqual(module.order, 35)

    def test_module_update_without_htmx_redirects_to_list(self) -> None:
        """Edição sem HTMX deve redirecionar para a listagem."""

        self._login_with_permissions("change_module")
        module = Module.objects.create(
            name="Operação",
            slug="operacao",
            description="Área operacional",
            icon="ti ti-settings",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )

        response = self.client.post(
            reverse("panel_module_update", args=[module.pk]),
            {
                "name": "Operação revisada",
                "slug": "operacao",
                "description": "Área operacional revisada",
                "icon": "ti ti-settings",
                "url_name": "module_entry",
                "menu_group": "Operação",
                "order": "12",
                "is_active": "on",
                "permission": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("panel_modules_list"))
        module.refresh_from_db()
        self.assertEqual(module.name, "Operação revisada")

    def test_module_deactivate_and_activate_toggle_state(self) -> None:
        """A listagem deve permitir inativar e reativar módulos com POST."""

        self._login_with_permissions("change_module")
        module = Module.objects.create(
            name="Expedição",
            slug="expedicao",
            description="Fluxo de saída",
            icon="ti ti-truck",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )

        deactivate_response = self.client.post(
            reverse("panel_module_deactivate", args=[module.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(deactivate_response.status_code, 204)
        module.refresh_from_db()
        self.assertFalse(module.is_active)

        activate_response = self.client.post(
            reverse("panel_module_activate", args=[module.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(activate_response.status_code, 204)
        module.refresh_from_db()
        self.assertTrue(module.is_active)

    def test_module_activate_and_deactivate_require_change_permission(self) -> None:
        """Ações rápidas devem respeitar a permissão de alteração do módulo."""

        self._login_with_permissions()
        module = Module.objects.create(
            name="Pedidos",
            slug="pedidos",
            description="Fluxo de pedidos",
            icon="ti ti-shopping-cart",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )

        deactivate_response = self.client.post(reverse("panel_module_deactivate", args=[module.pk]))
        activate_response = self.client.post(reverse("panel_module_activate", args=[module.pk]))

        self.assertEqual(deactivate_response.status_code, 403)
        self.assertEqual(activate_response.status_code, 403)

    def test_module_activate_and_deactivate_reject_get_requests(self) -> None:
        """As ações rápidas devem aceitar apenas POST."""

        self._login_with_permissions("change_module")
        module = Module.objects.create(
            name="Pedidos",
            slug="pedidos",
            description="Fluxo de pedidos",
            icon="ti ti-shopping-cart",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )

        deactivate_response = self.client.get(reverse("panel_module_deactivate", args=[module.pk]))
        activate_response = self.client.get(reverse("panel_module_activate", args=[module.pk]))

        self.assertEqual(deactivate_response.status_code, 405)
        self.assertEqual(activate_response.status_code, 405)

    def test_module_delete_blocks_canonical_seed_module(self) -> None:
        """Módulos canônicos não podem ser excluídos pelo painel."""

        self._login_with_permissions("delete_module")
        module = Module.objects.create(
            name="Módulos",
            slug="modulos",
            description="Cadastro canônico",
            icon="ti ti-layout-grid",
            url_name="panel_modules_list",
            app_label="core",
            permission_codename="view_module",
            menu_group="Configurações",
            order=20,
            is_active=False,
        )

        response = self.client.post(reverse("panel_module_delete", args=[module.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Módulos canônicos do seed não podem ser excluídos pelo painel.",
            status_code=400,
        )
        self.assertTrue(Module.objects.filter(pk=module.pk).exists())

    def test_module_delete_requires_delete_permission(self) -> None:
        """A confirmação de exclusão deve respeitar a permissão de delete."""

        self._login_with_permissions()
        module = Module.objects.create(
            name="Descartável",
            slug="descartavel",
            description="Módulo temporário",
            icon="ti ti-trash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Teste",
            order=10,
            is_active=False,
        )

        response = self.client.get(reverse("panel_module_delete", args=[module.pk]))

        self.assertEqual(response.status_code, 403)

    def test_module_delete_requires_inactive_module(self) -> None:
        """A exclusão deve ser bloqueada enquanto o módulo ainda estiver ativo."""

        self._login_with_permissions("delete_module")
        module = Module.objects.create(
            name="CRM legado",
            slug="crm-legado",
            description="Módulo em retirada",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Comercial",
            order=30,
            is_active=True,
        )

        response = self.client.post(reverse("panel_module_delete", args=[module.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Inative o módulo antes de solicitar a exclusão.",
            status_code=400,
        )
        self.assertTrue(Module.objects.filter(pk=module.pk).exists())

    def test_module_delete_confirmation_renders_for_inactive_custom_module(self) -> None:
        """A tela de confirmação deve abrir quando a exclusão for permitida."""

        self._login_with_permissions("delete_module")
        module = Module.objects.create(
            name="Arquivo morto",
            slug="arquivo-morto",
            description="Módulo descontinuado",
            icon="ti ti-archive",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Legado",
            order=50,
            is_active=False,
        )

        response = self.client.get(reverse("panel_module_delete", args=[module.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Excluir módulo: Arquivo morto"', html=False)
        self.assertContains(response, "Esta ação remove o módulo do dashboard e do sidebar.")
        self.assertContains(response, "Excluir módulo")

    def test_module_delete_removes_inactive_custom_module(self) -> None:
        """Módulos customizados e inativos podem ser excluídos com segurança."""

        self._login_with_permissions("delete_module")
        module = Module.objects.create(
            name="Campanhas antigas",
            slug="campanhas-antigas",
            description="Módulo descontinuado",
            icon="ti ti-speakerphone",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Marketing",
            order=40,
            is_active=False,
        )

        response = self.client.post(
            reverse("panel_module_delete", args=[module.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Module.objects.filter(pk=module.pk).exists())
