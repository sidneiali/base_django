"""Page objects leves para os smoke tests E2E do painel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from .e2e_support import PanelE2EBase


class _BasePageObject:
    """Pequena camada compartilhada para reduzir ruído nos smoke tests."""

    def __init__(self, test_case: PanelE2EBase) -> None:
        self.test_case = test_case

    @property
    def browser(self):
        return self.test_case.browser

    @property
    def wait(self):
        return self.test_case.wait

    def _locator_by_testid(self, testid: str) -> tuple[str, str]:
        return self.test_case._locator_by_testid(testid)

    def _find(self, testid: str) -> WebElement:
        return self.browser.find_element(*self._locator_by_testid(testid))

    def _click(self, testid: str) -> WebElement:
        element = self._wait_clickable(testid)
        element.click()
        self._pause()
        return element

    def _clear_and_type(self, testid: str, value: str) -> WebElement:
        element = self._wait_visible(testid)
        element.clear()
        element.send_keys(value)
        return element

    def _wait_present(self, testid: str) -> WebElement:
        return self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid(testid))
        )

    def _wait_visible(self, testid: str) -> WebElement:
        return self.wait.until(
            EC.visibility_of_element_located(self._locator_by_testid(testid))
        )

    def _wait_clickable(self, testid: str) -> WebElement:
        return self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid(testid))
        )

    def wait_for_url_fragment(self, fragment: str) -> None:
        self.wait.until(lambda browser: fragment in browser.current_url)

    def _wait_text(self, locator: tuple[str, str], text: str) -> None:
        self.wait.until(EC.text_to_be_present_in_element(locator, text))

    def _wait_text_in_testid(self, testid: str, text: str) -> None:
        self._wait_text(self._locator_by_testid(testid), text)

    def _wait_text_not_in_testid(self, testid: str, text: str) -> None:
        self.wait.until_not(
            lambda browser: text in browser.find_element(
                *self._locator_by_testid(testid)
            ).text
        )

    def _set_checkbox(self, testid: str, *, checked: bool) -> None:
        checkbox = self._find(testid)
        if checkbox.is_selected() != checked:
            checkbox.click()
            self._pause()

    def _xpath_literal(self, value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        tokens: list[str] = []
        for index, part in enumerate(parts):
            if part:
                tokens.append(f"'{part}'")
            if index < len(parts) - 1:
                tokens.append('"\'"')
        return f"concat({', '.join(tokens)})"

    def _select_option_by_xpath(
        self,
        *,
        select_testid: str,
        option_xpath: str,
    ) -> WebElement:
        select_box = self._wait_visible(select_testid)
        option = select_box.find_element(By.XPATH, option_xpath)
        self.test_case._select_dual_list_option(option)
        return option

    def _move_dual_list_option(
        self,
        *,
        source_testid: str,
        option_xpath: str,
        action_testid: str,
        target_testid: str,
        expected_text: str,
    ) -> None:
        self._select_option_by_xpath(
            select_testid=source_testid,
            option_xpath=option_xpath,
        )
        self._click(action_testid)
        self._wait_text_in_testid(target_testid, expected_text)

    def _remove_dual_list_option(
        self,
        *,
        source_testid: str,
        option_xpath: str,
        action_testid: str,
        removed_text: str,
    ) -> None:
        self._select_option_by_xpath(
            select_testid=source_testid,
            option_xpath=option_xpath,
        )
        self._click(action_testid)
        self._wait_text_not_in_testid(source_testid, removed_text)

    def _pause(self) -> None:
        self.test_case._pause_for_demo()


class _CrudListPage(_BasePageObject):
    """Comportamentos comuns das listagens CRUD do painel."""

    url_name: str
    page_testid: str
    query_testid: str
    filter_submit_testid: str
    create_link_testid: str
    table_testid: str | None = None

    def open(self, query: str = "") -> None:
        self.test_case._open(reverse(self.url_name) + query)
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self._wait_present(self.page_testid)

    def filter(self, query: str) -> None:
        self._clear_and_type(self.query_testid, query)
        self._click(self.filter_submit_testid)

    def wait_for_table_text(self, text: str) -> None:
        locator = (
            self._locator_by_testid(self.table_testid)
            if self.table_testid is not None
            else (By.CSS_SELECTOR, "tbody")
        )
        self._wait_text(locator, text)

    def table_text(self) -> str:
        if self.table_testid is None:
            return self.browser.find_element(By.CSS_SELECTOR, "tbody").text
        return self._find(self.table_testid).text


class _CrudFormPage(_BasePageObject):
    """Comportamentos comuns dos formulários CRUD do painel."""

    page_testid: str
    save_submit_testid: str

    def wait_until_loaded(self) -> None:
        self._wait_present(self.page_testid)


class TopbarPage(_BasePageObject):
    """Interações estáveis da topbar do shell autenticado."""

    def open_user_menu(self) -> None:
        self.test_case._open_user_menu()

    def open_shortcuts(self) -> None:
        self.test_case._open_topbar_shortcuts()

    def logout(self) -> None:
        self.open_user_menu()
        logout_button = self._wait_clickable("topbar-logout-submit")
        logout_button.click()
        self._pause()

        self._wait_visible("login-title")

    def go_to_my_password(self) -> None:
        self.open_user_menu()
        password_link = self._wait_clickable("topbar-my-password-link")
        password_link.click()
        self._pause()

        self.wait.until(
            lambda browser: browser.current_url.endswith(
                reverse("account_password_change")
            )
        )
        self._wait_present("account-password-page")

    def shortcut(self, shortcut_key: str) -> WebElement:
        return self.test_case._topbar_shortcut(shortcut_key)

    def go_to_audit(self) -> None:
        self.open_shortcuts()
        audit_link = self.shortcut("audit")
        audit_link.click()
        self._pause()

        AuditListPage(self.test_case).wait_until_loaded()


class AuditListPage(_BasePageObject):
    """Fluxos recorrentes da lista HTML de auditoria."""

    def open(self, query: str = "") -> None:
        self.test_case._open(reverse("panel_audit_logs_list") + query)
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self._wait_present("audit-list-page")

    def filter(
        self,
        *,
        actor: str | None = None,
        object_query: str | None = None,
    ) -> None:
        if actor is not None:
            actor_input = self._wait_visible("audit-filter-actor")
            actor_input.clear()
            actor_input.send_keys(actor)

        if object_query is not None:
            object_input = self._wait_visible("audit-filter-object-query")
            object_input.clear()
            object_input.send_keys(object_query)

        submit_button = self._find("audit-filter-submit")
        submit_button.click()
        self._pause()

    def clear_filters(self) -> None:
        clear_link = self._wait_clickable("audit-filter-clear")
        clear_link.click()
        self._pause()

    def row(self, request_id: str) -> WebElement:
        return self.test_case._audit_row(request_id)

    def open_first_detail(self) -> None:
        detail_link = self._wait_clickable("audit-detail-link")
        detail_link.click()
        self._pause()

        AuditDetailPage(self.test_case).wait_until_loaded()

    def go_to_page(self, page_number: int) -> None:
        selector = (
            '[data-teste="audit-page-number"]'
            f'[data-page-number="{page_number}"]'
        )
        page_link = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        page_link.click()
        self._pause()

    def export_link(self, export_format: str) -> WebElement:
        return self._find(f"audit-export-{export_format}")

    def export_href(self, export_format: str) -> str:
        return self.export_link(export_format).get_attribute("href") or ""

    def fetch_export(self, export_format: str) -> dict[str, object]:
        return self.test_case._fetch_response_in_browser(
            self.export_href(export_format)
        )


class AuditDetailPage(_BasePageObject):
    """Fluxos recorrentes do drill-down HTML de auditoria."""

    def open(self, audit_log_or_pk: object, query: str = "") -> None:
        audit_log_pk = getattr(audit_log_or_pk, "pk", audit_log_or_pk)
        self.test_case._open(reverse("panel_audit_log_detail", args=[audit_log_pk]) + query)
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        self._wait_present("audit-detail-page")

    def open_actor_filtered_list(self) -> None:
        actor_link = self._wait_clickable("audit-detail-actor-link")
        actor_link.click()
        self._pause()

        AuditListPage(self.test_case).wait_until_loaded()

    def open_request_filtered_list(self) -> None:
        request_link = self._wait_clickable("audit-detail-request-link")
        request_link.click()
        self._pause()

        AuditListPage(self.test_case).wait_until_loaded()

    def related_section(self, scope: str) -> WebElement:
        selector = (
            '[data-teste="audit-related-section"]'
            f'[data-related-scope="{scope}"]'
        )
        return self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def related_detail_link(self, scope: str) -> WebElement:
        return self.related_section(scope).find_element(
            *self._locator_by_testid("audit-related-detail-link")
        )

    def open_related_detail(self, scope: str) -> None:
        detail_link = self.related_detail_link(scope)
        detail_link.click()
        self._pause()

        self.wait_until_loaded()


class UsersListPage(_CrudListPage):
    """Fluxos recorrentes da listagem de usuários."""

    url_name = "panel_users_list"
    page_testid = "users-page"
    query_testid = "users-query"
    filter_submit_testid = "users-filter-submit"
    create_link_testid = "users-create-link"

    def row(self, username: str) -> WebElement:
        return self.test_case._user_row(username)

    def open_create_form(self) -> "UserFormPage":
        self._click(self.create_link_testid)
        form = UserFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, username: str) -> "UserFormPage":
        row = self.row(username)
        edit_link = row.find_element(*self._locator_by_testid("user-edit-link"))
        edit_link.click()
        self._pause()
        form = UserFormPage(self.test_case)
        form.wait_until_loaded()
        return form


class UserFormPage(_CrudFormPage):
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
            self._clear_and_type("user-username", username)
        if email is not None:
            self._clear_and_type("user-email", email)
        if first_name is not None:
            self._clear_and_type("user-first-name", first_name)
        if last_name is not None:
            self._clear_and_type("user-last-name", last_name)
        if password is not None:
            self._clear_and_type("user-password", password)
        if auto_refresh_interval is not None:
            self._clear_and_type(
                "user-auto-refresh-interval",
                auto_refresh_interval,
            )

    def assign_group(self, group_name: str) -> None:
        self._move_dual_list_option(
            source_testid="user-groups-available",
            option_xpath=(
                f".//option[normalize-space()={self._xpath_literal(group_name)}]"
            ),
            action_testid="user-groups-add",
            target_testid="user-groups-chosen",
            expected_text=group_name,
        )

    def remove_group(self, group_name: str) -> None:
        self._remove_dual_list_option(
            source_testid="user-groups-chosen",
            option_xpath=(
                f".//option[normalize-space()={self._xpath_literal(group_name)}]"
            ),
            action_testid="user-groups-remove",
            removed_text=group_name,
        )

    def save(self) -> UsersListPage:
        self._click(self.save_submit_testid)
        page = UsersListPage(self.test_case)
        page.wait_until_loaded()
        return page


class GroupsListPage(_CrudListPage):
    """Fluxos recorrentes da listagem de grupos."""

    url_name = "panel_groups_list"
    page_testid = "groups-page"
    query_testid = "groups-query"
    filter_submit_testid = "groups-filter-submit"
    create_link_testid = "groups-create-link"
    table_testid = "groups-table"

    def row(self, group_name: str) -> WebElement:
        return self.test_case._group_row(group_name)

    def open_create_form(self) -> "GroupFormPage":
        self._click(self.create_link_testid)
        form = GroupFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, group_name: str) -> "GroupFormPage":
        row = self.row(group_name)
        edit_link = row.find_element(*self._locator_by_testid("group-edit-link"))
        edit_link.click()
        self._pause()
        form = GroupFormPage(self.test_case)
        form.wait_until_loaded()
        return form


class GroupFormPage(_CrudFormPage):
    """Fluxos recorrentes do formulário de grupos."""

    page_testid = "group-form-page"
    save_submit_testid = "group-save-submit"

    def fill(self, *, name: str | None = None) -> None:
        if name is not None:
            self._clear_and_type("group-name", name)

    def _permission_xpath(self, action_label: str, subject_label: str) -> str:
        return (
            ".//option["
            f"contains(normalize-space(), {self._xpath_literal(action_label)}) and "
            f"contains(normalize-space(), {self._xpath_literal(subject_label)})"
            "]"
        )

    def assign_permission(self, *, action_label: str, subject_label: str) -> None:
        self._move_dual_list_option(
            source_testid="group-permissions-available",
            option_xpath=self._permission_xpath(action_label, subject_label),
            action_testid="group-permissions-add",
            target_testid="group-permissions-chosen",
            expected_text=action_label,
        )

    def remove_permission(self, *, action_label: str, subject_label: str) -> None:
        self._remove_dual_list_option(
            source_testid="group-permissions-chosen",
            option_xpath=self._permission_xpath(action_label, subject_label),
            action_testid="group-permissions-remove",
            removed_text=action_label,
        )

    def save(self) -> GroupsListPage:
        self._click(self.save_submit_testid)
        page = GroupsListPage(self.test_case)
        page.wait_until_loaded()
        return page


class ModulesListPage(_CrudListPage):
    """Fluxos recorrentes da listagem de módulos."""

    url_name = "panel_modules_list"
    page_testid = "modules-page"
    query_testid = "modules-query"
    filter_submit_testid = "modules-filter-submit"
    create_link_testid = "modules-create-link"
    table_testid = "modules-table"

    def row(self, module_name: str) -> WebElement:
        return self.test_case._module_row(module_name)

    def row_locator(self, module_name: str) -> tuple[str, str]:
        return self.test_case._module_row_locator(module_name)

    def open_create_form(self) -> "ModuleFormPage":
        self._click(self.create_link_testid)
        form = ModuleFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def open_edit_form(self, module_name: str) -> "ModuleFormPage":
        row = self.row(module_name)
        edit_link = row.find_element(*self._locator_by_testid("module-edit-link"))
        edit_link.click()
        self._pause()
        form = ModuleFormPage(self.test_case)
        form.wait_until_loaded()
        return form

    def wait_for_row_text(self, module_name: str, text: str) -> None:
        self._wait_text(self.row_locator(module_name), text)

    def deactivate(self, module_name: str) -> None:
        row = self.row(module_name)
        deactivate_button = row.find_element(
            *self._locator_by_testid("module-deactivate-submit")
        )
        deactivate_button.click()
        self._pause()
        self.wait_for_row_text(module_name, "Inativo")

    def activate(self, module_name: str) -> None:
        row = self.row(module_name)
        activate_button = row.find_element(
            *self._locator_by_testid("module-activate-submit")
        )
        activate_button.click()
        self._pause()
        self.wait_for_row_text(module_name, "Ativo")


class ModuleFormPage(_CrudFormPage):
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
            self._clear_and_type("module-name", name)
        if slug is not None:
            self._clear_and_type("module-slug", slug)
        if description is not None:
            self._clear_and_type("module-description", description)
        if icon is not None:
            self._clear_and_type("module-icon", icon)
        if menu_group is not None:
            self._clear_and_type("module-menu-group", menu_group)
        if url_name is not None:
            self._clear_and_type("module-url-name", url_name)
        if order is not None:
            self._clear_and_type("module-order", order)

    def set_show_in_dashboard(self, *, enabled: bool) -> None:
        self._set_checkbox("module-show-in-dashboard", checked=enabled)

    def set_show_in_sidebar(self, *, enabled: bool) -> None:
        self._set_checkbox("module-show-in-sidebar", checked=enabled)

    def save(self) -> ModulesListPage:
        self._click(self.save_submit_testid)
        page = ModulesListPage(self.test_case)
        page.wait_until_loaded()
        return page
