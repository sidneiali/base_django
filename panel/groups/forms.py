"""Formulário de grupos do painel."""

from typing import cast

from core.models import GroupInterfacePreference, UserInterfacePreference
from core.preferences import (
    get_group_interface_preference,
    save_group_interface_preference,
)
from django import forms
from django.contrib.auth.models import Group, Permission
from django.db.models import Model

from ..autonomy import (
    GROUP_SCOPE_BLOCK_REASON,
    filter_assignable_permissions_queryset,
    permissions_within_actor_scope,
)
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
    session_idle_timeout_minutes = forms.IntegerField(
        label="Sessão inativa do grupo (minutos)",
        required=False,
        min_value=UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES,
        max_value=UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": str(UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES),
                "max": str(UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES),
                "step": "5",
                "data-teste": "group-session-idle-timeout",
            }
        ),
        help_text=(
            "Opcional. Use um valor entre "
            f"{UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES} e "
            f"{UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES} minutos. "
            "Se o usuário também tiver valor próprio, vale o menor tempo configurado."
        ),
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "data-teste": "group-name",
                }
            ),
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

    def __init__(self, *args, acting_user=None, **kwargs):
        """Preenche a configuracao de sessao do grupo quando houver valor salvo."""

        self.acting_user = acting_user
        super().__init__(*args, **kwargs)
        permissions_field = cast(
            PermissionMultipleChoiceField,
            self.fields["permissions"],
        )
        permissions_field.queryset = filter_assignable_permissions_queryset(
            permissions_field.queryset,
            acting_user=self.acting_user,
        )
        if self.is_bound:
            return

        preference = self._get_group_preference()
        self.fields["session_idle_timeout_minutes"].initial = (
            preference.session_idle_timeout_minutes
        )

    def clean(self) -> dict[str, object]:
        """Impede que o grupo receba permissões acima do operador."""

        cleaned_data = super().clean() or {}
        permissions = cleaned_data.get("permissions")
        if permissions is not None and not permissions_within_actor_scope(
            permissions,
            acting_user=self.acting_user,
        ):
            self.add_error("permissions", GROUP_SCOPE_BLOCK_REASON)
        return cleaned_data

    def _get_group_preference(self) -> GroupInterfacePreference:
        """Retorna a preferencia persistida ou um objeto default em memoria."""

        return get_group_interface_preference(self.instance)

    def save(self, commit: bool = True) -> Group:
        """Salva o grupo e sua politica opcional de sessao inativa."""

        group = super().save(commit=commit)
        if commit:
            save_group_interface_preference(
                group,
                session_idle_timeout_minutes=self.cleaned_data[
                    "session_idle_timeout_minutes"
                ],
            )
        return group
