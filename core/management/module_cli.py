"""Utilitarios compartilhados pelos comandos interativos de modulos."""

from __future__ import annotations

from typing import Callable

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.urls import NoReverseMatch, reverse
from panel.modules.forms import PanelModuleForm

from core.models import Module
from core.module_catalog import INITIAL_MODULES, ModuleSeedDefinition


class ModuleCommandPrompts:
    """Centraliza perguntas interativas e validacao dos comandos de modulo."""

    def __init__(self, command: BaseCommand) -> None:
        self.command = command

    def prompt_new_slug(self) -> str:
        """Pede um slug novo e bloqueia conflito com modulo existente."""

        while True:
            slug = self.prompt_text("Slug do novo modulo", required=True)
            if not Module.objects.filter(slug=slug).exists():
                return slug
            self.command.stdout.write(
                "Esse slug ja existe. Use edit_module para atualizar um modulo existente."
            )

    def prompt_existing_module(self, *, slug: str | None = None) -> Module:
        """Resolve um modulo existente por slug, via argumento ou prompt."""

        if slug is None:
            self.write_existing_modules()

        while True:
            current_slug = slug or self.prompt_text(
                "Slug ou numero do modulo existente",
                required=True,
            )
            instance = self._resolve_existing_module_selection(current_slug)
            if instance is not None:
                return instance
            if slug is not None:
                raise CommandError(
                    f"Nenhum modulo encontrado com slug '{current_slug}'."
                )
            self.command.stdout.write(
                "Modulo nao encontrado. Informe um slug existente ou um numero valido."
            )

    def write_existing_modules(self) -> None:
        """Mostra os modulos atuais em formato curto para ajudar na escolha."""

        modules = list(
            Module.objects.order_by("menu_group", "order", "name").only(
                "name",
                "slug",
                "menu_group",
            )
        )
        if not modules:
            raise CommandError("Nenhum modulo cadastrado no momento.")

        self.command.stdout.write("Modulos existentes:")
        for index, module in enumerate(modules, start=1):
            self.command.stdout.write(
                f"{index}. {module.name} ({module.slug}) - {module.menu_group}"
            )
        self.command.stdout.write("")

    def write_canonical_modules(self) -> None:
        """Mostra os modulos canonicos definidos no projeto."""

        self.command.stdout.write("Modulos canonicos:")
        for index, definition in enumerate(INITIAL_MODULES, start=1):
            self.command.stdout.write(
                f"{index}. {definition.name} ({definition.slug}) - {definition.menu_group}"
            )
        self.command.stdout.write("")

    def build_form(
        self,
        *,
        instance: Module | None = None,
        slug: str | None = None,
        lock_slug: bool = False,
    ) -> PanelModuleForm:
        """Monta um ``PanelModuleForm`` com respostas coletadas no terminal."""

        current_slug = slug or (instance.slug if instance else "")
        form_slug = current_slug
        if not lock_slug:
            form_slug = self.prompt_text(
                "Slug do modulo",
                default=current_slug,
                required=True,
            )

        name = self.prompt_text(
            "Nome exibido",
            default=instance.name if instance else "",
            required=True,
        )
        description = self.prompt_text(
            "Descricao",
            default=instance.description if instance else "",
        )
        icon = self.prompt_text(
            "Icone Tabler",
            default=instance.icon if instance else "ti ti-layout-grid",
            required=True,
        )
        url_name = self.prompt_text(
            "Nome da rota Django",
            default=instance.url_name if instance else "module_entry",
            required=True,
            validator=self.validate_url_name,
        )
        menu_group = self.prompt_text(
            "Grupo do menu",
            default=instance.menu_group if instance else "Geral",
            required=True,
        )
        order = self.prompt_int(
            "Ordem dentro do grupo",
            default=instance.order if instance else 0,
            minimum=0,
        )
        show_in_dashboard = self.prompt_bool(
            "Exibir no dashboard?",
            default=instance.show_in_dashboard if instance else True,
        )
        show_in_sidebar = self.prompt_bool(
            "Exibir no sidebar?",
            default=instance.show_in_sidebar if instance else True,
        )
        is_active = self.prompt_bool(
            "Modulo ativo?",
            default=instance.is_active if instance else True,
        )
        permission = self.prompt_permission(
            default=instance.full_permission if instance else ""
        )

        return PanelModuleForm(
            data={
                "name": name,
                "slug": form_slug,
                "description": description,
                "icon": icon,
                "url_name": url_name,
                "menu_group": menu_group,
                "order": order,
                "is_active": is_active,
                "show_in_dashboard": show_in_dashboard,
                "show_in_sidebar": show_in_sidebar,
                "permission": str(permission.pk) if permission else "",
            },
            instance=instance,
        )

    def prompt_text(
        self,
        label: str,
        *,
        default: str = "",
        required: bool = False,
        validator: Callable[[str], None] | None = None,
    ) -> str:
        """Le um texto do terminal, com suporte a default e validacao."""

        while True:
            suffix = f" [{default}]" if default else ""
            value = input(f"{label}{suffix}: ").strip()
            if not value:
                value = default
            if required and not value:
                self.command.stdout.write("Esse campo e obrigatorio.")
                continue
            if validator is not None:
                try:
                    validator(value)
                except CommandError as exc:
                    self.command.stdout.write(str(exc))
                    continue
            return value

    def prompt_bool(self, label: str, *, default: bool) -> bool:
        """Pergunta uma escolha booleana simples em portugues."""

        hint = "S/n" if default else "s/N"
        while True:
            raw_value = input(f"{label} [{hint}]: ").strip().lower()
            if not raw_value:
                return default
            if raw_value in {"s", "sim", "y", "yes"}:
                return True
            if raw_value in {"n", "nao", "não", "no"}:
                return False
            self.command.stdout.write("Responda com 's' ou 'n'.")

    def prompt_int(self, label: str, *, default: int, minimum: int = 0) -> int:
        """Le um inteiro nao negativo com fallback previsivel."""

        while True:
            raw_value = input(f"{label} [{default}]: ").strip()
            if not raw_value:
                return default
            try:
                value = int(raw_value)
            except ValueError:
                self.command.stdout.write("Informe um numero inteiro valido.")
                continue
            if value < minimum:
                self.command.stdout.write(
                    f"Informe um valor maior ou igual a {minimum}."
                )
                continue
            return value

    def prompt_permission(self, *, default: str = "") -> Permission | None:
        """Pergunta a permissao no formato ``app_label.codename``."""

        while True:
            value = self.prompt_text(
                "Permissao exigida (app_label.codename ou vazio)",
                default=default,
            )
            if not value:
                return None
            try:
                app_label, codename = value.split(".", 1)
            except ValueError:
                self.command.stdout.write(
                    "Use o formato app_label.codename ou deixe em branco."
                )
                continue

            permission = Permission.objects.select_related("content_type").filter(
                content_type__app_label=app_label,
                codename=codename,
            ).first()
            if permission is None:
                self.command.stdout.write("Permissao nao encontrada. Tente de novo.")
                continue
            return permission

    def validate_url_name(self, value: str) -> None:
        """Valida a rota informada no mesmo contrato aceito pelo formulario."""

        if not value:
            raise CommandError("Informe o nome da rota do modulo.")
        if value == "module_entry":
            return
        try:
            reverse(value)
        except NoReverseMatch as exc:
            raise CommandError(
                "Informe um nome de rota valido sem argumentos obrigatorios."
            ) from exc

    def format_form_errors(self, form: PanelModuleForm) -> str:
        """Compacta os erros do formulario para feedback no terminal."""

        parts: list[str] = []
        for field_name, errors in form.errors.items():
            joined = "; ".join(str(error) for error in errors)
            parts.append(f"{field_name}: {joined}")
        return "Erros ao salvar o modulo: " + " | ".join(parts)

    def _resolve_existing_module_selection(self, value: str) -> Module | None:
        """Resolve um modulo por slug ou pelo numero exibido na lista."""

        if value.isdigit():
            modules = list(Module.objects.order_by("menu_group", "order", "name"))
            index = int(value) - 1
            if 0 <= index < len(modules):
                return modules[index]
            return None
        return Module.objects.filter(slug=value).first()

    def format_canonical_module(self, definition: ModuleSeedDefinition) -> str:
        """Resume um modulo canonico em uma unica linha legivel."""

        return (
            f"{definition.name} ({definition.slug}) - "
            f"{definition.menu_group} - {definition.url_name}"
        )
