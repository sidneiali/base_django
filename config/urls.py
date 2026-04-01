"""Mapa principal de URLs do projeto.

Centraliza as rotas do admin, autenticacao, dashboard, painel de gestao
e o handler customizado para erro 403.
"""

from core.forms import LoginForm, PasswordRecoveryConfirmForm, PasswordRecoveryForm
from core.views import api_openapi, forbidden_view
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

handler403 = forbidden_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("painel/", include("panel.urls")),
    path("api/openapi.json", api_openapi, name="api_openapi"),
    path("api/v1/openapi.json", api_openapi, name="api_v1_openapi"),
    path("api/core/", include("core.api.urls")),
    path("api/panel/", include("panel.api.urls")),
    path("api/v1/core/", include("core.api.urls_v1")),
    path("api/v1/panel/", include("panel.api.urls_v1")),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    path(
        "recuperar-senha/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            form_class=PasswordRecoveryForm,
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "recuperar-senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "recuperar-senha/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            form_class=PasswordRecoveryConfirmForm,
        ),
        name="password_reset_confirm",
    ),
    path(
        "recuperar-senha/concluido/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
