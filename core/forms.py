"""Fachada compatível para os formulários do app core."""

from .account.forms import SelfPasswordChangeForm
from .auth.forms import LoginForm, PasswordRecoveryConfirmForm, PasswordRecoveryForm

__all__ = [
    "LoginForm",
    "PasswordRecoveryConfirmForm",
    "PasswordRecoveryForm",
    "SelfPasswordChangeForm",
]
