"""Models relacionados à interface autenticada."""

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserInterfacePreference(models.Model):
    """Armazena preferencias de interface usadas no shell autenticado."""

    DEFAULT_AUTO_REFRESH_ENABLED = True
    DEFAULT_AUTO_REFRESH_INTERVAL = 30
    MIN_AUTO_REFRESH_INTERVAL = 30
    MAX_AUTO_REFRESH_INTERVAL = 120
    MIN_SESSION_IDLE_TIMEOUT_MINUTES = 5
    MAX_SESSION_IDLE_TIMEOUT_MINUTES = 1440

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ui_preferences",
    )
    auto_refresh_enabled = models.BooleanField(
        default=DEFAULT_AUTO_REFRESH_ENABLED,
    )
    auto_refresh_interval = models.PositiveSmallIntegerField(
        default=DEFAULT_AUTO_REFRESH_INTERVAL,
        validators=[
            MinValueValidator(MIN_AUTO_REFRESH_INTERVAL),
            MaxValueValidator(MAX_AUTO_REFRESH_INTERVAL),
        ],
    )
    session_idle_timeout_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MIN_SESSION_IDLE_TIMEOUT_MINUTES),
            MaxValueValidator(MAX_SESSION_IDLE_TIMEOUT_MINUTES),
        ],
        help_text=(
            "Define o tempo maximo de inatividade da sessao, em minutos. "
            "Deixe em branco para nao aplicar regra propria neste usuario."
        ),
    )

    class Meta:
        verbose_name = "Preferência de interface"
        verbose_name_plural = "Preferências de interface"

    def __str__(self) -> str:
        """Retorna um identificador amigavel para uso administrativo."""

        return f"Preferências de {self.user}"

    def clean(self) -> None:
        """Valida o intervalo permitido para auto refresh."""

        super().clean()
        if not (
            self.MIN_AUTO_REFRESH_INTERVAL
            <= self.auto_refresh_interval
            <= self.MAX_AUTO_REFRESH_INTERVAL
        ):
            raise ValidationError(
                {
                    "auto_refresh_interval": (
                        "O intervalo deve ficar entre "
                        f"{self.MIN_AUTO_REFRESH_INTERVAL} e "
                        f"{self.MAX_AUTO_REFRESH_INTERVAL} segundos."
                    )
                }
            )
        if self.session_idle_timeout_minutes is None:
            return
        if not (
            self.MIN_SESSION_IDLE_TIMEOUT_MINUTES
            <= self.session_idle_timeout_minutes
            <= self.MAX_SESSION_IDLE_TIMEOUT_MINUTES
        ):
            raise ValidationError(
                {
                    "session_idle_timeout_minutes": (
                        "A duracao da sessao inativa deve ficar entre "
                        f"{self.MIN_SESSION_IDLE_TIMEOUT_MINUTES} e "
                        f"{self.MAX_SESSION_IDLE_TIMEOUT_MINUTES} minutos."
                    )
                }
            )


class GroupInterfacePreference(models.Model):
    """Armazena preferencias globais de sessao aplicadas aos grupos."""

    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="ui_preferences",
    )
    session_idle_timeout_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES),
            MaxValueValidator(UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES),
        ],
        help_text=(
            "Define o tempo maximo de inatividade da sessao para membros do grupo, "
            "em minutos. Deixe em branco para nao aplicar regra neste grupo."
        ),
    )

    class Meta:
        verbose_name = "Preferência de grupo"
        verbose_name_plural = "Preferências de grupos"

    def __str__(self) -> str:
        """Retorna um identificador amigavel para uso administrativo."""

        return f"Preferências do grupo {self.group}"

    def clean(self) -> None:
        """Valida a janela de sessao inativa permitida para o grupo."""

        super().clean()
        if self.session_idle_timeout_minutes is None:
            return
        if not (
            UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES
            <= self.session_idle_timeout_minutes
            <= UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES
        ):
            raise ValidationError(
                {
                    "session_idle_timeout_minutes": (
                        "A duracao da sessao inativa deve ficar entre "
                        f"{UserInterfacePreference.MIN_SESSION_IDLE_TIMEOUT_MINUTES} e "
                        f"{UserInterfacePreference.MAX_SESSION_IDLE_TIMEOUT_MINUTES} minutos."
                    )
                }
            )
