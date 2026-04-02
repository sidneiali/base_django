"""Formulário de módulos do painel."""

from __future__ import annotations

from typing import cast

from core.models import Module
from django import forms
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.urls import NoReverseMatch, reverse

from ..constants import BLOCKED_PERMISSION_APP_LABELS
from ..groups.forms import traduz_app_label, traduz_model_name, traduz_permissao


class PermissionChoiceField(forms.ModelChoiceField):
    """Campo de permissão única com label amigável."""

    def label_from_instance(self, obj: Model) -> str:
        """Monta um label legível com app, model e permissão."""

        permission = cast(Permission, obj)
        app_name = traduz_app_label(permission.content_type.app_label)
        model_name = traduz_model_name(permission.content_type.model)
        permission_name = traduz_permissao(permission.name)
        return f"{app_name} | {model_name} | {permission_name}"


class PanelModuleForm(forms.ModelForm):
    """Formulário do painel para criação e edição de módulos do dashboard."""

    permission = PermissionChoiceField(
        queryset=Permission.objects.exclude(
            content_type__app_label__in=BLOCKED_PERMISSION_APP_LABELS
        )
        .select_related("content_type")
        .order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
        required=False,
        label="Permissão exigida",
        help_text="Deixe em branco para liberar o módulo a qualquer usuário autenticado.",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "data-teste": "module-permission",
            }
        ),
    )

    class Meta:
        model = Module
        fields = [
            "name",
            "slug",
            "description",
            "icon",
            "url_name",
            "menu_group",
            "order",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "module-name"}
            ),
            "slug": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "module-slug"}
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "module-description"}
            ),
            "icon": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "module-icon"}
            ),
            "url_name": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "module-url-name"}
            ),
            "menu_group": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "module-menu-group"}
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "data-teste": "module-order",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "data-teste": "module-is-active",
                }
            ),
        }
        labels = {
            "name": "Nome do módulo",
            "slug": "Slug",
            "description": "Descrição",
            "icon": "Ícone",
            "url_name": "Nome da rota",
            "menu_group": "Grupo do menu",
            "order": "Ordem",
            "is_active": "Módulo ativo",
        }
        help_texts = {
            "icon": "Use classes do Tabler, como `ti ti-layout-grid` ou `ti ti-users`.",
            "url_name": (
                "Informe uma rota sem argumentos obrigatórios, como "
                "`panel_users_list`, `panel_audit_logs_list`, `api_docs` ou "
                "`module_entry` para a entrada genérica por slug."
            ),
            "menu_group": "Define em qual grupo o módulo aparece no dashboard e no sidebar.",
        }

    def __init__(self, *args, **kwargs):
        """Preenche o seletor de permissão com o valor atual do módulo."""

        super().__init__(*args, **kwargs)

        if not self.instance.pk or not self.instance.full_permission:
            return

        permission = Permission.objects.filter(
            content_type__app_label=self.instance.app_label,
            codename=self.instance.permission_codename,
        ).first()
        if permission is not None:
            self.fields["permission"].initial = permission

    def clean_url_name(self) -> str:
        """Valida se a rota configurada pode ser resolvida pelo módulo."""

        url_name = self.cleaned_data["url_name"].strip()
        if not url_name:
            raise ValidationError("Informe o nome da rota do módulo.")

        if url_name == "module_entry":
            return url_name

        try:
            reverse(url_name)
        except NoReverseMatch as exc:
            raise ValidationError(
                "Informe um nome de rota válido sem argumentos obrigatórios.",
            ) from exc

        return url_name

    def save(self, commit: bool = True) -> Module:
        """Salva o módulo refletindo a permissão escolhida no model."""

        module = super().save(commit=False)
        permission = cast(Permission | None, self.cleaned_data.get("permission"))

        if permission is None:
            module.app_label = ""
            module.permission_codename = ""
        else:
            module.app_label = permission.content_type.app_label
            module.permission_codename = permission.codename

        if commit:
            module.save()

        return module
