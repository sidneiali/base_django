"""Rotas do painel administrativo interno."""

from django.urls import path

from .views import (
                    group_create,
                    group_update,
                    groups_list,
                    user_create,
                    user_update,
                    users_list,
)

urlpatterns = [
    path("usuarios/", users_list, name="panel_users_list"),
    path("usuarios/novo/", user_create, name="panel_user_create"),
    path("usuarios/<int:pk>/editar/", user_update, name="panel_user_update"),
    path("grupos/", groups_list, name="panel_groups_list"),
    path("grupos/novo/", group_create, name="panel_group_create"),
    path("grupos/<int:pk>/editar/", group_update, name="panel_group_update"),
]
