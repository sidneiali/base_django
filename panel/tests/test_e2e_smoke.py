"""Smoke tests E2E com Selenium para os fluxos mais sensíveis do shell."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

pytestmark = pytest.mark.e2e

User = get_user_model()


def _find_edge_binary() -> str | None:
    """Encontra um binário do Microsoft Edge em caminhos conhecidos."""

    candidates = [
        os.environ.get("E2E_EDGE_BINARY", "").strip(),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file():
            return str(path)
    return None


class PanelE2ESmokeTests(StaticLiveServerTestCase):
    """Valida no navegador real os fluxos críticos de autenticação e navegação."""

    host = "127.0.0.1"
    browser: WebDriver
    wait: WebDriverWait
    username = "e2e-user"
    password = "SenhaSegura@123"

    @classmethod
    def setUpClass(cls) -> None:
        """Inicializa o navegador headless usado pelos smoke tests."""

        super().setUpClass()

        edge_binary = _find_edge_binary()
        if edge_binary is None:
            raise unittest.SkipTest(
                "Microsoft Edge não encontrado. Defina E2E_EDGE_BINARY para habilitar os testes E2E."
            )

        options = EdgeOptions()
        options.binary_location = edge_binary
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1440,1200")

        try:
            cls.browser = webdriver.Edge(options=options)
        except WebDriverException as exc:
            raise unittest.SkipTest(
                f"Não foi possível iniciar o Edge WebDriver: {exc}"
            ) from exc

        cls.wait = WebDriverWait(cls.browser, 10)

    @classmethod
    def tearDownClass(cls) -> None:
        """Encerra o navegador ao final da classe de testes."""

        browser = getattr(cls, "browser", None)
        if browser is not None:
            browser.quit()
        super().tearDownClass()

    def setUp(self) -> None:
        """Garante um estado limpo do navegador e do usuário de teste."""

        self.browser.delete_all_cookies()
        User.objects.filter(username=self.username).delete()
        User.objects.create_user(
            username=self.username,
            email="e2e-user@example.com",
            password=self.password,
        )

    def _open(self, path: str) -> None:
        """Abre um caminho relativo do projeto no live server."""

        self.browser.get(f"{self.live_server_url}{path}")

    def _login(self) -> None:
        """Realiza login pelo formulário real da aplicação."""

        self._open(reverse("login"))

        username_input = self.wait.until(
            EC.visibility_of_element_located((By.NAME, "username"))
        )
        password_input = self.wait.until(
            EC.visibility_of_element_located((By.NAME, "password"))
        )
        username_input.clear()
        username_input.send_keys(self.username)
        password_input.clear()
        password_input.send_keys(self.password)

        submit_button = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        submit_button.click()

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-page-title="Dashboard"]'))
        )

    def _open_user_menu(self) -> None:
        """Expande o dropdown do usuário no topo da aplicação."""

        toggle = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Abrir menu do usuário']"))
        )
        toggle.click()
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".dropdown-menu.show"))
        )

    def test_login_and_logout_smoke(self) -> None:
        """O usuário deve conseguir entrar no dashboard e sair pela topbar."""

        self._login()
        self.assertTrue(self.browser.current_url.endswith(reverse("dashboard")))

        self._open_user_menu()
        logout_button = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".dropdown-menu.show button[type='submit']"))
        )
        logout_button.click()

        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".auth-cover-form-header__title"))
        )
        self.assertIn(reverse("login"), self.browser.current_url)
        self.assertIn("Entrar na sua conta", self.browser.page_source)

    def test_topbar_my_password_link_opens_account_page(self) -> None:
        """O link "Minha senha" deve navegar para a conta autenticada via HTMX."""

        self._login()
        self._open_user_menu()

        password_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Minha senha"))
        )
        password_link.click()

        self.wait.until(
            lambda browser: browser.current_url.endswith(
                reverse("account_password_change")
            )
        )
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-page-title="Minha senha"]'))
        )
        self.assertTrue(
            self.browser.current_url.endswith(reverse("account_password_change"))
        )
        self.assertIn("Alterar senha", self.browser.page_source)
