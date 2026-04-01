"""Catalogo canonico dos modulos iniciais do sistema."""

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
)
