"""Formulário de grupos do painel."""

from typing import cast

from django import forms
from django.contrib.auth.models import Group, Permission
from django.db.models import Model

from ..constants import (
    APP_LABEL_TRANSLATIONS,
    BLOCKED_PERMISSION_APP_LABELS,
    PROTECTED_GROUP_NAMES,
)

MODEL_NAME_TRANSLATIONS = {
    "group": "Grupo",
    "user": "Usuário",
    "permission": "Permissão",
    "module": "Módulo",
}


def traduz_permissao(name: str) -> str:
    """Traduz descricoes padrao de permissoes do Django para pt-BR."""

    text = (
        name.replace("Can add", "Pode adicionar")
        .replace("Can change", "Pode alterar")
        .replace("Can delete", "Pode excluir")
        .replace("Can view", "Pode visualizar")
    )

    for source, target in MODEL_NAME_TRANSLATIONS.items():
        text = text.replace(source, target.lower())

    return text


def traduz_app_label(app_label: str) -> str:
    """Converte o ``app_label`` para um nome amigavel de exibicao."""

    return APP_LABEL_TRANSLATIONS.get(
        app_label,
        app_label.replace("_", " ").strip().capitalize(),
    )


def traduz_model_name(model_name: str) -> str:
    """Converte o nome tecnico do model para um rotulo amigavel."""

    normalized = model_name.replace("_", " ").strip().lower()
    return MODEL_NAME_TRANSLATIONS.get(normalized, normalized.capitalize())


class PermissionMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Campo multipla escolha que exibe permissoes com label traduzida."""

    def label_from_instance(self, obj: Model) -> str:
        """Monta um label com app, model e permissao em formato legivel."""

        permission = cast(Permission, obj)
        app_name = traduz_app_label(permission.content_type.app_label)
        model_name = traduz_model_name(permission.content_type.model)
        permission_name = traduz_permissao(permission.name)
        return f"{app_name} | {model_name} | {permission_name}"


class PanelGroupForm(forms.ModelForm):
    """Formulario para criacao e edicao de grupos com filtro de permissoes."""

    permissions = PermissionMultipleChoiceField(
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
        label="Permissões",
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
                "size": "15",
                "id": "id_permissions",
            },
        ),
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Nome do grupo",
        }

    def clean_name(self) -> str:
        """Impede o uso de nomes reservados para grupos protegidos."""

        name = self.cleaned_data["name"].strip()
        if name in PROTECTED_GROUP_NAMES:
            raise forms.ValidationError("Esse grupo é protegido.")
        return name
