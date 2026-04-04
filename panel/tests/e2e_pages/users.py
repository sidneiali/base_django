"""Page objects E2E do CRUD de usuários do painel."""

from __future__ import annotations

from .crud import CrudFormPage, CrudListPage


class UsersListPage(CrudListPage):
    """Fluxos recorrentes da listagem de usuários."""

    url_name = "panel_users_list"
    page_testid = "users-page"
    query_testid = "users-query"
    filter_submit_testid = "users-filter-submit"
    create_link_testid = "users-create-link"

    def row(self, username: str):
        return self.test_case._user_row(username)

    def open_create_form(self) -> "UserFormPage":
        self.click(self.create_link_testid)
        form = UserFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, username: str) -> "UserFormPage":
        row = self.row(username)
        edit_link = row.find_element(*self.locator_by_testid("user-edit-link"))
        edit_link.click()
        self.pause()
        form = UserFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def row_action(self, username: str, testid: str):
        row = self.row(username)
        return row.find_element(*self.locator_by_testid(testid))

    def open_password_reset_confirm(
        self,
        username: str,
    ) -> "UserPasswordResetConfirmPage":
        row = self.row(username)
        reset_link = row.find_element(
            *self.locator_by_testid("user-password-reset-link")
        )
        reset_link.click()
        self.pause()
        page = UserPasswordResetConfirmPage(self.test_case)
        page.wait_until_loaded()
        return page


class UserFormPage(CrudFormPage):
    """Fluxos recorrentes do formulário de usuários."""

    page_testid = "user-form-page"
    save_submit_testid = "user-save-submit"

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
            self.clear_and_type("user-username", username)
        if email is not None:
            self.clear_and_type("user-email", email)
        if first_name is not None:
            self.clear_and_type("user-first-name", first_name)
        if last_name is not None:
            self.clear_and_type("user-last-name", last_name)
        if password is not None:
            self.clear_and_type("user-password", password)
        if auto_refresh_interval is not None:
            self.clear_and_type(
                "user-auto-refresh-interval",
                auto_refresh_interval,
            )

    def assign_group(self, group_name: str) -> None:
        self.move_dual_list_option(
            source_testid="user-groups-available",
            option_xpath=(
                f".//option[normalize-space()={self.xpath_literal(group_name)}]"
            ),
            action_testid="user-groups-add",
            target_testid="user-groups-chosen",
            expected_text=group_name,
        )

    def remove_group(self, group_name: str) -> None:
        self.remove_dual_list_option(
            source_testid="user-groups-chosen",
            option_xpath=(
                f".//option[normalize-space()={self.xpath_literal(group_name)}]"
            ),
            action_testid="user-groups-remove",
            removed_text=group_name,
        )

    def save(self) -> UsersListPage:
        self.click(self.save_submit_testid)
        page = UsersListPage(self.test_case)
        page.wait_until_loaded()
        return page


class UserPasswordResetConfirmPage(CrudFormPage):
    """Fluxos recorrentes da confirmação de recuperação de senha."""

    page_testid = "user-password-reset-confirm-page"
    save_submit_testid = "user-password-reset-confirm-submit"

    def submit(self) -> UsersListPage:
        self.click(self.save_submit_testid)
        page = UsersListPage(self.test_case)
        page.wait_until_loaded()
        return page
