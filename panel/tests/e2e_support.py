"""Apoio compartilhado pelos smoke tests E2E do painel."""

from __future__ import annotations

import os
import shutil
import time
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from core.models import AuditLog, Module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .audit_test_support import AuditTestDataFactory

User = get_user_model()


class PanelE2EDataFactory:
    """Factory pequena para reduzir setup repetido nos smoke tests E2E."""

    def __init__(self, *, default_password: str) -> None:
        self.default_password = default_password

    def create_user(
        self,
        username: str,
        *,
        email: str | None = None,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        groups: Iterable[Group] = (),
        permission_codenames: Iterable[str] = (),
    ) -> Any:
        """Cria um usuário com defaults previsíveis para os cenários E2E."""

        user = User.objects.create_user(
            username=username,
            email=email or f"{username}@example.com",
            password=password or self.default_password,
            first_name=first_name,
            last_name=last_name,
        )
        group_list = list(groups)
        if group_list:
            user.groups.add(*group_list)
        permission_codename_list = list(permission_codenames)
        if permission_codename_list:
            permissions = Permission.objects.filter(
                codename__in=permission_codename_list
            )
            user.user_permissions.add(*permissions)
        return user

    def create_group(
        self,
        name: str,
        *,
        permission_codenames: Iterable[str] = (),
    ) -> Group:
        """Cria um grupo com permissões opcionais."""

        group = Group.objects.create(name=name)
        permission_codename_list = list(permission_codenames)
        if permission_codename_list:
            permissions = Permission.objects.filter(
                codename__in=permission_codename_list
            )
            group.permissions.add(*permissions)
        return group

    def create_module(
        self,
        *,
        name: str,
        slug: str,
        description: str,
        icon: str = "ti ti-layout-grid",
        url_name: str = "module_entry",
        app_label: str = "",
        permission_codename: str = "",
        menu_group: str = "Operação",
        order: int = 10,
        is_active: bool = True,
        show_in_dashboard: bool = True,
        show_in_sidebar: bool = True,
    ) -> Module:
        """Cria um módulo com defaults úteis para os smoke tests."""

        return Module.objects.create(
            name=name,
            slug=slug,
            description=description,
            icon=icon,
            url_name=url_name,
            app_label=app_label,
            permission_codename=permission_codename,
            menu_group=menu_group,
            order=order,
            is_active=is_active,
            show_in_dashboard=show_in_dashboard,
            show_in_sidebar=show_in_sidebar,
        )


def _find_edge_binary() -> str | None:
    """Encontra um binário do Microsoft Edge em env, PATH ou caminhos conhecidos."""

    candidates = [
        os.environ.get("E2E_EDGE_BINARY", "").strip(),
        shutil.which("msedge") or "",
        shutil.which("microsoft-edge") or "",
        shutil.which("microsoft-edge-stable") or "",
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


def _env_flag(name: str, default: bool) -> bool:
    """Converte flags de ambiente em booleanos previsíveis."""

    raw_value = os.environ.get(name, "").strip().lower()
    if not raw_value:
        return default
    return raw_value not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    """Lê inteiros de ambiente com fallback seguro."""

    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _running_in_ci() -> bool:
    """Detecta execução em ambiente de integração contínua."""

    return _env_flag("GITHUB_ACTIONS", default=False) or _env_flag(
        "CI", default=False
    )


class PanelE2EBase(StaticLiveServerTestCase):
    """Base compartilhada para smoke tests E2E com Selenium."""

    host = "127.0.0.1"
    browser: WebDriver
    wait: WebDriverWait
    factory: PanelE2EDataFactory
    audit_factory: AuditTestDataFactory
    username = "e2e-user"
    email = "e2e-user@example.com"
    password = "SenhaSegura@123"
    headless = False
    slow_mo_seconds = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        """Inicializa o navegador usado pelos smoke tests."""

        super().setUpClass()

        edge_binary = _find_edge_binary()
        if edge_binary is None:
            raise unittest.SkipTest(
                "Microsoft Edge não encontrado. Defina E2E_EDGE_BINARY para habilitar os testes E2E."
            )

        cls.headless = _env_flag("E2E_HEADLESS", default=_running_in_ci())
        cls.slow_mo_seconds = max(_env_int("E2E_SLOW_MO_MS", 0), 0) / 1000

        options = EdgeOptions()
        options.binary_location = edge_binary
        if cls.headless:
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1440,1200")

        try:
            cls.browser = webdriver.Edge(options=options)
        except WebDriverException as exc:
            raise unittest.SkipTest(
                f"Não foi possível iniciar o Edge WebDriver: {exc}"
            ) from exc

        try:
            cls.browser.maximize_window()
        except WebDriverException:
            pass

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
        self.factory = PanelE2EDataFactory(default_password=self.password)
        self.audit_factory = AuditTestDataFactory(default_password=self.password)
        User.objects.filter(username=self.username).delete()
        User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
        )
        Module.objects.filter(slug__startswith="e2e-").delete()

    def _open(self, path: str) -> None:
        """Abre um caminho relativo do projeto no live server."""

        self.browser.get(f"{self.live_server_url}{path}")
        self._pause_for_demo()

    def _locator_by_testid(self, testid: str) -> tuple[str, str]:
        """Monta um locator CSS estável baseado em `data-teste`."""

        return (By.CSS_SELECTOR, f'[data-teste="{testid}"]')

    def _test_user(self):
        """Retorna o usuário principal usado pelos cenários E2E."""

        return User.objects.get(username=self.username)

    def _grant_permissions(self, *codenames: str) -> None:
        """Concede permissões do Django ao usuário principal do cenário."""

        permissions = Permission.objects.filter(codename__in=codenames)
        self._test_user().user_permissions.add(*permissions)

    def _pause_for_demo(self) -> None:
        """Desacelera o teste quando o modo visível for usado manualmente."""

        if self.slow_mo_seconds > 0:
            time.sleep(self.slow_mo_seconds)

    def _fetch_response_in_browser(self, url: str) -> dict[str, object]:
        """Executa um fetch autenticado usando a sessão atual do navegador."""

        response = self.browser.execute_async_script(
            """
            const url = arguments[0];
            const done = arguments[arguments.length - 1];

            fetch(url, { credentials: "same-origin" })
              .then(async (response) => {
                done({
                  ok: response.ok,
                  status: response.status,
                  contentType: response.headers.get("content-type") || "",
                  contentDisposition: response.headers.get("content-disposition") || "",
                  body: await response.text(),
                });
              })
              .catch((error) => {
                done({
                  ok: false,
                  status: 0,
                  contentType: "",
                  contentDisposition: "",
                  body: "",
                  error: String(error),
                });
              });
            """,
            url,
        )

        status = int(response.get("status", 0))
        if status == 0:
            error = str(response.get("error", "erro desconhecido"))
            raise AssertionError(
                f"Falha ao buscar {url!r} no contexto do navegador: {error}"
            )

        return response

    def _select_dual_list_option(self, option) -> None:
        """Marca uma option do dual-list de forma estável antes da ação."""

        self.browser.execute_script(
            """
            arguments[0].scrollIntoView({block: "center"});
            arguments[0].selected = true;
            arguments[0].dispatchEvent(new Event("change", {bubbles: true}));
            """,
            option,
        )
        self._pause_for_demo()

    def _login(self) -> None:
        """Realiza login pelo formulário real da aplicação."""

        self._open(reverse("login"))

        username_input = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("login-username")
            )
        )
        password_input = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("login-password")
            )
        )
        username_input.clear()
        username_input.send_keys(self.email)
        password_input.clear()
        password_input.send_keys(self.password)

        submit_button = self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid("login-submit"))
        )
        submit_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("dashboard-page"))
        )

    def _open_user_menu(self) -> None:
        """Expande o dropdown do usuário no topo da aplicação."""

        toggle = self.wait.until(
            EC.element_to_be_clickable(
                self._locator_by_testid("topbar-user-toggle")
            )
        )
        toggle.click()
        self._pause_for_demo()
        self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("topbar-user-menu")
            )
        )

    def _open_topbar_shortcuts(self) -> None:
        """Expande a seção de atalhos operacionais da topbar."""

        self._open_user_menu()
        toggle = self.wait.until(
            EC.element_to_be_clickable(
                self._locator_by_testid("topbar-shortcuts-toggle")
            )
        )
        toggle.click()
        self._pause_for_demo()
        self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("topbar-shortcuts-panel")
            )
        )

    def _topbar_shortcut_locator(self, shortcut_key: str) -> tuple[str, str]:
        """Monta o locator de um atalho específico da topbar."""

        selector = (
            '[data-teste="topbar-shortcut-link"]'
            f'[data-topbar-shortcut="{shortcut_key}"]'
        )
        return (By.CSS_SELECTOR, selector)

    def _topbar_shortcut(self, shortcut_key: str):
        """Localiza um atalho específico da topbar."""

        return self.wait.until(
            EC.element_to_be_clickable(self._topbar_shortcut_locator(shortcut_key))
        )

    def _create_audit_log(
        self,
        *,
        action: str,
        actor_identifier: str,
        object_repr: str,
        request_id: str,
        actor: object | None = None,
    ) -> AuditLog:
        """Cria um evento de auditoria controlado para os smoke tests."""

        return self.audit_factory.create_log(
            action=action,
            actor=actor if actor is not None else self._test_user(),
            actor_identifier=actor_identifier,
            object_repr=object_repr,
            object_verbose_name="Evento",
            request_method="GET",
            path="/painel/auditoria/",
            request_id=request_id,
        )

    def _audit_row_locator(self, request_id: str) -> tuple[str, str]:
        """Monta o locator da linha da tabela correspondente ao request id informado."""

        selector = f'[data-teste="audit-row"][data-request-id="{request_id}"]'
        return (By.CSS_SELECTOR, selector)

    def _audit_row(self, request_id: str):
        """Localiza a linha da tabela correspondente ao request id informado."""

        return self.wait.until(
            EC.presence_of_element_located(self._audit_row_locator(request_id))
        )

    def _module_row_locator(self, module_name: str) -> tuple[str, str]:
        """Monta o locator da linha da tabela correspondente ao módulo informado."""

        slug = Module.objects.only("slug").get(name=module_name).slug
        selector = '[data-teste="module-row"]' f'[data-module-slug="{slug}"]'
        return (By.CSS_SELECTOR, selector)

    def _module_row(self, module_name: str):
        """Localiza a linha da tabela correspondente ao módulo informado."""

        return self.wait.until(
            EC.presence_of_element_located(self._module_row_locator(module_name))
        )

    def _user_row_locator(self, username: str) -> tuple[str, str]:
        """Monta o locator da linha da tabela correspondente ao usuário informado."""

        selector = f'[data-teste="user-row"][data-username="{username}"]'
        return (By.CSS_SELECTOR, selector)

    def _user_row(self, username: str):
        """Localiza a linha da tabela correspondente ao usuário informado."""

        return self.wait.until(
            EC.presence_of_element_located(self._user_row_locator(username))
        )

    def _group_row_locator(self, group_name: str) -> tuple[str, str]:
        """Monta o locator da linha da tabela correspondente ao grupo informado."""

        selector = f'[data-teste="group-row"][data-group-name="{group_name}"]'
        return (By.CSS_SELECTOR, selector)

    def _group_row(self, group_name: str):
        """Localiza a linha da tabela correspondente ao grupo informado."""

        return self.wait.until(
            EC.presence_of_element_located(self._group_row_locator(group_name))
        )
