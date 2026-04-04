"""Fachada compatível para as views principais do app core."""

from .account.views import account_password_change
from .docs.views import api_docs, api_docs_postman, api_openapi
from .errors.views import forbidden_view, not_found_view, server_error_view
from .web.dashboard import dashboard, module_entry

__all__ = [
    "account_password_change",
    "api_docs",
    "api_docs_postman",
    "api_openapi",
    "dashboard",
    "forbidden_view",
    "module_entry",
    "not_found_view",
    "server_error_view",
]
