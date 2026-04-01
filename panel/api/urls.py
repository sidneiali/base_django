"""Mapa de URLs JSON do app panel."""

from django.urls import path

from .views import group_detail, groups_collection, user_detail, users_collection

urlpatterns = [
    path("groups/", groups_collection, name="api_panel_groups_collection"),
    path("groups/<int:pk>/", group_detail, name="api_panel_group_detail"),
    path("users/", users_collection, name="api_panel_users_collection"),
    path("users/<int:pk>/", user_detail, name="api_panel_user_detail"),
]
