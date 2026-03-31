"""Formularios relacionados a autenticacao e entrada no sistema."""

from django.contrib.auth.forms import AuthenticationForm


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
