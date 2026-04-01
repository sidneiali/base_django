"""Models relacionados à interface autenticada."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserInterfacePreference(models.Model):
    """Armazena preferencias de interface usadas no shell autenticado."""

    DEFAULT_AUTO_REFRESH_ENABLED = True
    DEFAULT_AUTO_REFRESH_INTERVAL = 30
    MIN_AUTO_REFRESH_INTERVAL = 30
    MAX_AUTO_REFRESH_INTERVAL = 120

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
