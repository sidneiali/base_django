"""Testes dos fluxos HTML de segurança de login no painel."""

from __future__ import annotations

from datetime import timedelta

from axes.models import (  # type: ignore[import-untyped]
    AccessAttempt,
    AccessFailureLog,
    AccessLog,
)
from core.models import AuditLog
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class LoginSecurityViewTests(TestCase):
    """Valida a superfície operacional do django-axes dentro do painel."""

    def _login_with_permissions(self, *codenames: str) -> None:
        """Autentica um operador com o conjunto informado de permissões."""

        user = User.objects.create_user(
            username="operador-seguranca",
            email="operador-seguranca@example.com",
            password="SenhaSegura@123",
        )
        permissions = list(Permission.objects.filter(codename__in=codenames))
        user.user_permissions.add(*permissions)
        self.client.force_login(user)

    def _create_access_attempt(
        self,
        *,
        username: str,
        ip_address: str,
        failures_since_start: int,
        user_agent: str = "Chrome Test",
        path_info: str = "/login/",
    ) -> AccessAttempt:
        """Cria uma tentativa estável do axes para uso em testes HTML."""

        return AccessAttempt.objects.create(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            http_accept="text/html",
            path_info=path_info,
            get_data="next=/",
            post_data="username=test@example.com",
            failures_since_start=failures_since_start,
        )

    def _create_failure_log(
        self,
        *,
        username: str,
        ip_address: str,
        locked_out: bool,
        path_info: str = "/login/",
    ) -> AccessFailureLog:
        """Cria um registro de falha do axes."""

        return AccessFailureLog.objects.create(
            username=username,
            ip_address=ip_address,
            user_agent="Firefox Test",
            http_accept="text/html",
            path_info=path_info,
            locked_out=locked_out,
        )

    def _create_access_log(
        self,
        *,
        username: str,
        ip_address: str,
        path_info: str = "/login/",
    ) -> AccessLog:
        """Cria um registro de acesso do axes."""

        return AccessLog.objects.create(
            username=username,
            ip_address=ip_address,
            user_agent="Edge Test",
            http_accept="text/html",
            path_info=path_info,
        )

    def test_login_security_requires_any_axes_view_permission(self) -> None:
        """Sem permissão de leitura do axes, a página deve negar acesso."""

        self._login_with_permissions()

        response = self.client.get(reverse("panel_login_security_list"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar este recurso.",
            status_code=403,
        )

    def test_login_security_attempts_page_hides_other_sections_without_permissions(self) -> None:
        """Com permissão apenas de tentativas, a página deve ocultar os demais blocos."""

        self._login_with_permissions("view_accessattempt")
        self._create_access_attempt(
            username="somente-attempt@example.com",
            ip_address="10.0.0.10",
            failures_since_start=1,
        )

        response = self.client.get(reverse("panel_login_security_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-teste="login-security-attempts-table"', html=False)
        self.assertNotContains(response, 'data-teste="login-security-failures-table"', html=False)
        self.assertNotContains(response, 'data-teste="login-security-access-logs-table"', html=False)
        self.assertContains(response, 'data-teste="login-security-cleanup-disabled"', html=False)

    def test_login_security_filters_attempts_failures_and_logs(self) -> None:
        """A busca textual e o filtro de bloqueio devem refletir as três trilhas."""

        self._login_with_permissions(
            "view_accessattempt",
            "view_accessfailurelog",
            "view_accesslog",
        )
        self._create_access_attempt(
            username="bloqueado@example.com",
            ip_address="10.0.0.20",
            failures_since_start=5,
        )
        self._create_access_attempt(
            username="aberto@example.com",
            ip_address="10.0.0.21",
            failures_since_start=2,
        )
        self._create_failure_log(
            username="bloqueado@example.com",
            ip_address="10.0.0.20",
            locked_out=True,
        )
        self._create_failure_log(
            username="outro@example.com",
            ip_address="10.0.0.30",
            locked_out=False,
        )
        self._create_access_log(
            username="bloqueado@example.com",
            ip_address="10.0.0.20",
        )
        self._create_access_log(
            username="outro@example.com",
            ip_address="10.0.0.31",
        )

        response = self.client.get(
            reverse("panel_login_security_list"),
            {
                "q": "bloqueado@example.com",
                "locked": "yes",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page-title="Segurança de login"', html=False)
        self.assertContains(response, "bloqueado@example.com")
        self.assertNotContains(response, "aberto@example.com")
        self.assertNotContains(response, "outro@example.com")
        self.assertContains(response, "Bloqueado")

    def test_cleanup_expired_attempts_requires_delete_permission(self) -> None:
        """A limpeza operacional deve respeitar a permissão de delete do axes."""

        self._login_with_permissions("view_accessattempt")

        response = self.client.post(
            reverse("panel_login_security_cleanup_expired_attempts"),
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(AXES_COOLOFF_TIME=timedelta(minutes=15))
    def test_cleanup_expired_attempts_removes_old_rows_and_audits(self) -> None:
        """A ação deve remover tentativas antigas e registrar a operação em auditoria."""

        self._login_with_permissions("view_accessattempt", "delete_accessattempt")
        old_attempt = self._create_access_attempt(
            username="expirado@example.com",
            ip_address="10.0.0.40",
            failures_since_start=5,
        )
        fresh_attempt = self._create_access_attempt(
            username="ativo@example.com",
            ip_address="10.0.0.41",
            failures_since_start=1,
        )
        AccessAttempt.objects.filter(pk=old_attempt.pk).update(
            attempt_time=timezone.now() - timedelta(minutes=20)
        )

        response = self.client.post(
            reverse("panel_login_security_cleanup_expired_attempts"),
            {"next": reverse("panel_login_security_list") + "?locked=yes"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(AccessAttempt.objects.filter(pk=old_attempt.pk).exists())
        self.assertTrue(AccessAttempt.objects.filter(pk=fresh_attempt.pk).exists())

        log = AuditLog.objects.filter(
            metadata__event="axes_cleanup_expired_attempts"
        ).latest("created_at")
        self.assertEqual(log.action, AuditLog.ACTION_UPDATE)
        self.assertEqual(log.metadata["cleaned_count"], 1)

    def test_reset_attempt_requires_delete_permission(self) -> None:
        """O desbloqueio pontual deve respeitar a permissão de delete do axes."""

        self._login_with_permissions("view_accessattempt")
        attempt = self._create_access_attempt(
            username="travado@example.com",
            ip_address="10.0.0.50",
            failures_since_start=5,
        )

        response = self.client.post(
            reverse("panel_login_security_reset_attempt", args=[attempt.pk]),
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(AccessAttempt.objects.filter(pk=attempt.pk).exists())

    def test_reset_attempt_removes_row_and_writes_audit_log(self) -> None:
        """O painel deve desbloquear a tentativa e registrar a ação manual."""

        self._login_with_permissions("view_accessattempt", "delete_accessattempt")
        attempt = self._create_access_attempt(
            username="travado@example.com",
            ip_address="10.0.0.50",
            failures_since_start=5,
        )

        response = self.client.post(
            reverse("panel_login_security_reset_attempt", args=[attempt.pk]),
            {"next": reverse("panel_login_security_list")},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(AccessAttempt.objects.filter(pk=attempt.pk).exists())

        log = AuditLog.objects.filter(metadata__event="axes_attempt_reset").latest(
            "created_at"
        )
        self.assertEqual(log.action, AuditLog.ACTION_DELETE)
        self.assertEqual(log.object_id, str(attempt.pk))
        self.assertEqual(log.metadata["username"], "travado@example.com")
