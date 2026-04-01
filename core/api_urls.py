"""Rotas JSON do domínio transversal do app core."""

from django.urls import path

from .api_views import (
    audit_log_detail,
    audit_logs_collection,
    health,
    me,
    token_status,
)

urlpatterns = [
    path("health/", health, name="api_core_health"),
    path("me/", me, name="api_core_me"),
    path("token/", token_status, name="api_core_token"),
    path("audit-logs/", audit_logs_collection, name="api_core_audit_logs_collection"),
    path("audit-logs/<int:pk>/", audit_log_detail, name="api_core_audit_log_detail"),
]
