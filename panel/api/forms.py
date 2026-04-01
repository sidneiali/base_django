"""Formulários de escrita usados pelos endpoints JSON do app panel."""

from django import forms
from django.contrib.auth.models import Group, Permission, User

from ..constants import BLOCKED_PERMISSION_APP_LABELS, PROTECTED_GROUP_NAMES
from ..modules.forms import PanelModuleForm


class ApiUserWriteForm(forms.ModelForm):
    """Valida payloads JSON de criação e edição de usuários comuns."""

    password = forms.CharField(required=False)
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.exclude(name__in=PROTECTED_GROUP_NAMES).order_by("name"),
        required=False,
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

    def __init__(self, *args, require_password: bool = False, **kwargs):
        """Permite exigir senha apenas na criação do usuário."""

        self.require_password = require_password
        super().__init__(*args, **kwargs)

    def clean(self):
        """Exige a senha quando o payload representa uma criação."""

        cleaned_data = super().clean()
        if self.require_password and not cleaned_data.get("password"):
            self.add_error("password", "A senha é obrigatória para novos usuários.")
        return cleaned_data

    def save(self, commit: bool = True) -> User:
        """Salva o usuário garantindo que ele continue fora da área staff."""

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

        return user


class ApiGroupWriteForm(forms.ModelForm):
    """Valida payloads JSON de criação e edição de grupos editáveis."""

    permissions = forms.ModelMultipleChoiceField(
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
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]

    def clean_name(self) -> str:
        """Impede o uso dos nomes reservados para grupos protegidos."""

        name = self.cleaned_data["name"].strip()
        if name in PROTECTED_GROUP_NAMES:
            raise forms.ValidationError("Esse grupo é protegido.")
        return name


class ApiModuleWriteForm(PanelModuleForm):
    """Reaproveita a validação de módulos para payloads JSON da API."""
