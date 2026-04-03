"""Page objects E2E do CRUD de grupos do painel."""

from __future__ import annotations

from .crud import CrudFormPage, CrudListPage


class GroupsListPage(CrudListPage):
    """Fluxos recorrentes da listagem de grupos."""

    url_name = "panel_groups_list"
    page_testid = "groups-page"
    query_testid = "groups-query"
    filter_submit_testid = "groups-filter-submit"
    create_link_testid = "groups-create-link"
    table_testid = "groups-table"

    def row(self, group_name: str):
        return self.test_case._group_row(group_name)

    def open_create_form(self) -> "GroupFormPage":
        self.click(self.create_link_testid)
        form = GroupFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, group_name: str) -> "GroupFormPage":
        row = self.row(group_name)
        edit_link = row.find_element(*self.locator_by_testid("group-edit-link"))
        edit_link.click()
        self.pause()
        form = GroupFormPage(self.test_case)
        form.wait_until_loaded()
        return form


class GroupFormPage(CrudFormPage):
    """Fluxos recorrentes do formulário de grupos."""

    page_testid = "group-form-page"
    save_submit_testid = "group-save-submit"

    def fill(self, *, name: str | None = None) -> None:
        if name is not None:
            self.clear_and_type("group-name", name)

    def permission_xpath(self, action_label: str, subject_label: str) -> str:
        return (
            ".//option["
            f"contains(normalize-space(), {self.xpath_literal(action_label)}) and "
            f"contains(normalize-space(), {self.xpath_literal(subject_label)})"
            "]"
        )

    def assign_permission(self, *, action_label: str, subject_label: str) -> None:
        self.move_dual_list_option(
            source_testid="group-permissions-available",
            option_xpath=self.permission_xpath(action_label, subject_label),
            action_testid="group-permissions-add",
            target_testid="group-permissions-chosen",
            expected_text=action_label,
        )

    def remove_permission(self, *, action_label: str, subject_label: str) -> None:
        self.remove_dual_list_option(
            source_testid="group-permissions-chosen",
            option_xpath=self.permission_xpath(action_label, subject_label),
            action_testid="group-permissions-remove",
            removed_text=action_label,
        )

    def save(self) -> GroupsListPage:
        self.click(self.save_submit_testid)
        page = GroupsListPage(self.test_case)
        page.wait_until_loaded()
        return page
