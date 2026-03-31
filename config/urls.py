"""Mapa principal de URLs do projeto.

Centraliza as rotas do admin, autenticacao, dashboard, painel de gestao
e o handler customizado para erro 403.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import forbidden_view

handler403 = forbidden_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("painel/", include("panel.urls")),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
