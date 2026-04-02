"""Smoke tests E2E com Selenium para os fluxos mais sensíveis do shell."""

from __future__ import annotations

import os
import time
import unittest
from datetime import timedelta
from pathlib import Path

import pytest
from core.models import AuditLog, Module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
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


class PanelE2ESmokeTests(StaticLiveServerTestCase):
    """Valida no navegador real os fluxos críticos de autenticação e navegação."""

    host = "127.0.0.1"
    browser: WebDriver
    wait: WebDriverWait
    username = "e2e-user"
    password = "SenhaSegura@123"
    headless = True
    slow_mo_seconds = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        """Inicializa o navegador headless usado pelos smoke tests."""

        super().setUpClass()

        edge_binary = _find_edge_binary()
        if edge_binary is None:
            raise unittest.SkipTest(
                "Microsoft Edge não encontrado. Defina E2E_EDGE_BINARY para habilitar os testes E2E."
            )

        cls.headless = _env_flag("E2E_HEADLESS", default=True)
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
        User.objects.filter(username=self.username).delete()
        User.objects.create_user(
            username=self.username,
            email="e2e-user@example.com",
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
        username_input.send_keys(self.username)
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

    def _create_audit_log(
        self,
        *,
        action: str,
        actor_identifier: str,
        object_repr: str,
        request_id: str,
    ) -> AuditLog:
        """Cria um evento de auditoria controlado para os smoke tests."""

        return AuditLog.objects.create(
            action=action,
            actor=self._test_user(),
            actor_identifier=actor_identifier,
            object_repr=object_repr,
            object_verbose_name="Evento",
            request_method="GET",
            path="/painel/auditoria/",
            metadata={"request_id": request_id},
        )

    def test_login_and_logout_smoke(self) -> None:
        """O usuário deve conseguir entrar no dashboard e sair pela topbar."""

        self._login()
        self.assertTrue(self.browser.current_url.endswith(reverse("dashboard")))

        self._open_user_menu()
        logout_button = self.wait.until(
            EC.element_to_be_clickable(
                self._locator_by_testid("topbar-logout-submit")
            )
        )
        logout_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.visibility_of_element_located(self._locator_by_testid("login-title"))
        )
        self.assertIn(reverse("login"), self.browser.current_url)
        self.assertIn("Entrar na sua conta", self.browser.page_source)

    def test_topbar_my_password_link_opens_account_page(self) -> None:
        """O link "Minha senha" deve navegar para a conta autenticada via HTMX."""

        self._login()
        self._open_user_menu()

        password_link = self.wait.until(
            EC.element_to_be_clickable(
                self._locator_by_testid("topbar-my-password-link")
            )
        )
        password_link.click()
        self._pause_for_demo()

        self.wait.until(
            lambda browser: browser.current_url.endswith(
                reverse("account_password_change")
            )
        )
        self.wait.until(
            EC.presence_of_element_located(
                self._locator_by_testid("account-password-page")
            )
        )
        self.assertTrue(
            self.browser.current_url.endswith(reverse("account_password_change"))
        )
        self.assertIn("Alterar senha", self.browser.page_source)

    def test_audit_list_filter_smoke(self) -> None:
        """A tela de auditoria deve filtrar eventos reais no navegador."""

        self._grant_permissions("view_auditlog")
        self._create_audit_log(
            action=AuditLog.ACTION_LOGIN,
            actor_identifier=self.username,
            object_repr="Login do operador",
            request_id="req-filter-match",
        )
        old_log = self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor_identifier=self.username,
            object_repr="Atualização antiga",
            request_id="req-filter-old",
        )
        AuditLog.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )

        self._login()
        self._open(reverse("panel_audit_logs_list"))

        actor_input = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("audit-filter-actor")
            )
        )
        actor_input.clear()
        actor_input.send_keys(self.username)

        object_input = self.browser.find_element(
            *self._locator_by_testid("audit-filter-object-query")
        )
        object_input.clear()
        object_input.send_keys("req-filter-match")

        submit_button = self.browser.find_element(
            *self._locator_by_testid("audit-filter-submit"),
        )
        submit_button.click()
        self._pause_for_demo()

        self.wait.until(lambda browser: "object_query=req-filter-match" in browser.current_url)
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Login do operador",
            )
        )
        self.assertIn("Login do operador", self.browser.page_source)
        self.assertNotIn("Atualização antiga", self.browser.page_source)

    def test_audit_detail_back_link_preserves_filters(self) -> None:
        """O drill-down deve abrir e o retorno deve manter os filtros atuais."""

        self._grant_permissions("view_auditlog")
        self._create_audit_log(
            action=AuditLog.ACTION_UPDATE,
            actor_identifier=self.username,
            object_repr="Evento detalhado",
            request_id="req-detail-smoke",
        )

        self._login()
        query = "?actor=e2e-user&object_query=req-detail-smoke"
        self._open(reverse("panel_audit_logs_list") + query)

        detail_link = self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid("audit-detail-link"))
        )
        detail_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(
                self._locator_by_testid("audit-detail-page")
            )
        )
        self.assertIn("Evento detalhado", self.browser.page_source)
        self.assertIn("req-detail-smoke", self.browser.page_source)

        back_link = self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid("audit-back-link"))
        )
        back_href = back_link.get_attribute("href") or ""
        self.assertIn(query, back_href)
        back_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("audit-list-page"))
        )
        self.wait.until(lambda browser: "object_query=req-detail-smoke" in browser.current_url)
        self.assertIn("Evento detalhado", self.browser.page_source)

    def _module_row_locator(self, module_name: str) -> tuple[str, str]:
        """Monta o locator da linha da tabela correspondente ao módulo informado."""

        slug = Module.objects.only("slug").get(name=module_name).slug
        selector = (
            '[data-teste="module-row"]'
            f'[data-module-slug="{slug}"]'
        )
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

    def test_modules_list_filter_smoke(self) -> None:
        """A listagem de módulos deve filtrar resultados reais no navegador."""

        self._grant_permissions("view_module")
        Module.objects.create(
            name="E2E Financeiro",
            slug="e2e-financeiro",
            description="Fluxo financeiro",
            icon="ti ti-cash",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=10,
            is_active=True,
        )
        Module.objects.create(
            name="E2E CRM",
            slug="e2e-crm",
            description="Fluxo comercial",
            icon="ti ti-users",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=20,
            is_active=True,
        )

        self._login()
        self._open(reverse("panel_modules_list"))

        query_input = self.wait.until(
            EC.visibility_of_element_located(self._locator_by_testid("modules-query"))
        )
        query_input.clear()
        query_input.send_keys("financeiro")

        search_button = self.browser.find_element(
            *self._locator_by_testid("modules-filter-submit"),
        )
        search_button.click()
        self._pause_for_demo()

        self.wait.until(lambda browser: "q=financeiro" in browser.current_url)
        self.wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, "tbody"), "E2E Financeiro")
        )
        modules_table = self.browser.find_element(
            *self._locator_by_testid("modules-table")
        )
        self.assertIn("E2E Financeiro", modules_table.text)
        self.assertNotIn("E2E CRM", modules_table.text)

    def test_module_create_and_toggle_status_smoke(self) -> None:
        """O operador deve conseguir criar, inativar e reativar um módulo no navegador."""

        self._grant_permissions("view_module", "add_module", "change_module")

        self._login()
        self._open(reverse("panel_modules_list"))

        new_link = self.wait.until(
            EC.element_to_be_clickable(
                self._locator_by_testid("modules-create-link")
            )
        )
        new_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("module-form-page"))
        )
        self.browser.find_element(
            *self._locator_by_testid("module-name")
        ).send_keys("E2E Módulo")
        self.browser.find_element(
            *self._locator_by_testid("module-slug")
        ).send_keys("e2e-modulo")
        self.browser.find_element(
            *self._locator_by_testid("module-description")
        ).send_keys("Criado pelo smoke test")
        self.browser.find_element(
            *self._locator_by_testid("module-icon")
        ).send_keys("ti ti-layout-grid")
        menu_group_input = self.browser.find_element(
            *self._locator_by_testid("module-menu-group")
        )
        menu_group_input.clear()
        menu_group_input.send_keys("Operação")
        url_name_input = self.browser.find_element(
            *self._locator_by_testid("module-url-name")
        )
        url_name_input.clear()
        url_name_input.send_keys("module_entry")
        order_input = self.browser.find_element(
            *self._locator_by_testid("module-order")
        )
        order_input.clear()
        order_input.send_keys("25")

        save_button = self.browser.find_element(
            *self._locator_by_testid("module-save-submit")
        )
        save_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("modules-page"))
        )
        self.wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, "tbody"), "E2E Módulo")
        )
        self.assertTrue(Module.objects.filter(slug="e2e-modulo").exists())

        row_locator = self._module_row_locator("E2E Módulo")
        row = self.wait.until(EC.presence_of_element_located(row_locator))
        self.assertIn("Ativo", row.text)
        deactivate_button = row.find_element(
            *self._locator_by_testid("module-deactivate-submit")
        )
        deactivate_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.text_to_be_present_in_element(row_locator, "Inativo")
        )
        module = Module.objects.get(slug="e2e-modulo")
        self.assertFalse(module.is_active)

        row = self.wait.until(EC.presence_of_element_located(row_locator))
        activate_button = row.find_element(
            *self._locator_by_testid("module-activate-submit")
        )
        activate_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.text_to_be_present_in_element(row_locator, "Ativo")
        )
        module.refresh_from_db()
        self.assertTrue(module.is_active)

    def test_users_list_filter_smoke(self) -> None:
        """A listagem de usuários deve filtrar resultados reais no navegador."""

        self._grant_permissions("view_user")
        User.objects.create_user(
            username="ana-e2e",
            email="ana-e2e@example.com",
            password="SenhaSegura@123",
        )
        User.objects.create_user(
            username="bruno-e2e",
            email="bruno-e2e@example.com",
            password="SenhaSegura@123",
        )

        self._login()
        self._open(reverse("panel_users_list"))

        query_input = self.wait.until(
            EC.visibility_of_element_located(self._locator_by_testid("users-query"))
        )
        query_input.clear()
        query_input.send_keys("ana-e2e")

        search_button = self.browser.find_element(
            *self._locator_by_testid("users-filter-submit"),
        )
        search_button.click()
        self._pause_for_demo()

        self.wait.until(lambda browser: "q=ana-e2e" in browser.current_url)
        self.wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, "tbody"), "ana-e2e")
        )
        self.assertIn("ana-e2e", self.browser.page_source)
        self.assertNotIn("bruno-e2e", self.browser.page_source)

    def test_user_create_with_group_smoke(self) -> None:
        """O operador deve conseguir criar usuário e associar grupo pela dual-list."""

        self._grant_permissions("view_user", "add_user")
        Group.objects.create(name="Operação E2E")

        self._login()
        self._open(reverse("panel_users_list"))

        new_link = self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid("users-create-link"))
        )
        new_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("user-form-page"))
        )
        self.browser.find_element(
            *self._locator_by_testid("user-username")
        ).send_keys("novo-e2e")
        self.browser.find_element(
            *self._locator_by_testid("user-email")
        ).send_keys("novo-e2e@example.com")
        self.browser.find_element(
            *self._locator_by_testid("user-first-name")
        ).send_keys("Novo")
        self.browser.find_element(
            *self._locator_by_testid("user-last-name")
        ).send_keys("E2E")
        self.browser.find_element(
            *self._locator_by_testid("user-password")
        ).send_keys("SenhaSegura@123")

        interval_input = self.browser.find_element(
            *self._locator_by_testid("user-auto-refresh-interval")
        )
        interval_input.clear()
        interval_input.send_keys("30")

        available_groups = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("user-groups-available")
            )
        )
        operation_group = available_groups.find_element(
            By.XPATH,
            ".//option[normalize-space()='Operação E2E']",
        )
        operation_group.click()
        self._pause_for_demo()

        add_group_button = self.browser.find_element(
            *self._locator_by_testid("user-groups-add"),
        )
        add_group_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.text_to_be_present_in_element(
                self._locator_by_testid("user-groups-chosen"),
                "Operação E2E",
            )
        )

        save_button = self.browser.find_element(
            *self._locator_by_testid("user-save-submit")
        )
        save_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("users-page"))
        )
        self.wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, "tbody"), "novo-e2e")
        )

        created_user = User.objects.get(username="novo-e2e")
        self.assertEqual(created_user.email, "novo-e2e@example.com")
        self.assertTrue(created_user.groups.filter(name="Operação E2E").exists())
        self.assertIn("novo-e2e", self._user_row("novo-e2e").text)

    def test_user_update_with_group_smoke(self) -> None:
        """O operador deve conseguir editar usuário e trocar seus grupos."""

        self._grant_permissions("view_user", "change_user")
        original_group = Group.objects.create(name="Grupo Atual E2E")
        Group.objects.create(name="Grupo Novo E2E")
        user = User.objects.create_user(
            username="editar-e2e",
            email="editar-e2e@example.com",
            password="SenhaSegura@123",
            first_name="Editar",
            last_name="Original",
        )
        user.groups.add(original_group)

        self._login()
        self._open(reverse("panel_users_list"))

        row = self._user_row("editar-e2e")
        edit_link = row.find_element(
            *self._locator_by_testid("user-edit-link")
        )
        edit_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("user-form-page"))
        )
        email_input = self.browser.find_element(
            *self._locator_by_testid("user-email")
        )
        email_input.clear()
        email_input.send_keys("editar-atualizado@example.com")

        first_name_input = self.browser.find_element(
            *self._locator_by_testid("user-first-name")
        )
        first_name_input.clear()
        first_name_input.send_keys("Editado")

        last_name_input = self.browser.find_element(
            *self._locator_by_testid("user-last-name")
        )
        last_name_input.clear()
        last_name_input.send_keys("Atualizado")

        chosen_groups = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("user-groups-chosen")
            )
        )
        current_group = chosen_groups.find_element(
            By.XPATH,
            ".//option[normalize-space()='Grupo Atual E2E']",
        )
        self._select_dual_list_option(current_group)

        remove_group_button = self.browser.find_element(
            *self._locator_by_testid("user-groups-remove"),
        )
        remove_group_button.click()
        self._pause_for_demo()

        self.wait.until_not(
            lambda browser: "Grupo Atual E2E"
            in browser.find_element(
                *self._locator_by_testid("user-groups-chosen")
            ).text
        )

        available_groups = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("user-groups-available")
            )
        )
        replacement_option = available_groups.find_element(
            By.XPATH,
            ".//option[normalize-space()='Grupo Novo E2E']",
        )
        self._select_dual_list_option(replacement_option)

        add_group_button = self.browser.find_element(
            *self._locator_by_testid("user-groups-add"),
        )
        add_group_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.text_to_be_present_in_element(
                self._locator_by_testid("user-groups-chosen"),
                "Grupo Novo E2E",
            )
        )

        save_button = self.browser.find_element(
            *self._locator_by_testid("user-save-submit")
        )
        save_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("users-page"))
        )
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "editar-e2e",
            )
        )

        user.refresh_from_db()
        self.assertEqual(user.email, "editar-atualizado@example.com")
        self.assertEqual(user.first_name, "Editado")
        self.assertEqual(user.last_name, "Atualizado")
        self.assertFalse(user.groups.filter(name="Grupo Atual E2E").exists())
        self.assertTrue(user.groups.filter(name="Grupo Novo E2E").exists())
        self.assertIn("editar-atualizado@example.com", self._user_row("editar-e2e").text)

    def test_groups_list_filter_smoke(self) -> None:
        """A listagem de grupos deve filtrar resultados reais no navegador."""

        self._grant_permissions("view_group")
        Group.objects.create(name="Grupo Financeiro E2E")
        Group.objects.create(name="Grupo Comercial E2E")

        self._login()
        self._open(reverse("panel_groups_list"))

        query_input = self.wait.until(
            EC.visibility_of_element_located(self._locator_by_testid("groups-query"))
        )
        query_input.clear()
        query_input.send_keys("Financeiro")

        search_button = self.browser.find_element(
            *self._locator_by_testid("groups-filter-submit"),
        )
        search_button.click()
        self._pause_for_demo()

        self.wait.until(lambda browser: "q=Financeiro" in browser.current_url)
        groups_table = self.browser.find_element(
            *self._locator_by_testid("groups-table")
        )
        self.assertIn("Grupo Financeiro E2E", groups_table.text)
        self.assertNotIn("Grupo Comercial E2E", groups_table.text)

    def test_group_create_with_permission_smoke(self) -> None:
        """O operador deve conseguir criar grupo e associar permissão pela dual-list."""

        self._grant_permissions("view_group", "add_group")

        self._login()
        self._open(reverse("panel_groups_list"))

        new_link = self.wait.until(
            EC.element_to_be_clickable(self._locator_by_testid("groups-create-link"))
        )
        new_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("group-form-page"))
        )
        self.browser.find_element(
            *self._locator_by_testid("group-name")
        ).send_keys("Grupo Operação E2E")

        available_permissions = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("group-permissions-available")
            )
        )
        target_permission = available_permissions.find_element(
            By.XPATH,
            ".//option[contains(normalize-space(), 'Pode visualizar') and contains(normalize-space(), 'Usuário')]",
        )
        target_permission.click()
        self._pause_for_demo()

        add_permission_button = self.browser.find_element(
            *self._locator_by_testid("group-permissions-add"),
        )
        add_permission_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.text_to_be_present_in_element(
                self._locator_by_testid("group-permissions-chosen"),
                "Pode visualizar",
            )
        )

        save_button = self.browser.find_element(
            *self._locator_by_testid("group-save-submit")
        )
        save_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("groups-page"))
        )
        self.wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, "tbody"), "Grupo Operação E2E")
        )

        created_group = Group.objects.get(name="Grupo Operação E2E")
        self.assertTrue(created_group.permissions.filter(codename="view_user").exists())
        self.assertIn("Grupo Operação E2E", self._group_row("Grupo Operação E2E").text)

    def test_group_update_permissions_smoke(self) -> None:
        """O operador deve conseguir editar um grupo e trocar suas permissões."""

        self._grant_permissions("view_group", "change_group")
        group = Group.objects.create(name="Grupo Edição E2E")
        group.permissions.add(Permission.objects.get(codename="view_user"))

        self._login()
        self._open(reverse("panel_groups_list"))

        row = self._group_row("Grupo Edição E2E")
        edit_link = row.find_element(
            *self._locator_by_testid("group-edit-link")
        )
        edit_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("group-form-page"))
        )
        name_input = self.browser.find_element(
            *self._locator_by_testid("group-name")
        )
        name_input.clear()
        name_input.send_keys("Grupo Edição Atualizado")

        chosen_permissions = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("group-permissions-chosen")
            )
        )
        current_permission = chosen_permissions.find_element(
            By.XPATH,
            ".//option[contains(normalize-space(), 'Pode visualizar') and contains(normalize-space(), 'Usuário')]",
        )
        self._select_dual_list_option(current_permission)

        remove_permission_button = self.browser.find_element(
            *self._locator_by_testid("group-permissions-remove"),
        )
        remove_permission_button.click()
        self._pause_for_demo()

        self.wait.until_not(
            lambda browser: "Pode visualizar"
            in browser.find_element(
                *self._locator_by_testid("group-permissions-chosen")
            ).text
        )

        available_permissions = self.wait.until(
            EC.visibility_of_element_located(
                self._locator_by_testid("group-permissions-available")
            )
        )
        replacement_permission = available_permissions.find_element(
            By.XPATH,
            ".//option[contains(normalize-space(), 'Pode alterar') and contains(normalize-space(), 'Usuário')]",
        )
        self._select_dual_list_option(replacement_permission)

        add_permission_button = self.browser.find_element(
            *self._locator_by_testid("group-permissions-add"),
        )
        add_permission_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.text_to_be_present_in_element(
                self._locator_by_testid("group-permissions-chosen"),
                "Pode alterar",
            )
        )

        save_button = self.browser.find_element(
            *self._locator_by_testid("group-save-submit")
        )
        save_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("groups-page"))
        )
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "tbody"),
                "Grupo Edição Atualizado",
            )
        )

        group.refresh_from_db()
        self.assertEqual(group.name, "Grupo Edição Atualizado")
        self.assertTrue(group.permissions.filter(codename="change_user").exists())
        self.assertFalse(group.permissions.filter(codename="view_user").exists())
        self.assertIn("Grupo Edição Atualizado", self._group_row(group.name).text)

    def test_module_update_visibility_smoke(self) -> None:
        """O operador deve conseguir editar um módulo e alterar sua visibilidade."""

        self._grant_permissions("view_module", "change_module")
        Module.objects.create(
            name="E2E Módulo Editável",
            slug="e2e-modulo-editavel",
            description="Descrição inicial",
            icon="ti ti-layout-grid",
            url_name="module_entry",
            app_label="",
            permission_codename="",
            menu_group="Operação",
            order=15,
            is_active=True,
            show_in_dashboard=True,
            show_in_sidebar=True,
        )

        self._login()
        self._open(reverse("panel_modules_list"))

        row = self._module_row("E2E Módulo Editável")
        edit_link = row.find_element(
            *self._locator_by_testid("module-edit-link")
        )
        edit_link.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("module-form-page"))
        )
        description_input = self.browser.find_element(
            *self._locator_by_testid("module-description")
        )
        description_input.clear()
        description_input.send_keys("Descrição atualizada pelo smoke test")

        show_in_dashboard = self.browser.find_element(
            *self._locator_by_testid("module-show-in-dashboard")
        )
        if show_in_dashboard.is_selected():
            show_in_dashboard.click()
            self._pause_for_demo()

        show_in_sidebar = self.browser.find_element(
            *self._locator_by_testid("module-show-in-sidebar")
        )
        if show_in_sidebar.is_selected():
            show_in_sidebar.click()
            self._pause_for_demo()

        save_button = self.browser.find_element(
            *self._locator_by_testid("module-save-submit")
        )
        save_button.click()
        self._pause_for_demo()

        self.wait.until(
            EC.presence_of_element_located(self._locator_by_testid("modules-page"))
        )
        row = self._module_row("E2E Módulo Editável")
        self.wait.until(
            lambda browser: "Oculto" in self._module_row("E2E Módulo Editável").text
        )

        updated_module = Module.objects.get(slug="e2e-modulo-editavel")
        self.assertEqual(
            updated_module.description,
            "Descrição atualizada pelo smoke test",
        )
        self.assertFalse(updated_module.show_in_dashboard)
        self.assertFalse(updated_module.show_in_sidebar)
        self.assertIn("Oculto", row.text)
