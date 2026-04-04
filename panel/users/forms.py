"""Formulário de usuários do painel."""

from typing import cast

from core.api.forms import ApiAccessFormMixin
from core.models import UserInterfacePreference
from core.preferences import (
    get_user_interface_preference,
    save_user_interface_preference,
)
from django import forms
from django.contrib.auth.models import Group, User
from django.db.models import QuerySet

from ..autonomy import (
    API_SCOPE_BLOCK_REASON,
    api_payload_within_actor_scope,
    filter_assignable_groups_queryset,
    limit_api_fields_to_actor_scope,
)
from ..constants import PROTECTED_GROUP_NAMES


class PanelUserForm(ApiAccessFormMixin, forms.ModelForm):
    """Formulario de criacao e edicao de usuarios nao administrativos."""

    password = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "data-teste": "user-password",
            },
            render_value=False,
        ),
        help_text="Preencha só se quiser trocar a senha de um usuário existente.",
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
                "data-teste": "user-auto-refresh-interval",
            }
        ),
        help_text=(
            "Use um valor entre "
            f"{UserInterfacePreference.MIN_AUTO_REFRESH_INTERVAL}s e "
            f"{UserInterfacePreference.MAX_AUTO_REFRESH_INTERVAL}s."
        ),
    )
    session_idle_timeout_minutes = forms.IntegerField(
        label="Sessão inativa (minutos)",
        required=False,
        min_value=UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES,
        max_value=UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": str(UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES),
                "max": str(UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES),
                "step": "5",
                "data-teste": "user-session-idle-timeout",
            }
        ),
        help_text=(
            "Opcional. Use um valor entre "
            f"{UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES} e "
            f"{UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES} minutos. "
            "Se houver regra em grupos, vale o menor tempo configurado."
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
            "username": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "user-username"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "user-first-name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "data-teste": "user-last-name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "data-teste": "user-email"}
            ),
        }
        labels = {
            "username": "Usuário",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "is_active": "Usuário ativo",
        }

    def __init__(self, *args, acting_user: User | None = None, **kwargs):
        """Preenche os campos extras com as preferencias atuais do usuario."""

        self.acting_user = acting_user
        super().__init__(*args, **kwargs)
        self.fields["auto_refresh_enabled"].widget.attrs.update(
            {
                "class": "form-check-input",
                "data-teste": "user-auto-refresh-enabled",
            }
        )
        self.fields["is_active"].widget.attrs.update(
            {
                "class": "form-check-input",
                "data-teste": "user-is-active",
            }
        )
        self.fields["api_enabled"].widget.attrs.update(
            {"class": "form-check-input"}
        )
        for row in self.get_api_permission_rows():
            for cell in cast(list[dict[str, object]], row["fields"]):
                bound_field = cast(forms.BoundField, cell["field"])
                bound_field.field.widget.attrs.update(
                    {"class": "form-check-input"}
                )

        groups_field = cast(forms.ModelMultipleChoiceField, self.fields["groups"])
        groups_queryset = cast(QuerySet[Group], groups_field.queryset)
        groups_field.queryset = filter_assignable_groups_queryset(
            groups_queryset.prefetch_related("permissions"),
            acting_user=self.acting_user,
        )
        limit_api_fields_to_actor_scope(
            self.fields,
            acting_user=self.acting_user,
        )

        if not self.instance.pk:
            self.fields["email"].required = True
            self.fields["email"].help_text = (
                "Obrigatório. O usuário receberá neste e-mail o link para definir "
                "a senha do primeiro acesso."
            )

        if self.is_bound:
            return

        preference = self._get_ui_preference()
        self.fields["auto_refresh_enabled"].initial = preference.auto_refresh_enabled
        self.fields["auto_refresh_interval"].initial = preference.auto_refresh_interval
        self.fields["session_idle_timeout_minutes"].initial = (
            preference.session_idle_timeout_minutes
        )

    def clean(self) -> dict[str, object]:
        """Exige e-mail na criação e permite troca opcional de senha na edição."""

        cleaned_data = super().clean() or {}
        email = str(cleaned_data.get("email", "") or "").strip()

        if not self.instance.pk and not email:
            self.add_error(
                "email",
                "O e-mail é obrigatório para enviar o convite de primeiro acesso.",
            )

        if not api_payload_within_actor_scope(
            self.build_api_access_payload(),
            acting_user=self.acting_user,
        ):
            self.add_error(None, API_SCOPE_BLOCK_REASON)

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
        if user.pk and password:
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
                session_idle_timeout_minutes=self.cleaned_data[
                    "session_idle_timeout_minutes"
                ],
            )
            self.save_api_access_settings(user)

        return user
