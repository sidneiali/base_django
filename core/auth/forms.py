"""Formulários do fluxo público de autenticação."""

from django.conf import settings
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)

from .services import queue_password_recovery_email


class LoginForm(AuthenticationForm):
    """Formulario de login por e-mail com widgets alinhados ao projeto."""

    error_messages = {
        "invalid_login": (
            "Por favor, entre com um e-mail e senha corretos. "
            "Note que ambos diferenciam maiúsculas de minúsculas."
        ),
        "inactive": "Esta conta está inativa.",
    }

    def __init__(self, *args, **kwargs):
        """Aplica labels e atributos de exibicao aos campos padrao."""

        super().__init__(*args, **kwargs)

        self.fields["username"].label = "E-mail"
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Digite seu e-mail",
                "autofocus": True,
                "spellcheck": "false",
                "autocomplete": "email",
                "inputmode": "email",
                "data-teste": "login-username",
            }
        )

        self.fields["password"].label = "Senha"
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Digite sua senha",
                "data-teste": "login-password",
            }
        )


class PasswordRecoveryForm(PasswordResetForm):
    """Formulario publico para solicitar o e-mail de recuperacao de senha."""

    def __init__(self, *args, **kwargs):
        """Aplica o visual da pagina externa aos campos do reset."""

        super().__init__(*args, **kwargs)
        self.fields["email"].label = "E-mail"
        self.fields["email"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Digite seu e-mail",
                "autocomplete": "email",
            }
        )

    def save(
        self,
        domain_override=None,
        subject_template_name="registration/password_reset_subject.txt",
        email_template_name="registration/password_reset_email.html",
        use_https=False,
        token_generator=None,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """Enfileira a recuperação de senha sem bloquear a resposta HTTP."""

        del subject_template_name
        del email_template_name
        del token_generator
        del html_email_template_name
        del extra_email_context

        if request is None and not domain_override:
            raise ValueError(
                "PasswordRecoveryForm.save() precisa de request ou domain_override."
            )

        protocol = "https" if use_https or (request and request.is_secure()) else "http"
        domain = domain_override or request.get_host()

        for user in self.get_users(self.cleaned_data["email"]):
            queue_password_recovery_email(
                user=user,
                protocol=protocol,
                domain=domain,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            )


class PasswordRecoveryConfirmForm(SetPasswordForm):
    """Formulario publico para definir uma nova senha a partir do token."""

    def __init__(self, *args, **kwargs):
        """Aplica labels e classes do fluxo externo aos campos do reset."""

        super().__init__(*args, **kwargs)

        field_map = {
            "new_password1": (
                "Nova senha",
                "Digite a nova senha",
            ),
            "new_password2": (
                "Confirmar nova senha",
                "Digite novamente a nova senha",
            ),
        }

        for field_name, (label, placeholder) in field_map.items():
            field = self.fields[field_name]
            field.label = label
            field.widget.attrs.update(
                {
                    "class": "form-control form-control-lg",
                    "placeholder": placeholder,
                    "autocomplete": "new-password",
                }
            )
