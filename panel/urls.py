"""Rotas do painel administrativo interno."""

from django.urls import path

from .views import (
                    audit_log_detail,
                    audit_logs_export_csv,
                    audit_logs_export_json,
                    audit_logs_list,
                    group_create,
                    group_update,
                    groups_list,
                    module_activate,
                    module_create,
                    module_deactivate,
                    module_delete,
                    module_update,
                    modules_list,
                    user_create,
                    user_update,
                    users_list,
)

urlpatterns = [
    path("auditoria/", audit_logs_list, name="panel_audit_logs_list"),
    path(
        "auditoria/exportar/csv/",
        audit_logs_export_csv,
        name="panel_audit_logs_export_csv",
    ),
    path(
        "auditoria/exportar/json/",
        audit_logs_export_json,
        name="panel_audit_logs_export_json",
    ),
    path("auditoria/<int:pk>/", audit_log_detail, name="panel_audit_log_detail"),
    path("modulos/", modules_list, name="panel_modules_list"),
    path("modulos/novo/", module_create, name="panel_module_create"),
    path("modulos/<int:pk>/ativar/", module_activate, name="panel_module_activate"),
    path("modulos/<int:pk>/inativar/", module_deactivate, name="panel_module_deactivate"),
    path("modulos/<int:pk>/excluir/", module_delete, name="panel_module_delete"),
    path("modulos/<int:pk>/editar/", module_update, name="panel_module_update"),
    path("usuarios/", users_list, name="panel_users_list"),
    path("usuarios/novo/", user_create, name="panel_user_create"),
    path("usuarios/<int:pk>/editar/", user_update, name="panel_user_update"),
    path("grupos/", groups_list, name="panel_groups_list"),
    path("grupos/novo/", group_create, name="panel_group_create"),
    path("grupos/<int:pk>/editar/", group_update, name="panel_group_update"),
]
