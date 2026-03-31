"""Rotas do app core."""

from django.urls import path

from .views import dashboard, module_entry

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("modulo/<slug:slug>/", module_entry, name="module_entry"),
]
