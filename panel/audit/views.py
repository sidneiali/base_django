"""Views HTML da trilha de auditoria no painel interno."""

from __future__ import annotations

from core.audit import apply_audit_log_filters
from core.htmx import render_page
from core.models import AuditLog
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, QueryDict

from .forms import AuditLogFilterForm

AUDIT_PAGE_SIZE = 25


def _build_preserved_querystring(params: QueryDict) -> str:
    """Monta a query string preservada para paginação da listagem."""

    preserved = params.copy()
    preserved.pop("page", None)
    encoded = preserved.urlencode()
    if not encoded:
        return ""
    return f"&{encoded}"


@login_required
@permission_required("core.view_auditlog", raise_exception=True)
def audit_logs_list(request: HttpRequest) -> HttpResponse:
    """Lista os logs de auditoria com filtros HTML e suporte a HTMX."""

    form = AuditLogFilterForm(request.GET or None)
    audit_logs = AuditLog.objects.select_related("actor", "content_type").order_by(
        "-created_at",
        "-id",
    )

    if form.is_valid():
        audit_logs = apply_audit_log_filters(
            audit_logs,
            search=str(form.cleaned_data["object_query"] or "").strip(),
            action=str(form.cleaned_data["action"] or "").strip(),
            actor=str(form.cleaned_data["actor"] or "").strip(),
            date_from=form.cleaned_data.get("date_from"),
            date_to=form.cleaned_data.get("date_to"),
        )

    page_obj = Paginator(audit_logs, AUDIT_PAGE_SIZE).get_page(
        request.GET.get("page") or 1
    )

    return render_page(
        request,
        "panel/audit_logs_list.html",
        "panel/partials/audit_logs_list_content.html",
        {
            "page_title": "Auditoria",
            "form": form,
            "page_obj": page_obj,
            "audit_logs": page_obj.object_list,
            "page_query": _build_preserved_querystring(request.GET),
        },
    )
