"""Models centrais usados para compor o dashboard e a auditoria do sistema."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
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


class AuditLog(models.Model):
    """Registra eventos relevantes de auditoria do sistema."""

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_LOGIN_FAILED = "login_failed"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Criação"),
        (ACTION_UPDATE, "Alteração"),
        (ACTION_DELETE, "Exclusão"),
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_LOGIN_FAILED, "Falha de login"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_identifier = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    object_verbose_name = models.CharField(max_length=100, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Log de auditoria"
        verbose_name_plural = "Logs de auditoria"

    def __str__(self) -> str:
        """Resume o evento para listagens administrativas."""

        target = self.object_repr or self.object_verbose_name or "evento"
        return f"{self.get_action_display()} em {target}"


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
