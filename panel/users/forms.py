"""Formulário de usuários do painel."""

from core.api.forms import ApiAccessFormMixin
from core.models import UserInterfacePreference
from core.preferences import (
    get_user_interface_preference,
    save_user_interface_preference,
)
from django import forms
from django.contrib.auth.models import Group, User

from ..constants import PROTECTED_GROUP_NAMES


class PanelUserForm(ApiAccessFormMixin, forms.ModelForm):
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
        self.fields["api_enabled"].widget.attrs.update(
            {"class": "form-check-input"}
        )
        for row in self.get_api_permission_rows():
            for cell in row["fields"]:
                cell["field"].field.widget.attrs.update(
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

        return get_user_interface_preference(self.instance)

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
            self.save_api_access_settings(user)

        return user
