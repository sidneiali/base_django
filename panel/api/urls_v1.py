"""Rotas JSON versionadas do app panel."""

from django.urls import path

from .views import user_detail, users_collection

urlpatterns = [
    path("users/", users_collection, name="api_v1_panel_users_collection"),
    path("users/<int:pk>/", user_detail, name="api_v1_panel_user_detail"),
]
