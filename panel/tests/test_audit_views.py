"""Testes da tela HTML de auditoria do painel."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from core.models import AuditLog
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class PanelAuditViewTests(TestCase):
    """Valida permissão e filtros da auditoria HTML."""

    def _login_with_audit_permission(self) -> AbstractUser:
        """Autentica um operador com acesso de leitura aos logs."""

        user = User.objects.create_user(
            username="operador-auditoria",
            email="operador-auditoria@example.com",
            password="SenhaSegura@123",
        )
        user.user_permissions.add(Permission.objects.get(codename="view_auditlog"))
        self.client.force_login(user)
        AuditLog.objects.all().delete()
        return user

    def _create_audit_log(
        self,
        *,
        action: str,
        actor: Any,
        actor_identifier: str,
        object_repr: str,
        request_id: str,
        created_at: datetime,
    ) -> AuditLog:
        """Cria um log manual para cenários de listagem e filtros."""

        audit_log = AuditLog.objects.create(
            action=action,
            actor=actor,
            actor_identifier=actor_identifier,
            object_repr=object_repr,
            object_verbose_name="Evento",
            request_method="GET",
            path="/painel/auditoria/",
            metadata={"request_id": request_id},
        )
        AuditLog.objects.filter(pk=audit_log.pk).update(created_at=created_at)
        audit_log.refresh_from_db()
        return audit_log

    def test_audit_list_requires_view_permission(self) -> None:
        """Usuário autenticado sem permissão não pode consultar auditoria."""

        user = User.objects.create_user(
            username="sem-permissao",
            email="sem-permissao@example.com",
            password="SenhaSegura@123",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("panel_audit_logs_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_audit_detail_requires_view_permission(self) -> None:
        """Usuário sem permissão também não pode abrir o drill-down."""

        audit_log = AuditLog.objects.create(
            action=AuditLog.ACTION_LOGIN,
            actor_identifier="sem-permissao",
            object_repr="Login bloqueado",
        )
        user = User.objects.create_user(
            username="sem-permissao",
            email="sem-permissao@example.com",
            password="SenhaSegura@123",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("panel_audit_log_detail", args=[audit_log.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_audit_list_filters_results_and_renders_partial_for_htmx(self) -> None:
        """A listagem deve combinar filtros e responder com partial no HTMX."""

        actor = self._login_with_audit_permission()
        now = timezone.now()
        today = timezone.localdate(now).isoformat()
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor=actor,
            actor_identifier=actor.username,
            object_repr="Login do operador",
            request_id="req-match",
            created_at=now,
        )
        self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor=actor,
            actor_identifier=actor.username,
            object_repr="Atualização de grupo",
            request_id="req-update",
            created_at=now,
        )
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor=None,
            actor_identifier="legacy-user",
            object_repr="Login antigo",
            request_id="req-old",
            created_at=now - timedelta(days=2),
        )

        response = self.client.get(
            reverse("panel_audit_logs_list"),
            {
                "actor": actor.username,
                "action": AuditLog.ACTION_LOGIN,
                "object_query": "req-match",
                "date_from": today,
                "date_to": today,
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Auditoria"', html=False)
        self.assertContains(response, "Login do operador")
        self.assertNotContains(response, "Atualização de grupo")
        self.assertNotContains(response, "Login antigo")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_audit_list_shows_validation_error_for_invalid_date_range(self) -> None:
        """Data final anterior à inicial deve aparecer como erro do filtro."""

        self._login_with_audit_permission()

        response = self.client.get(
            reverse("panel_audit_logs_list"),
            {
                "date_from": "2026-04-10",
                "date_to": "2026-04-01",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "A data final precisa ser igual ou posterior à data inicial.",
        )

    def test_audit_detail_renders_payloads_and_preserves_back_filters(self) -> None:
        """O detalhe deve exibir drill-down e manter o retorno para a lista filtrada."""

        actor = self._login_with_audit_permission()
        actor_for_log: Any = actor
        audit_log = AuditLog.objects.create(
            action=AuditLog.ACTION_UPDATE,
            actor=actor_for_log,
            actor_identifier=actor.username,
            object_repr="Usuário alterado",
            object_verbose_name="Usuário",
            object_id="42",
            request_method="PATCH",
            path="/painel/usuarios/42/editar/",
            ip_address="127.0.0.1",
            before={"email": "antes@example.com"},
            after={"email": "depois@example.com"},
            changes={"email": {"before": "antes@example.com", "after": "depois@example.com"}},
            metadata={"request_id": "req-detail"},
        )

        response = self.client.get(
            reverse("panel_audit_log_detail", args=[audit_log.pk]),
            {"actor": actor.username, "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuário alterado")
        self.assertContains(response, "req-detail")
        self.assertContains(response, "&quot;email&quot;: &quot;antes@example.com&quot;", html=False)
        self.assertContains(response, "&quot;email&quot;: &quot;depois@example.com&quot;", html=False)
        self.assertContains(
            response,
            reverse("panel_audit_logs_list") + "?actor=operador-auditoria&amp;page=2",
            html=False,
        )

    def test_audit_detail_returns_partial_for_htmx(self) -> None:
        """O detalhe deve devolver só o conteúdo central quando for HTMX."""

        actor = self._login_with_audit_permission()
        audit_log = self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor=actor,
            actor_identifier=actor.username,
            object_repr="Evento HTMX",
            request_id="req-htmx",
            created_at=timezone.now(),
        )

        response = self.client.get(
            reverse("panel_audit_log_detail", args=[audit_log.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Detalhe da auditoria"', html=False)
        self.assertContains(response, "Evento HTMX")
        self.assertNotContains(response, "<!doctype html>", html=False)

    def test_audit_detail_returns_404_for_unknown_event(self) -> None:
        """A abertura de um log inexistente deve responder 404."""

        self._login_with_audit_permission()

        response = self.client.get(reverse("panel_audit_log_detail", args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_audit_list_shows_richer_pagination_controls(self) -> None:
        """A listagem deve mostrar contagem e paginação numerada quando houver mais páginas."""

        actor = self._login_with_audit_permission()
        now = timezone.now()

        with patch("panel.audit.views.AUDIT_PAGE_SIZE", 2):
            for index in range(5):
                self._create_audit_log(
                    action=AuditLog.ACTION_LOGIN,
                    actor=actor,
                    actor_identifier=actor.username,
                    object_repr=f"Evento {index}",
                    request_id=f"req-{index}",
                    created_at=now - timedelta(minutes=index),
                )

            response = self.client.get(reverse("panel_audit_logs_list"), {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exibindo 3-4 de 5 eventos.")
        self.assertContains(response, "?page=1", html=False)
        self.assertContains(response, "?page=3", html=False)
        self.assertContains(response, ">2<", html=False)

    def test_audit_list_exposes_export_links_with_current_filters(self) -> None:
        """A listagem deve expor exportações CSV/JSON preservando a query atual."""

        actor = self._login_with_audit_permission()
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor=actor,
            actor_identifier=actor.username,
            object_repr="Evento exportável",
            request_id="req-export-link",
            created_at=timezone.now(),
        )

        response = self.client.get(
            reverse("panel_audit_logs_list"),
            {"actor": actor.username, "object_query": "req-export-link"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("panel_audit_logs_export_csv")
            + "?actor=operador-auditoria&amp;object_query=req-export-link",
            html=False,
        )
        self.assertContains(
            response,
            reverse("panel_audit_logs_export_json")
            + "?actor=operador-auditoria&amp;object_query=req-export-link",
            html=False,
        )

    def test_audit_csv_export_respects_filters(self) -> None:
        """A exportação CSV deve reaproveitar os filtros da listagem HTML."""

        actor = self._login_with_audit_permission()
        now = timezone.now()
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor=actor,
            actor_identifier=actor.username,
            object_repr="Evento exportado",
            request_id="req-export-match",
            created_at=now,
        )
        self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor=actor,
            actor_identifier=actor.username,
            object_repr="Evento fora do filtro",
            request_id="req-export-skip",
            created_at=now,
        )

        response = self.client.get(
            reverse("panel_audit_logs_export_csv"),
            {"object_query": "req-export-match"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("Evento exportado", content)
        self.assertNotIn("Evento fora do filtro", content)
        self.assertIn("request_id", content)

    def test_audit_json_export_includes_filters_and_payload(self) -> None:
        """A exportação JSON deve incluir metadados do filtro e os resultados serializados."""

        actor = self._login_with_audit_permission()
        actor_for_log: Any = actor
        audit_log = AuditLog.objects.create(
            action=AuditLog.ACTION_UPDATE,
            actor=actor_for_log,
            actor_identifier=actor.username,
            object_repr="Evento JSON",
            object_verbose_name="Usuário",
            request_method="PATCH",
            path="/painel/usuarios/7/editar/",
            before={"email": "antes@example.com"},
            after={"email": "depois@example.com"},
            changes={"email": {"before": "antes@example.com", "after": "depois@example.com"}},
            metadata={"request_id": "req-export-json"},
        )

        response = self.client.get(
            reverse("panel_audit_logs_export_json"),
            {"actor": actor.username, "action": AuditLog.ACTION_UPDATE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["filters"]["actor"], actor.username)
        self.assertEqual(payload["filters"]["action"], AuditLog.ACTION_UPDATE)
        self.assertEqual(payload["results"][0]["id"], audit_log.pk)
        self.assertEqual(payload["results"][0]["request_id"], "req-export-json")
        self.assertEqual(
            payload["results"][0]["changes"]["email"]["after"],
            "depois@example.com",
        )

    def test_audit_export_returns_400_for_invalid_filters(self) -> None:
        """Filtros inválidos não devem gerar exportação silenciosa."""

        self._login_with_audit_permission()

        response = self.client.get(
            reverse("panel_audit_logs_export_csv"),
            {
                "date_from": "2026-04-10",
                "date_to": "2026-04-01",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Filtros inválidos para exportação.",
            status_code=400,
        )
        self.assertContains(
            response,
            "A data final precisa ser igual ou posterior à data inicial.",
            status_code=400,
        )
