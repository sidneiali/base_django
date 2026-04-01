"""Formulários usados pela conta autenticada."""

from django.contrib.auth.forms import PasswordChangeForm


class SelfPasswordChangeForm(PasswordChangeForm):
    """Formulario de troca de senha alinhado ao visual autenticado da base."""

    def __init__(self, *args, **kwargs):
        """Aplica labels, placeholders e classes Tabler aos campos padrao."""

        super().__init__(*args, **kwargs)

        field_map = {
            "old_password": (
                "Senha atual",
                "Digite sua senha atual",
                "current-password",
            ),
            "new_password1": (
                "Nova senha",
                "Digite a nova senha",
                "new-password",
            ),
            "new_password2": (
                "Confirmar nova senha",
                "Digite novamente a nova senha",
                "new-password",
            ),
        }

        for field_name, (label, placeholder, autocomplete) in field_map.items():
            field = self.fields[field_name]
            field.label = label
            field.widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": placeholder,
                    "autocomplete": autocomplete,
                }
            )
