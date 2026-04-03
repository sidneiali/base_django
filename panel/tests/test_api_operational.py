"""Testes operacionais e de segurança da API do app panel."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol, TypedDict

from core.models import (
    ApiAccessProfile,
    ApiResourcePermission,
    ApiToken,
    AuditLog,
    Module,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class _HasPk(Protocol):
    """Contrato mínimo dos alvos usados nos testes de detalhe da API."""

    pk: int


ResourceFactory = Callable[[], _HasPk]


class ResourceCase(TypedDict):
    """Define um recurso do painel com as superfícies usadas nos testes."""

    label: str
    resource: str
    collection_url: str
    detail_url_name: str
    factory: ResourceFactory
    create_payload: dict[str, object]
    update_payload: dict[str, object]


class PanelApiOperationalTests(TestCase):
    """Valida cenários operacionais e falhas padronizadas da API do painel."""

    def _issue_token(self, resource: str, **permissions: bool) -> str:
        """Cria um token ativo com acesso configurável ao recurso informado."""

        user = User.objects.create_user(
            username=f"api-{resource.rsplit('.', 1)[-1]}-{User.objects.count()}",
            email=f"{resource.rsplit('.', 1)[-1]}@example.com",
            password="SenhaSegura@123",
        )
        access_profile = ApiAccessProfile.objects.create(user=user, api_enabled=True)
        ApiResourcePermission.objects.create(
            access_profile=access_profile,
            resource=resource,
            **permissions,
        )
        _token, raw_token = ApiToken.issue_for_user(user)
        return raw_token

    def _create_user_target(self) -> _HasPk:
        """Cria um usuário comum editável pela API."""

        return User.objects.create_user(
            username=f"target-user-{User.objects.count()}",
            email=f"target-user-{User.objects.count()}@example.com",
            password="SenhaSegura@123",
        )

    def _create_group_target(self) -> _HasPk:
        """Cria um grupo editável pela API."""

        return Group.objects.create(name=f"Grupo {Group.objects.count() + 1}")

    def _create_module_target(self) -> _HasPk:
        """Cria um módulo customizado seguro para edição e exclusão."""

        return Module.objects.create(
            name=f"Módulo {Module.objects.count() + 1}",
            slug=f"modulo-{Module.objects.count() + 1}",
            description="Módulo operacional de teste",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Teste",
            order=10,
            is_active=False,
        )

    def _resource_cases(self) -> list[ResourceCase]:
        """Retorna os recursos do painel com URLs e payloads representativos."""

        return [
            {
                "label": "usuarios",
                "resource": ApiResourcePermission.Resource.PANEL_USERS,
                "collection_url": reverse("api_panel_users_collection"),
                "detail_url_name": "api_panel_user_detail",
                "factory": self._create_user_target,
                "create_payload": {
                    "username": "novo-operacional",
                    "email": "novo-operacional@example.com",
                    "password": "SenhaSegura@123",
                },
                "update_payload": {
                    "email": "atualizado-operacional@example.com",
                },
            },
            {
                "label": "grupos",
                "resource": ApiResourcePermission.Resource.PANEL_GROUPS,
                "collection_url": reverse("api_panel_groups_collection"),
                "detail_url_name": "api_panel_group_detail",
                "factory": self._create_group_target,
                "create_payload": {
                    "name": "Grupo Operacional",
                },
                "update_payload": {
                    "name": "Grupo Operacional Atualizado",
                },
            },
            {
                "label": "modulos",
                "resource": ApiResourcePermission.Resource.PANEL_MODULES,
                "collection_url": reverse("api_panel_modules_collection"),
                "detail_url_name": "api_panel_module_detail",
                "factory": self._create_module_target,
                "create_payload": {
                    "name": "Módulo Operacional",
                    "slug": "modulo-operacional",
                    "url_name": "module_entry",
                },
                "update_payload": {
                    "description": "Módulo atualizado via teste operacional",
                },
            },
        ]

    def test_collection_post_requires_create_permission_for_each_resource(self) -> None:
        """POST da coleção deve bloquear tokens sem a flag de criação."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_read=True,
                )

                response = self.client.post(
                    str(case["collection_url"]),
                    data=json.dumps(case["create_payload"]),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_detail_patch_requires_update_permission_for_each_resource(self) -> None:
        """PATCH do detalhe deve bloquear tokens sem a flag de atualização."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                target = case["factory"]()
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_read=True,
                )

                response = self.client.patch(
                    reverse(str(case["detail_url_name"]), args=[target.pk]),
                    data=json.dumps(case["update_payload"]),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_detail_delete_requires_delete_permission_for_each_resource(self) -> None:
        """DELETE do detalhe deve bloquear tokens sem a flag de exclusão."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                target = case["factory"]()
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_read=True,
                )

                response = self.client.delete(
                    reverse(str(case["detail_url_name"]), args=[target.pk]),
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_detail_delete_returns_enveloped_success_for_each_resource(self) -> None:
        """DELETE bem-sucedido deve preservar envelope JSON e contexto básico."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                target = case["factory"]()
                detail_url = reverse(str(case["detail_url_name"]), args=[target.pk])
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_delete=True,
                )

                response = self.client.delete(
                    detail_url,
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(
                    payload["data"],
                    {
                        "deleted": True,
                        "resource": str(case["resource"]),
                        "id": target.pk,
                    },
                )
                self.assertEqual(payload["meta"]["method"], "DELETE")
                self.assertEqual(payload["meta"]["path"], detail_url)
                self.assertEqual(payload["meta"]["request_id"], response["X-Request-ID"])

    def test_collection_rejects_invalid_json_for_each_resource(self) -> None:
        """POST da coleção deve rejeitar corpo JSON inválido nos três recursos."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_create=True,
                )

                response = self.client.post(
                    str(case["collection_url"]),
                    data="{json-invalido",
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_json")

    def test_collection_rejects_non_object_payload_for_each_resource(self) -> None:
        """POST da coleção deve rejeitar payload JSON que não seja objeto."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_create=True,
                )

                response = self.client.post(
                    str(case["collection_url"]),
                    data=json.dumps([case["create_payload"]]),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_payload")

    def test_collection_put_returns_method_not_allowed_for_each_resource(self) -> None:
        """PUT na coleção deve chegar à view e responder 405 padronizado."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_update=True,
                )

                response = self.client.put(
                    str(case["collection_url"]),
                    data=json.dumps(case["update_payload"]),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_detail_post_returns_method_not_allowed_for_each_resource(self) -> None:
        """POST no detalhe deve responder 405 quando o token puder criar."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                target = case["factory"]()
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_create=True,
                )

                response = self.client.post(
                    reverse(str(case["detail_url_name"]), args=[target.pk]),
                    data=json.dumps(case["create_payload"]),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_detail_returns_not_found_for_unknown_resource_for_each_resource(self) -> None:
        """GET do detalhe deve responder 404 para ids inexistentes."""

        for case in self._resource_cases():
            with self.subTest(resource=case["label"]):
                raw_token = self._issue_token(
                    str(case["resource"]),
                    can_read=True,
                )

                response = self.client.get(
                    reverse(str(case["detail_url_name"]), args=[999999]),
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_forbidden_create_attempt_is_audited_for_panel_modules(self) -> None:
        """Acesso negado de criação em módulos deve gerar trilha auditável."""

        raw_token = self._issue_token(
            ApiResourcePermission.Resource.PANEL_MODULES,
            can_read=True,
        )
        AuditLog.objects.all().delete()

        response = self.client.post(
            reverse("api_panel_modules_collection"),
            data=json.dumps(
                {
                    "name": "Módulo Negado",
                    "slug": "modulo-negado",
                    "url_name": "module_entry",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")

        log = AuditLog.objects.filter(action=AuditLog.ACTION_API_ACCESS_DENIED).first()
        self.assertIsNotNone(log)
        assert log is not None
        self.assertEqual(log.metadata["reason_code"], "forbidden")
        self.assertEqual(log.metadata["resource"], "panel.modules")
        self.assertEqual(log.metadata["action"], "create")
        self.assertEqual(log.metadata["status"], 403)
