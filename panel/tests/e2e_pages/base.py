"""Infraestrutura base compartilhada entre page objects E2E."""

from __future__ import annotations

from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from ..e2e_support import PanelE2EBase


class BasePageObject:
    """Pequena camada compartilhada para reduzir ruído nos smoke tests."""

    def __init__(self, test_case: PanelE2EBase) -> None:
        self.test_case = test_case

    @property
    def browser(self):
        return self.test_case.browser

    @property
    def wait(self):
        return self.test_case.wait

    def locator_by_testid(self, testid: str) -> tuple[str, str]:
        return self.test_case._locator_by_testid(testid)

    def find(self, testid: str) -> WebElement:
        return self.browser.find_element(*self.locator_by_testid(testid))

    def click(self, testid: str) -> WebElement:
        element = self.wait_clickable(testid)
        element.click()
        self.pause()
        return element

    def clear_and_type(self, testid: str, value: str) -> WebElement:
        element = self.wait_visible(testid)
        element.clear()
        element.send_keys(value)
        return element

    def wait_present(self, testid: str) -> WebElement:
        return self.wait.until(
            EC.presence_of_element_located(self.locator_by_testid(testid))
        )

    def wait_visible(self, testid: str) -> WebElement:
        return self.wait.until(
            EC.visibility_of_element_located(self.locator_by_testid(testid))
        )

    def wait_clickable(self, testid: str) -> WebElement:
        return self.wait.until(
            EC.element_to_be_clickable(self.locator_by_testid(testid))
        )

    def wait_for_url_fragment(self, fragment: str) -> None:
        self.wait.until(lambda browser: fragment in browser.current_url)

    def wait_text(self, locator: tuple[str, str], text: str) -> None:
        self.wait.until(EC.text_to_be_present_in_element(locator, text))

    def wait_text_in_testid(self, testid: str, text: str) -> None:
        self.wait_text(self.locator_by_testid(testid), text)

    def wait_text_not_in_testid(self, testid: str, text: str) -> None:
        self.wait.until_not(
            lambda browser: text
            in browser.find_element(*self.locator_by_testid(testid)).text
        )

    def set_checkbox(self, testid: str, *, checked: bool) -> None:
        checkbox = self.find(testid)
        if checkbox.is_selected() != checked:
            checkbox.click()
            self.pause()

    def xpath_literal(self, value: str) -> str:
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

    def select_option_by_xpath(
        self,
        *,
        select_testid: str,
        option_xpath: str,
    ) -> WebElement:
        select_box = self.wait_visible(select_testid)
        option = select_box.find_element(By.XPATH, option_xpath)
        self.test_case._select_dual_list_option(option)
        return option

    def move_dual_list_option(
        self,
        *,
        source_testid: str,
        option_xpath: str,
        action_testid: str,
        target_testid: str,
        expected_text: str,
    ) -> None:
        self.select_option_by_xpath(
            select_testid=source_testid,
            option_xpath=option_xpath,
        )
        self.click(action_testid)
        self.wait_text_in_testid(target_testid, expected_text)

    def remove_dual_list_option(
        self,
        *,
        source_testid: str,
        option_xpath: str,
        action_testid: str,
        removed_text: str,
    ) -> None:
        self.select_option_by_xpath(
            select_testid=source_testid,
            option_xpath=option_xpath,
        )
        self.click(action_testid)
        self.wait_text_not_in_testid(source_testid, removed_text)

    def pause(self) -> None:
        self.test_case._pause_for_demo()
