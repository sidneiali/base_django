"""Rotas do app core."""

from django.urls import path

from .views import account_password_change, api_docs, dashboard, module_entry

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("minha-conta/senha/", account_password_change, name="account_password_change"),
    path("api/docs/", api_docs, name="api_docs"),
    path("modulo/<slug:slug>/", module_entry, name="module_entry"),
]
