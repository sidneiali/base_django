"""Testes operacionais e de segurança da API do app panel."""

from __future__ import annotations

import json

from core.models import (
    ApiResourcePermission,
    AuditLog,
)
from core.tests.factories import GroupFactory, ModuleFactory, UserFactory
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .api_test_support import (
    HasPk,
    PanelApiResourceCase,
    PanelApiTokenMixin,
    build_panel_api_resource_cases,
)

User = get_user_model()


class PanelApiOperationalTests(PanelApiTokenMixin, TestCase):
    """Valida cenários operacionais e falhas padronizadas da API do painel."""

    def _create_user_target(self) -> HasPk:
        """Cria um usuário comum editável pela API."""

        return UserFactory.create(
            username=f"target-user-{User.objects.count()}",
            email=f"target-user-{User.objects.count()}@example.com",
            password="SenhaSegura@123",
        )

    def _create_group_target(self) -> HasPk:
        """Cria um grupo editável pela API."""

        return GroupFactory.create()

    def _create_module_target(self) -> HasPk:
        """Cria um módulo customizado seguro para edição e exclusão."""

        return ModuleFactory.create(
            is_active=False,
        )

    def _resource_cases(self) -> tuple[PanelApiResourceCase, ...]:
        """Retorna os recursos do painel com URLs e payloads representativos."""

        return build_panel_api_resource_cases(
            user_factory=self._create_user_target,
            group_factory=self._create_group_target,
            module_factory=self._create_module_target,
        )

    def test_collection_post_requires_create_permission_for_each_resource(self) -> None:
        """POST da coleção deve bloquear tokens sem a flag de criação."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_read=True,
                )

                response = self.client.post(
                    case.collection_url,
                    data=json.dumps(case.create_payload),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_detail_patch_requires_update_permission_for_each_resource(self) -> None:
        """PATCH do detalhe deve bloquear tokens sem a flag de atualização."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                target = case.factory()
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_read=True,
                )

                response = self.client.patch(
                    case.detail_url(target.pk),
                    data=json.dumps(case.update_payload),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_detail_delete_requires_delete_permission_for_each_resource(self) -> None:
        """DELETE do detalhe deve bloquear tokens sem a flag de exclusão."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                target = case.factory()
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_read=True,
                )

                response = self.client.delete(
                    case.detail_url(target.pk),
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "forbidden")

    def test_detail_delete_returns_enveloped_success_for_each_resource(self) -> None:
        """DELETE bem-sucedido deve preservar envelope JSON e contexto básico."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                target = case.factory()
                detail_url = case.detail_url(target.pk)
                raw_token = self._issue_raw_token(
                    resource=case.resource,
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
                        "resource": case.resource,
                        "id": target.pk,
                    },
                )
                self.assertEqual(payload["meta"]["method"], "DELETE")
                self.assertEqual(payload["meta"]["path"], detail_url)
                self.assertEqual(payload["meta"]["request_id"], response["X-Request-ID"])

    def test_collection_rejects_invalid_json_for_each_resource(self) -> None:
        """POST da coleção deve rejeitar corpo JSON inválido nos três recursos."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_create=True,
                )

                response = self.client.post(
                    case.collection_url,
                    data="{json-invalido",
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_json")

    def test_collection_rejects_non_object_payload_for_each_resource(self) -> None:
        """POST da coleção deve rejeitar payload JSON que não seja objeto."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_create=True,
                )

                response = self.client.post(
                    case.collection_url,
                    data=json.dumps([case.create_payload]),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_payload")

    def test_collection_put_returns_method_not_allowed_for_each_resource(self) -> None:
        """PUT na coleção deve chegar à view e responder 405 padronizado."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_update=True,
                )

                response = self.client.put(
                    case.collection_url,
                    data=json.dumps(case.update_payload),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_detail_post_returns_method_not_allowed_for_each_resource(self) -> None:
        """POST no detalhe deve responder 405 quando o token puder criar."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                target = case.factory()
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_create=True,
                )

                response = self.client.post(
                    case.detail_url(target.pk),
                    data=json.dumps(case.create_payload),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_detail_returns_not_found_for_unknown_resource_for_each_resource(self) -> None:
        """GET do detalhe deve responder 404 para ids inexistentes."""

        for case in self._resource_cases():
            with self.subTest(resource=case.label):
                raw_token = self._issue_raw_token(
                    resource=case.resource,
                    can_read=True,
                )

                response = self.client.get(
                    case.detail_url(999999),
                    HTTP_AUTHORIZATION=f"Bearer {raw_token}",
                )

                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_forbidden_create_attempt_is_audited_for_panel_modules(self) -> None:
        """Acesso negado de criação em módulos deve gerar trilha auditável."""

        raw_token = self._issue_raw_token(
            resource=ApiResourcePermission.Resource.PANEL_MODULES,
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
