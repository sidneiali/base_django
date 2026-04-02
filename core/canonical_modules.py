"""Definicoes canonicas dos modulos iniciais do sistema."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ModuleSeedDefinition:
    """Define os campos persistidos para um modulo inicial."""

    name: str
    slug: str
    description: str
    icon: str
    url_name: str
    app_label: str
    permission_codename: str
    menu_group: str
    order: int
    is_active: bool = True
    show_in_sidebar: bool = True
    show_in_dashboard: bool = True

    def defaults(self) -> dict[str, object]:
        """Retorna os campos usados no ``update_or_create`` do seed."""

        data = asdict(self)
        data.pop("slug")
        return data


INITIAL_MODULES: tuple[ModuleSeedDefinition, ...] = (
    ModuleSeedDefinition(
        name="Usuários",
        slug="usuarios",
        description="Gestão de usuários do sistema",
        icon="ti ti-users",
        url_name="panel_users_list",
        app_label="auth",
        permission_codename="view_user",
        menu_group="Configurações",
        order=10,
    ),
    ModuleSeedDefinition(
        name="Módulos",
        slug="modulos",
        description="Gestão dos módulos exibidos no dashboard e no sidebar",
        icon="ti ti-layout-grid",
        url_name="panel_modules_list",
        app_label="core",
        permission_codename="view_module",
        menu_group="Configurações",
        order=20,
    ),
    ModuleSeedDefinition(
        name="Grupos",
        slug="grupos",
        description="Gestão de grupos e permissões",
        icon="ti ti-users-group",
        url_name="panel_groups_list",
        app_label="auth",
        permission_codename="view_group",
        menu_group="Segurança",
        order=20,
    ),
    ModuleSeedDefinition(
        name="Auditoria",
        slug="auditoria",
        description="Consulta operacional dos eventos auditados do sistema",
        icon="ti ti-history",
        url_name="panel_audit_logs_list",
        app_label="core",
        permission_codename="view_auditlog",
        menu_group="Segurança",
        order=30,
    ),
    ModuleSeedDefinition(
        name="Documentação da API",
        slug="documentacao-api",
        description="Referência pública da API, exemplos e coleção Postman",
        icon="ti ti-book",
        url_name="api_docs",
        app_label="",
        permission_codename="",
        menu_group="Integrações",
        order=40,
    ),
)
