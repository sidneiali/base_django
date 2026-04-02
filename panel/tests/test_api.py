"""Testes dos endpoints JSON do painel."""

import json

from core.models import ApiAccessProfile, ApiResourcePermission, ApiToken, Module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PanelApiTests(TestCase):
    """Valida o primeiro recurso JSON protegido por token da API."""

    def _issue_token(
        self,
        *,
        resource: str = ApiResourcePermission.Resource.PANEL_USERS,
        **permissions,
    ):
        """Cria um usuário da API com token ativo e permissão configurável."""

        user = User.objects.create_user(
            username=permissions.pop("username", "api-client"),
            email="api-client@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=resource,
            **permissions,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return user, raw_token

    def test_users_collection_requires_bearer_token(self):
        """A listagem JSON deve rejeitar chamadas sem Authorization Bearer."""

        response = self.client.get(reverse("api_panel_users_collection"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "missing_authorization")

    def test_users_collection_requires_read_permission(self):
        """O token autenticado ainda precisa ter permissão de leitura."""

        _user, raw_token = self._issue_token()

        response = self.client.get(
            reverse("api_panel_users_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_users_collection_lists_non_superusers_and_updates_last_used(self):
        """A listagem deve autenticar via Bearer e ignorar superusuários."""

        api_user, raw_token = self._issue_token(can_read=True)
        User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="SenhaSegura@123",
        )

        response = self.client.get(
            reverse("api_panel_users_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        usernames = {item["username"] for item in payload["data"]}
        self.assertIn("api-client", usernames)
        self.assertIn("maria", usernames)
        self.assertNotIn("root", usernames)
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 2)
        self.assertEqual(payload["meta"]["ordering"], "username")

        token = ApiToken.objects.get(user=api_user)
        self.assertIsNotNone(token.last_used_at)

    def test_versioned_users_collection_alias_works(self):
        """A rota versionada deve responder com o mesmo recurso de usuários."""

        _api_user, raw_token = self._issue_token(can_read=True)

        response = self.client.get(
            reverse("api_v1_panel_users_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())

    def test_users_collection_supports_filters_ordering_and_pagination(self):
        """A coleção deve aceitar filtros explícitos, ordenação e paginação."""

        _api_user, raw_token = self._issue_token(can_read=True)
        group = Group.objects.create(name="Clientes")
        ana = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="SenhaSegura@123",
            is_active=True,
        )
        ana.groups.add(group)
        User.objects.create_user(
            username="bruno",
            email="bruno@example.com",
            password="SenhaSegura@123",
            is_active=False,
        )

        response = self.client.get(
            reverse("api_panel_users_collection"),
            {
                "is_active": "true",
                "group_id": group.pk,
                "ordering": "-username",
                "page_size": 1,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["ordering"], "-username")
        self.assertEqual(payload["meta"]["filters"]["is_active"], True)
        self.assertEqual(payload["meta"]["filters"]["group_id"], group.pk)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 1)
        self.assertEqual(payload["data"][0]["username"], "ana")

    def test_users_collection_rejects_invalid_query_parameter(self):
        """Filtros inválidos devem retornar erro padronizado."""

        _api_user, raw_token = self._issue_token(can_read=True)

        response = self.client.get(
            reverse("api_panel_users_collection"),
            {"is_active": "talvez"},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"]["code"],
            "invalid_query_parameter",
        )

    def test_users_collection_creates_user_with_create_permission(self):
        """POST deve criar usuário quando o token tiver permissão de criação."""

        _user, raw_token = self._issue_token(can_create=True)

        response = self.client.post(
            reverse("api_panel_users_collection"),
            data=json.dumps(
                {
                    "username": "novo-api",
                    "email": "novo@example.com",
                    "password": "SenhaSegura@123",
                    "is_active": True,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="novo-api").exists())
        self.assertEqual(response.json()["data"]["username"], "novo-api")

    def test_user_detail_updates_and_deletes_with_crud_permissions(self):
        """PATCH e DELETE devem respeitar o token com update/delete."""

        _user, raw_token = self._issue_token(can_update=True, can_delete=True)
        target = User.objects.create_user(
            username="alvo-api",
            email="alvo@example.com",
            password="SenhaSegura@123",
        )
        detail_url = reverse("api_panel_user_detail", args=[target.pk])

        update_response = self.client.patch(
            detail_url,
            data=json.dumps({"email": "alterado@example.com"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["email"], "alterado@example.com")
        target.refresh_from_db()
        self.assertEqual(target.email, "alterado@example.com")

        delete_response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())

    def test_groups_collection_requires_read_permission(self):
        """A listagem JSON de grupos também precisa da permissão de leitura."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS
        )

        response = self.client.get(
            reverse("api_panel_groups_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_groups_collection_lists_editable_groups_and_supports_filters(self):
        """A coleção de grupos deve excluir protegidos e aceitar filtros/paginação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )
        permission = Permission.objects.get(codename="view_user")
        clientes = Group.objects.create(name="Clientes")
        clientes.permissions.add(permission)
        Group.objects.create(name="Root")
        Group.objects.create(name="Financeiro")

        response = self.client.get(
            reverse("api_panel_groups_collection"),
            {
                "search": "clien",
                "permission_id": permission.pk,
                "ordering": "-name",
                "page_size": 1,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["ordering"], "-name")
        self.assertEqual(payload["meta"]["filters"]["search"], "clien")
        self.assertEqual(payload["meta"]["filters"]["permission_id"], permission.pk)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 1)
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 1)
        self.assertEqual(payload["data"][0]["name"], "Clientes")
        self.assertEqual(payload["data"][0]["permissions_count"], 1)
        self.assertEqual(payload["data"][0]["permissions"][0]["codename"], "view_user")

    def test_groups_collection_rejects_invalid_query_parameter(self):
        """Filtros inválidos da coleção de grupos devem falhar com erro padronizado."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_panel_groups_collection"),
            {"permission_id": "talvez"},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_query_parameter")

    def test_groups_collection_creates_group_with_permissions(self):
        """POST deve criar grupo editável quando o token tiver permissão de criação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_create=True,
        )
        permission = Permission.objects.get(codename="view_user")

        response = self.client.post(
            reverse("api_panel_groups_collection"),
            data=json.dumps(
                {
                    "name": "Suporte API",
                    "permissions": [permission.pk],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        group = Group.objects.get(name="Suporte API")
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
        self.assertEqual(response.json()["data"]["permissions_count"], 1)

    def test_groups_collection_rejects_protected_group_name(self):
        """A criação deve bloquear nomes reservados do painel."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_create=True,
        )

        response = self.client.post(
            reverse("api_panel_groups_collection"),
            data=json.dumps({"name": "Root"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_group_detail_reads_updates_and_deletes(self):
        """GET, PATCH e DELETE devem funcionar para grupos editáveis."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
            can_update=True,
            can_delete=True,
        )
        permission = Permission.objects.get(codename="view_user")
        group = Group.objects.create(name="Parceiros")
        detail_url = reverse("api_panel_group_detail", args=[group.pk])

        read_response = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["data"]["name"], "Parceiros")

        update_response = self.client.patch(
            detail_url,
            data=json.dumps({"name": "Parceiros VIP", "permissions": [permission.pk]}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(update_response.status_code, 200)
        group.refresh_from_db()
        self.assertEqual(group.name, "Parceiros VIP")
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())

        delete_response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_group_detail_returns_404_for_protected_group(self):
        """Grupos protegidos não devem ficar expostos na API do painel."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )
        group = Group.objects.create(name="Root")

        response = self.client.get(
            reverse("api_panel_group_detail", args=[group.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_versioned_groups_collection_alias_works(self):
        """A rota versionada também deve responder para grupos do painel."""

        _api_user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_GROUPS,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_v1_panel_groups_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())

    def test_modules_collection_requires_read_permission(self):
        """A listagem JSON de módulos também precisa da permissão de leitura."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES
        )

        response = self.client.get(
            reverse("api_panel_modules_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_modules_collection_lists_and_filters_modules(self):
        """A coleção de módulos deve aceitar filtros explícitos e paginação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )
        permission = Permission.objects.get(codename="view_auditlog")
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
            name="Auditoria avançada",
            slug="auditoria-avancada",
            description="Eventos detalhados",
            icon="ti ti-history",
            url_name="panel_audit_logs_list",
            app_label="core",
            permission_codename="view_auditlog",
            menu_group="Segurança",
            order=20,
            is_active=False,
        )

        response = self.client.get(
            reverse("api_panel_modules_collection"),
            {
                "search": "auditoria",
                "permission_id": permission.pk,
                "is_active": "false",
                "ordering": "-name",
                "page_size": 1,
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["ordering"], "-name")
        self.assertEqual(payload["meta"]["filters"]["search"], "auditoria")
        self.assertEqual(payload["meta"]["filters"]["permission_id"], permission.pk)
        self.assertEqual(payload["meta"]["filters"]["is_active"], False)
        self.assertEqual(payload["meta"]["pagination"]["page_size"], 1)
        self.assertEqual(payload["meta"]["pagination"]["total_items"], 1)
        self.assertEqual(payload["data"][0]["slug"], "auditoria-avancada")
        self.assertEqual(payload["data"][0]["permission"]["codename"], "view_auditlog")
        self.assertEqual(
            payload["data"][0]["resolved_url"],
            reverse("panel_audit_logs_list"),
        )

    def test_modules_collection_rejects_invalid_query_parameter(self):
        """Filtros inválidos da coleção de módulos devem falhar com erro padronizado."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_panel_modules_collection"),
            {"is_active": "talvez"},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_query_parameter")

    def test_modules_collection_creates_module_with_permission(self):
        """POST deve criar módulo quando o token tiver permissão de criação."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_create=True,
        )
        permission = Permission.objects.get(codename="view_group")

        response = self.client.post(
            reverse("api_panel_modules_collection"),
            data=json.dumps(
                {
                    "name": "Gestão de grupos",
                    "slug": "gestao-de-grupos",
                    "description": "API de grupos no painel",
                    "icon": "ti ti-users-group",
                    "url_name": "panel_groups_list",
                    "menu_group": "Segurança",
                    "order": 25,
                    "is_active": True,
                    "show_in_dashboard": True,
                    "show_in_sidebar": False,
                    "permission": permission.pk,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        module = Module.objects.get(slug="gestao-de-grupos")
        self.assertEqual(module.app_label, "auth")
        self.assertEqual(module.permission_codename, "view_group")
        self.assertTrue(module.show_in_dashboard)
        self.assertFalse(module.show_in_sidebar)
        self.assertEqual(response.json()["data"]["permission"]["id"], permission.pk)

    def test_module_detail_reads_updates_and_deletes(self):
        """GET, PATCH e DELETE devem funcionar para módulos editáveis."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
            can_update=True,
            can_delete=True,
        )
        permission = Permission.objects.get(codename="view_auditlog")
        module = Module.objects.create(
            name="Operação legada",
            slug="operacao-legada",
            description="Área antiga",
            icon="ti ti-settings",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=15,
            is_active=False,
        )
        detail_url = reverse("api_panel_module_detail", args=[module.pk])

        read_response = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["data"]["slug"], "operacao-legada")

        update_response = self.client.patch(
            detail_url,
            data=json.dumps(
                {
                    "name": "Operação auditada",
                    "url_name": "panel_audit_logs_list",
                    "permission": permission.pk,
                    "is_active": True,
                    "show_in_dashboard": False,
                    "show_in_sidebar": True,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(update_response.status_code, 200)
        module.refresh_from_db()
        self.assertEqual(module.name, "Operação auditada")
        self.assertEqual(module.url_name, "panel_audit_logs_list")
        self.assertEqual(module.app_label, "core")
        self.assertEqual(module.permission_codename, "view_auditlog")
        self.assertTrue(module.is_active)
        self.assertFalse(module.show_in_dashboard)
        self.assertTrue(module.show_in_sidebar)

        module.is_active = False
        module.save(update_fields=["is_active"])

        delete_response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Module.objects.filter(pk=module.pk).exists())

    def test_module_detail_blocks_unsafe_delete(self):
        """DELETE deve bloquear módulos ativos ou canônicos do seed."""

        _user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_delete=True,
        )
        active_module = Module.objects.create(
            name="CRM legado",
            slug="crm-legado",
            description="Ainda ativo",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Comercial",
            order=10,
            is_active=True,
        )
        canonical_module = Module.objects.create(
            name="Módulos",
            slug="modulos",
            description="Catálogo canônico",
            icon="ti ti-layout-grid",
            url_name="panel_modules_list",
            app_label="core",
            permission_codename="view_module",
            menu_group="Configurações",
            order=20,
            is_active=False,
        )

        active_response = self.client.delete(
            reverse("api_panel_module_detail", args=[active_module.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        canonical_response = self.client.delete(
            reverse("api_panel_module_detail", args=[canonical_module.pk]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(active_response.status_code, 400)
        self.assertEqual(active_response.json()["error"]["code"], "delete_not_allowed")
        self.assertEqual(canonical_response.status_code, 400)
        self.assertEqual(canonical_response.json()["error"]["code"], "delete_not_allowed")

    def test_versioned_modules_collection_alias_works(self):
        """A rota versionada também deve responder para módulos do painel."""

        _api_user, raw_token = self._issue_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )

        response = self.client.get(
            reverse("api_v1_panel_modules_collection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())
