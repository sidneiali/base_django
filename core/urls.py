"""Rotas do app core."""

from django.urls import path

from .views import (
                    account_password_change,
                    api_docs,
                    api_docs_postman,
                    dashboard,
                    module_entry,
)

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("minha-conta/senha/", account_password_change, name="account_password_change"),
    path("api/docs/", api_docs, name="api_docs"),
    path("api/docs/postman.json", api_docs_postman, name="api_docs_postman"),
    path("modulo/<slug:slug>/", module_entry, name="module_entry"),
]
