"""Models centrais usados para compor o dashboard por modulos."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class UserInterfacePreference(models.Model):
    """Armazena preferencias de interface usadas no shell autenticado.

    No momento o model controla o auto refresh global do conteudo principal,
    permitindo habilitar ou desabilitar a atualizacao automatica e definir o
    intervalo em segundos dentro de uma faixa segura para a aplicacao.
    """

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


class Module(models.Model):
    """Representa uma area funcional exibida no dashboard.

    Cada modulo pode apontar para uma rota nomeada do Django e,
    opcionalmente, exigir uma permissao especifica para liberacao
    de acesso ao usuario autenticado.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=100, blank=True)
    url_name = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100, blank=True)
    permission_codename = models.CharField(max_length=100, blank=True)
    menu_group = models.CharField(max_length=100, default="Geral")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["menu_group", "order", "name"]

    def __str__(self) -> str:
        """Retorna o nome usado em telas administrativas e logs."""

        return self.name

    @property
    def full_permission(self) -> str:
        """Monta a permissao completa no formato ``app_label.codename``."""

        if not self.app_label or not self.permission_codename:
            return ""
        return f"{self.app_label}.{self.permission_codename}"

    def get_absolute_url(self) -> str:
        """Resolve a URL nomeada configurada para o modulo."""

        return reverse(self.url_name)
