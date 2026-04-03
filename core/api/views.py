"""Fachada pública compatível dos endpoints JSON transversais do app core."""

from .audit_logs import audit_log_detail, audit_logs_collection
from .introspection import me, token_status
from .operational import health

__all__ = [
    "audit_log_detail",
    "audit_logs_collection",
    "health",
    "me",
    "token_status",
]
