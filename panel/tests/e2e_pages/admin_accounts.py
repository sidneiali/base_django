"""Page objects E2E da superfície de contas administrativas do painel."""

from __future__ import annotations

from .crud import CrudFormPage, CrudListPage


class AdminAccountsListPage(CrudListPage):
    """Fluxos recorrentes da listagem de contas administrativas."""

    url_name = "panel_admin_accounts_list"
    page_testid = "admin-accounts-page"
    query_testid = "admin-accounts-query"
    filter_submit_testid = "admin-accounts-filter-submit"
    create_link_testid = "admin-accounts-create-link"
    table_testid = "admin-accounts-table"

    def row(self, username: str):
        return self.test_case._admin_account_row(username)

    def open_create_form(self) -> "AdminAccountFormPage":
        self.click(self.create_link_testid)
        form = AdminAccountFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, username: str) -> "AdminAccountFormPage":
        row = self.row(username)
        edit_link = row.find_element(*self.locator_by_testid("admin-account-edit-link"))
        edit_link.click()
        self.pause()
        form = AdminAccountFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def row_action(self, username: str, testid: str):
        row = self.row(username)
        return row.find_element(*self.locator_by_testid(testid))


class AdminAccountFormPage(CrudFormPage):
    """Fluxos recorrentes do formulário de contas administrativas."""

    page_testid = "admin-account-form-page"
    save_submit_testid = "admin-account-save-submit"

    def fill(
        self,
        *,
        username: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        password: str | None = None,
        auto_refresh_interval: str | None = None,
    ) -> None:
        if username is not None:
            self.clear_and_type("admin-account-username", username)
        if email is not None:
            self.clear_and_type("admin-account-email", email)
        if first_name is not None:
            self.clear_and_type("admin-account-first-name", first_name)
        if last_name is not None:
            self.clear_and_type("admin-account-last-name", last_name)
        if password is not None:
            self.clear_and_type("admin-account-password", password)
        if auto_refresh_interval is not None:
            self.clear_and_type(
                "admin-account-auto-refresh-interval",
                auto_refresh_interval,
            )

    def set_staff(self, *, checked: bool) -> None:
        self.set_checkbox("admin-account-is-staff", checked=checked)

    def set_superuser(self, *, checked: bool) -> None:
        self.set_checkbox("admin-account-is-superuser", checked=checked)

    def assign_group(self, group_name: str) -> None:
        self.move_dual_list_option(
            source_testid="admin-account-groups-available",
            option_xpath=(
                f".//option[normalize-space()={self.xpath_literal(group_name)}]"
            ),
            action_testid="admin-account-groups-add",
            target_testid="admin-account-groups-chosen",
            expected_text=group_name,
        )

    def assign_permission(self, permission_label: str) -> None:
        self.move_dual_list_option(
            source_testid="admin-account-permissions-available",
            option_xpath=(
                f".//option[normalize-space()={self.xpath_literal(permission_label)}]"
            ),
            action_testid="admin-account-permissions-add",
            target_testid="admin-account-permissions-chosen",
            expected_text=permission_label,
        )

    def save(self) -> AdminAccountsListPage:
        self.click(self.save_submit_testid)
        page = AdminAccountsListPage(self.test_case)
        page.wait_until_loaded()
        return page
