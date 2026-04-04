"""Mapa declarativo dos modulos canonicos iniciais do produto."""

from __future__ import annotations

from core.modules import ModuleDefinition

INITIAL_MODULES: dict[str, ModuleDefinition] = {
    "usuarios": {
        "name": "Usuários",
        "description": "Gestão de usuários do sistema",
        "icon": "ti ti-users",
        "url_name": "panel_users_list",
        "app_label": "auth",
        "permission_codename": "view_user",
        "menu_group": "Configurações",
        "order": 10,
    },
    "modulos": {
        "name": "Módulos",
        "description": "Gestão dos módulos exibidos no dashboard e no sidebar",
        "icon": "ti ti-layout-grid",
        "url_name": "panel_modules_list",
        "app_label": "core",
        "permission_codename": "view_module",
        "menu_group": "Configurações",
        "order": 20,
    },
    "grupos": {
        "name": "Grupos",
        "description": "Gestão de grupos e permissões",
        "icon": "ti ti-users-group",
        "url_name": "panel_groups_list",
        "app_label": "auth",
        "permission_codename": "view_group",
        "menu_group": "Segurança",
        "order": 20,
    },
    "auditoria": {
        "name": "Auditoria",
        "description": "Consulta operacional dos eventos auditados do sistema",
        "icon": "ti ti-history",
        "url_name": "panel_audit_logs_list",
        "app_label": "core",
        "permission_codename": "view_auditlog",
        "menu_group": "Segurança",
        "order": 30,
    },
    "seguranca-login": {
        "name": "Segurança de login",
        "description": "Tentativas, bloqueios e acessos monitorados pelo django-axes",
        "icon": "ti ti-shield-lock",
        "url_name": "panel_login_security_list",
        "app_label": "axes",
        "permission_codename": "view_accessattempt",
        "menu_group": "Segurança",
        "order": 25,
    },
    "documentacao-api": {
        "name": "Documentação da API",
        "description": "Referência pública da API, exemplos e coleção Postman",
        "icon": "ti ti-book",
        "url_name": "api_docs",
        "app_label": "",
        "permission_codename": "",
        "menu_group": "Integrações",
        "order": 40,
        "show_in_dashboard": False,
    },
}
