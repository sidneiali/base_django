"""Formularios relacionados a autenticacao e entrada no sistema."""

from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm


class LoginForm(AuthenticationForm):
    """Formulario de login com widgets alinhados ao visual do projeto."""

    def __init__(self, *args, **kwargs):
        """Aplica labels e atributos de exibicao aos campos padrao."""

        super().__init__(*args, **kwargs)

        self.fields["username"].label = "Usuário"
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Digite seu usuário",
                "autofocus": True,
                "spellcheck": "false",
            }
        )

        self.fields["password"].label = "Senha"
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Digite sua senha",
            }
        )


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
