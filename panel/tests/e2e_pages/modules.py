"""Page objects E2E do CRUD de módulos do painel."""

from __future__ import annotations

from .crud import CrudFormPage, CrudListPage


class ModulesListPage(CrudListPage):
    """Fluxos recorrentes da listagem de módulos."""

    url_name = "panel_modules_list"
    page_testid = "modules-page"
    query_testid = "modules-query"
    filter_submit_testid = "modules-filter-submit"
    create_link_testid = "modules-create-link"
    table_testid = "modules-table"

    def row(self, module_name: str):
        return self.test_case._module_row(module_name)

    def row_locator(self, module_name: str) -> tuple[str, str]:
        return self.test_case._module_row_locator(module_name)

    def open_create_form(self) -> "ModuleFormPage":
        self.click(self.create_link_testid)
        form = ModuleFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, module_name: str) -> "ModuleFormPage":
        row = self.row(module_name)
        edit_link = row.find_element(*self.locator_by_testid("module-edit-link"))
        edit_link.click()
        self.pause()
        form = ModuleFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def wait_for_row_text(self, module_name: str, text: str) -> None:
        self.wait_text(self.row_locator(module_name), text)

    def deactivate(self, module_name: str) -> None:
        row = self.row(module_name)
        deactivate_button = row.find_element(
            *self.locator_by_testid("module-deactivate-submit")
        )
        deactivate_button.click()
        self.pause()
        self.wait_for_row_text(module_name, "Inativo")

    def activate(self, module_name: str) -> None:
        row = self.row(module_name)
        activate_button = row.find_element(
            *self.locator_by_testid("module-activate-submit")
        )
        activate_button.click()
        self.pause()
        self.wait_for_row_text(module_name, "Ativo")


class ModuleFormPage(CrudFormPage):
    """Fluxos recorrentes do formulário de módulos."""

    page_testid = "module-form-page"
    save_submit_testid = "module-save-submit"

    def fill(
        self,
        *,
        name: str | None = None,
        slug: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        menu_group: str | None = None,
        url_name: str | None = None,
        order: str | None = None,
    ) -> None:
        if name is not None:
            self.clear_and_type("module-name", name)
        if slug is not None:
            self.clear_and_type("module-slug", slug)
        if description is not None:
            self.clear_and_type("module-description", description)
        if icon is not None:
            self.clear_and_type("module-icon", icon)
        if menu_group is not None:
            self.clear_and_type("module-menu-group", menu_group)
        if url_name is not None:
            self.clear_and_type("module-url-name", url_name)
        if order is not None:
            self.clear_and_type("module-order", order)

    def set_show_in_dashboard(self, *, enabled: bool) -> None:
        self.set_checkbox("module-show-in-dashboard", checked=enabled)

    def set_show_in_sidebar(self, *, enabled: bool) -> None:
        self.set_checkbox("module-show-in-sidebar", checked=enabled)

    def save(self) -> ModulesListPage:
        self.click(self.save_submit_testid)
        page = ModulesListPage(self.test_case)
        page.wait_until_loaded()
        return page
