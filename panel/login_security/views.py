"""Views HTML da trilha operacional do django-axes no painel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from axes.conf import settings as axes_settings  # type: ignore[import-untyped]
from axes.models import (  # type: ignore[import-untyped]
    AccessAttempt,
    AccessFailureLog,
    AccessLog,
)
from core.audit import build_changes, build_instance_snapshot, create_audit_log
from core.htmx import htmx_location, is_htmx_request, render_page
from core.models import AuditLog
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

LOGIN_SECURITY_PAGE_SIZE = 25


@dataclass(frozen=True, slots=True)
class LoginAttemptRow:
    """Representa um resumo operacional de uma tentativa registrada pelo axes."""

    attempt: AccessAttempt
    failure_limit: int
    expires_at: datetime | None

    @property
    def is_locked(self) -> bool:
        return self.attempt.failures_since_start >= self.failure_limit

    @property
    def remaining_attempts(self) -> int:
        return max(self.failure_limit - self.attempt.failures_since_start, 0)

    @property
    def status_label(self) -> str:
        if self.is_locked:
            return "Bloqueado"
        return f"{self.remaining_attempts} tentativa(s) restante(s)"

    @property
    def status_badge_class(self) -> str:
        return "bg-danger-lt" if self.is_locked else "bg-success-lt"


def _login_security_base_path() -> str:
    """Retorna a URL base da página operacional do axes no painel."""

    return reverse("panel_login_security_list")


def _redirect_login_security_page(request: HttpRequest) -> HttpResponse:
    """Redireciona de volta para a lista preservando filtros quando possível."""

    target = str(request.POST.get("next", "") or "").strip()
    default = _login_security_base_path()
    if not target.startswith(default):
        target = default

    if is_htmx_request(request):
        return htmx_location(target)
    return redirect(target)


def _has_any_login_security_view_permission(user: object) -> bool:
    """Resolve se o usuário pode acessar ao menos uma seção da página."""

    if not getattr(user, "is_authenticated", False):
        return False

    has_perm = getattr(user, "has_perm", None)
    if not callable(has_perm):
        return False

    return any(
        has_perm(permission)
        for permission in (
            "axes.view_accessattempt",
            "axes.view_accessfailurelog",
            "axes.view_accesslog",
        )
    )


def _ensure_login_security_access(user: object) -> None:
    """Bloqueia acesso quando o operador não possui nenhuma permissão útil."""

    if not _has_any_login_security_view_permission(user):
        raise PermissionDenied("Você não tem permissão para acessar este recurso.")


def _filter_login_security_queryset(
    queryset: QuerySet,
    *,
    query: str,
) -> QuerySet:
    """Aplica busca textual comum às tabelas operacionais do axes."""

    if not query:
        return queryset

    return queryset.filter(
        Q(username__icontains=query)
        | Q(ip_address__icontains=query)
        | Q(path_info__icontains=query)
        | Q(user_agent__icontains=query)
    )


def _build_attempt_expires_at(attempt: AccessAttempt) -> datetime | None:
    """Resolve a expiração visível da tentativa usando a configuração atual."""

    expiration = getattr(attempt, "expiration", None)
    if expiration is not None:
        return expiration.expires_at

    cooloff = getattr(axes_settings, "AXES_COOLOFF_TIME", None)
    if cooloff is None:
        return None

    return attempt.attempt_time + cooloff


def _build_attempt_rows(queryset: QuerySet[AccessAttempt]) -> list[LoginAttemptRow]:
    """Converte o queryset de tentativas em resumos de UI estáveis."""

    failure_limit = int(getattr(axes_settings, "AXES_FAILURE_LIMIT", 5) or 5)
    return [
        LoginAttemptRow(
            attempt=attempt,
            failure_limit=failure_limit,
            expires_at=_build_attempt_expires_at(attempt),
        )
        for attempt in queryset[:LOGIN_SECURITY_PAGE_SIZE]
    ]


def _clean_expired_attempts() -> int:
    """Remove tentativas expiradas respeitando a configuração atual do axes."""

    attempts = AccessAttempt.objects.all()

    if getattr(axes_settings, "AXES_USE_ATTEMPT_EXPIRATION", False):
        expired_attempts = attempts.filter(expiration__expires_at__lte=timezone.now())
    else:
        cooloff = getattr(axes_settings, "AXES_COOLOFF_TIME", None)
        if cooloff is None:
            return 0
        expired_attempts = attempts.filter(attempt_time__lte=timezone.now() - cooloff)

    cleaned_count = expired_attempts.count()
    expired_attempts.delete()
    return cleaned_count


@login_required
def login_security_list(request: HttpRequest) -> HttpResponse:
    """Exibe as trilhas operacionais do django-axes em uma página do painel."""

    _ensure_login_security_access(request.user)

    query = str(request.GET.get("q", "") or "").strip()
    locked = str(request.GET.get("locked", "") or "").strip()

    can_view_attempts = request.user.has_perm("axes.view_accessattempt")
    can_view_failures = request.user.has_perm("axes.view_accessfailurelog")
    can_view_access_logs = request.user.has_perm("axes.view_accesslog")
    can_manage_attempts = request.user.has_perm("axes.delete_accessattempt")

    attempt_rows: list[LoginAttemptRow] = []
    attempt_count = 0
    if can_view_attempts:
        attempts_queryset = AccessAttempt.objects.select_related("expiration").order_by(
            "-attempt_time"
        )
        attempts_queryset = _filter_login_security_queryset(
            attempts_queryset,
            query=query,
        )
        failure_limit = int(getattr(axes_settings, "AXES_FAILURE_LIMIT", 5) or 5)
        if locked == "yes":
            attempts_queryset = attempts_queryset.filter(
                failures_since_start__gte=failure_limit
            )
        elif locked == "no":
            attempts_queryset = attempts_queryset.filter(
                failures_since_start__lt=failure_limit
            )
        attempt_count = attempts_queryset.count()
        attempt_rows = _build_attempt_rows(attempts_queryset)

    failure_logs: list[AccessFailureLog] = []
    failure_log_count = 0
    if can_view_failures:
        failure_logs_queryset = _filter_login_security_queryset(
            AccessFailureLog.objects.order_by("-attempt_time"),
            query=query,
        )
        failure_log_count = failure_logs_queryset.count()
        failure_logs = list(failure_logs_queryset[:LOGIN_SECURITY_PAGE_SIZE])

    access_logs: list[AccessLog] = []
    access_log_count = 0
    if can_view_access_logs:
        access_logs_queryset = _filter_login_security_queryset(
            AccessLog.objects.order_by("-attempt_time"),
            query=query,
        )
        access_log_count = access_logs_queryset.count()
        access_logs = list(access_logs_queryset[:LOGIN_SECURITY_PAGE_SIZE])

    return render_page(
        request,
        "panel/login_security_list.html",
        "panel/partials/login_security_list_content.html",
        {
            "page_title": "Segurança de login",
            "query": query,
            "locked": locked,
            "attempt_rows": attempt_rows,
            "attempt_count": attempt_count,
            "failure_logs": failure_logs,
            "failure_log_count": failure_log_count,
            "access_logs": access_logs,
            "access_log_count": access_log_count,
            "can_view_attempts": can_view_attempts,
            "can_view_failures": can_view_failures,
            "can_view_access_logs": can_view_access_logs,
            "can_manage_attempts": can_manage_attempts,
            "axes_failure_limit": int(getattr(axes_settings, "AXES_FAILURE_LIMIT", 5) or 5),
            "axes_cooloff_minutes": (
                int(axes_settings.AXES_COOLOFF_TIME.total_seconds() // 60)
                if getattr(axes_settings, "AXES_COOLOFF_TIME", None) is not None
                else None
            ),
            "current_path": request.get_full_path(),
        },
    )


@login_required
@require_POST
def login_security_cleanup_expired_attempts(request: HttpRequest) -> HttpResponse:
    """Limpa tentativas expiradas do axes sem depender do admin."""

    if not request.user.has_perm("axes.delete_accessattempt"):
        raise PermissionDenied("Você não tem permissão para acessar este recurso.")

    cleaned_count = _clean_expired_attempts()
    create_audit_log(
        AuditLog.ACTION_UPDATE,
        actor=request.user,
        object_repr="Tentativas de login do axes",
        changes={
            "expired_attempts_cleanup": {
                "before": None,
                "after": cleaned_count,
            }
        },
        metadata={
            "event": "axes_cleanup_expired_attempts",
            "cleaned_count": cleaned_count,
        },
    )
    return _redirect_login_security_page(request)


@login_required
@require_POST
def login_security_reset_attempt(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove uma tentativa específica para liberar o próximo login do usuário."""

    if not request.user.has_perm("axes.delete_accessattempt"):
        raise PermissionDenied("Você não tem permissão para acessar este recurso.")

    attempt = get_object_or_404(
        AccessAttempt.objects.select_related("expiration"),
        pk=pk,
    )
    before_state, before_comparison = build_instance_snapshot(attempt)
    object_id = str(attempt.pk)
    metadata = {
        "event": "axes_attempt_reset",
        "username": attempt.username or "",
        "ip_address": str(attempt.ip_address or ""),
        "failures_since_start": attempt.failures_since_start,
    }
    attempt.delete()
    create_audit_log(
        AuditLog.ACTION_DELETE,
        actor=request.user,
        instance=attempt,
        object_id=object_id,
        before=before_state,
        changes=build_changes(
            before_state,
            {},
            before_comparison,
            {},
        ),
        metadata=metadata,
    )
    return _redirect_login_security_page(request)
