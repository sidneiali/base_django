"""Formulários da superfície de contas administrativas do painel."""

from __future__ import annotations

from typing import cast

from core.api.forms import ApiAccessFormMixin
from core.models import UserInterfacePreference
from core.preferences import (
    get_user_interface_preference,
    save_user_interface_preference,
)
from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.db.models import QuerySet

from ..autonomy import (
    API_SCOPE_BLOCK_REASON,
    DIRECT_PERMISSION_SCOPE_BLOCK_REASON,
    GROUP_SCOPE_BLOCK_REASON,
    api_payload_within_actor_scope,
    filter_assignable_groups_queryset,
    filter_assignable_permissions_queryset,
    groups_within_actor_scope,
    limit_api_fields_to_actor_scope,
    permissions_within_actor_scope,
)
from ..groups.forms import PermissionMultipleChoiceField
from .services import get_admin_account_transition_block_reason


class PanelAdminAccountForm(ApiAccessFormMixin, forms.ModelForm):
    """Formulário para criar e editar contas administrativas via painel."""

    password = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "data-teste": "admin-account-password",
            },
            render_value=False,
        ),
        help_text="Preencha só se quiser trocar a senha de uma conta já existente.",
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        label="Grupos",
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
                "size": "10",
            }
        ),
    )
    user_permissions = PermissionMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
        required=False,
        label="Permissões diretas",
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
                "size": "14",
            }
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
                "data-teste": "admin-account-auto-refresh-interval",
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
                "data-teste": "admin-account-session-idle-timeout",
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
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "data-teste": "admin-account-username",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "data-teste": "admin-account-first-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "data-teste": "admin-account-last-name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "data-teste": "admin-account-email",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "data-teste": "admin-account-is-active",
                }
            ),
            "is_staff": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "data-teste": "admin-account-is-staff",
                }
            ),
            "is_superuser": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "data-teste": "admin-account-is-superuser",
                }
            ),
        }
        labels = {
            "username": "Usuário",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "is_active": "Conta ativa",
            "is_staff": "Conta staff",
            "is_superuser": "Conta superusuária",
        }

    def __init__(self, *args, acting_user: User | None = None, **kwargs):
        """Preenche preferências atuais e guarda quem está operando a tela."""

        self.acting_user = acting_user
        super().__init__(*args, **kwargs)

        self.fields["auto_refresh_enabled"].widget.attrs.update(
            {
                "class": "form-check-input",
                "data-teste": "admin-account-auto-refresh-enabled",
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
        permissions_field = cast(
            PermissionMultipleChoiceField,
            self.fields["user_permissions"],
        )
        permissions_queryset = cast(QuerySet[Permission], permissions_field.queryset)
        permissions_field.queryset = filter_assignable_permissions_queryset(
            permissions_queryset,
            acting_user=self.acting_user,
        )
        limit_api_fields_to_actor_scope(
            self.fields,
            acting_user=self.acting_user,
        )

        if not self.instance.pk:
            self.fields["email"].required = True
            self.fields["email"].help_text = (
                "Obrigatório. A conta receberá neste e-mail o link para definir "
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

    def _get_ui_preference(self) -> UserInterfacePreference:
        """Retorna a preferência persistida ou um default em memória."""

        return get_user_interface_preference(self.instance)

    def clean(self) -> dict[str, object]:
        """Valida e protege a transição de uma conta administrativa."""

        cleaned_data = super().clean() or {}
        email = str(cleaned_data.get("email", "") or "").strip()
        is_active = bool(cleaned_data.get("is_active"))
        is_staff = bool(cleaned_data.get("is_staff"))
        is_superuser = bool(cleaned_data.get("is_superuser"))

        if not self.instance.pk and not email:
            self.add_error(
                "email",
                "O e-mail é obrigatório para enviar o convite de primeiro acesso.",
            )

        if is_superuser:
            cleaned_data["is_staff"] = True
            is_staff = True

        block_reason = get_admin_account_transition_block_reason(
            self.instance,
            acting_user=self.acting_user,
            next_is_active=is_active,
            next_is_staff=is_staff,
            next_is_superuser=is_superuser,
        )
        if block_reason:
            self.add_error(None, block_reason)

        groups = cleaned_data.get("groups")
        if groups is not None and not groups_within_actor_scope(
            groups,
            acting_user=self.acting_user,
        ):
            self.add_error("groups", GROUP_SCOPE_BLOCK_REASON)

        user_permissions = cleaned_data.get("user_permissions")
        if user_permissions is not None and not permissions_within_actor_scope(
            user_permissions,
            acting_user=self.acting_user,
        ):
            self.add_error(
                "user_permissions",
                DIRECT_PERMISSION_SCOPE_BLOCK_REASON,
            )

        if not api_payload_within_actor_scope(
            self.build_api_access_payload(),
            acting_user=self.acting_user,
        ):
            self.add_error(None, API_SCOPE_BLOCK_REASON)

        return cleaned_data

    def save(self, commit: bool = True) -> User:
        """Salva a conta administrativa com preferências e acesso à API."""

        user = super().save(commit=False)
        if self.cleaned_data.get("is_superuser"):
            user.is_staff = True

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
