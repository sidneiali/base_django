"""Formularios e traducoes auxiliares do painel administrativo."""

from typing import cast

from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.db.models import Model

from core.models import UserInterfacePreference
from core.preferences import (get_user_interface_preference,
                              save_user_interface_preference)
from .constants import (APP_LABEL_TRANSLATIONS, BLOCKED_PERMISSION_APP_LABELS,
                        PROTECTED_GROUP_NAMES)

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


class PanelUserForm(forms.ModelForm):
    """Formulario de criacao e edicao de usuarios nao administrativos."""

    password = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control"},
            render_value=False,
        ),
        help_text="Preencha só se quiser trocar a senha. Na criação, obrigatório.",
    )

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.exclude(
            name__in=PROTECTED_GROUP_NAMES).order_by("name"),
        required=False,
        label="Grupos",
        widget=forms.SelectMultiple(
            attrs={"class": "form-select", "size": "10"},
        ),
    )
    auto_refresh_enabled = forms.BooleanField(
        required=False,
        label="Atualização automática habilitada",
        widget=forms.CheckboxInput(
            attrs={"data-auto-refresh-toggle": "true"}
        ),
    )
    auto_refresh_interval = forms.IntegerField(
        label="Intervalo de atualização (segundos)",
        min_value=UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL,
        max_value=UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": str(UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL),
                "max": str(UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL),
                "step": "5",
                "data-auto-refresh-interval-input": "true",
            }
        ),
        help_text=(
            "Use um valor entre "
            f"{UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL}s e "
            f"{UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL}s."
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "groups",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
        labels = {
            "username": "Usuário",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "is_active": "Usuário ativo",
        }

    def __init__(self, *args, **kwargs):
        """Preenche os campos extras com as preferencias atuais do usuario."""

        super().__init__(*args, **kwargs)
        self.fields["auto_refresh_enabled"].widget.attrs.update(
            {"class": "form-check-input"}
        )

        if self.is_bound:
            return

        preference = self._get_ui_preference()
        self.fields["auto_refresh_enabled"].initial = preference.auto_refresh_enabled
        self.fields["auto_refresh_interval"].initial = preference.auto_refresh_interval

    def clean(self) -> dict:
        """Exige senha na criacao e permite troca opcional na edicao."""

        cleaned_data = super().clean()
        password = cleaned_data.get("password")

        if not self.instance.pk and not password:
            self.add_error(
                "password", "A senha é obrigatória para novos usuários.")

        return cleaned_data

    def _get_ui_preference(self) -> UserInterfacePreference:
        """Retorna a preferencia persistida ou um objeto default em memoria."""

        return cast(UserInterfacePreference, get_user_interface_preference(self.instance))

    def save(self, commit: bool = True) -> User:
        """Salva o usuario garantindo que ele nao vire staff ou superuser."""

        user = super().save(commit=False)
        user.is_superuser = False
        user.is_staff = False

        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()

        if commit:
            user.save()
            self.save_m2m()
            save_user_interface_preference(
                user,
                auto_refresh_enabled=self.cleaned_data["auto_refresh_enabled"],
                auto_refresh_interval=self.cleaned_data["auto_refresh_interval"],
            )

        return user


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
