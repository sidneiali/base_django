"""Models centrais usados para compor o dashboard, auditoria e acesso a API."""

import hashlib
import hmac
import secrets

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


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
    ACTION_API_ACCESS_DENIED = "api_access_denied"
    ACTION_RATE_LIMITED = "rate_limited"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Criação"),
        (ACTION_UPDATE, "Alteração"),
        (ACTION_DELETE, "Exclusão"),
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_LOGIN_FAILED, "Falha de login"),
        (ACTION_API_ACCESS_DENIED, "Acesso negado à API"),
        (ACTION_RATE_LIMITED, "Rate limit"),
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


class ApiAccessProfile(models.Model):
    """Controla se um usuario pode gerar e usar token para a API."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_access_profile",
    )
    api_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Acesso à API"
        verbose_name_plural = "Acessos à API"

    def __str__(self) -> str:
        """Resume o estado do acesso a API para uso administrativo."""

        status = "habilitada" if self.api_enabled else "desabilitada"
        return f"API {status} para {self.user}"


class ApiResourcePermission(models.Model):
    """Define quais operacoes CRUD o usuario pode executar por recurso."""

    class Resource(models.TextChoices):
        PANEL_USERS = "panel.users", "Usuários"
        CORE_API_ACCESS = "core.api_access", "Acesso à API"
        CORE_AUDIT_LOGS = "core.audit_logs", "Logs de auditoria"

    access_profile = models.ForeignKey(
        ApiAccessProfile,
        on_delete=models.CASCADE,
        related_name="resource_permissions",
    )
    resource = models.CharField(max_length=50, choices=Resource.choices)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Permissão de recurso da API"
        verbose_name_plural = "Permissões de recursos da API"
        ordering = ["access_profile__user__username", "resource"]
        constraints = [
            models.UniqueConstraint(
                fields=["access_profile", "resource"],
                name="core_unique_api_resource_permission",
            )
        ]

    def __str__(self) -> str:
        """Resume o recurso configurado para o usuario no admin."""

        return f"{self.access_profile.user} · {self.get_resource_display()}"

    def has_any_permission(self) -> bool:
        """Indica se ao menos uma operacao CRUD foi liberada."""

        return any(
            [
                self.can_create,
                self.can_read,
                self.can_update,
                self.can_delete,
            ]
        )

    def allows(self, action: str) -> bool:
        """Retorna se a acao CRUD informada foi liberada para o recurso."""

        permission_map = {
            "create": self.can_create,
            "read": self.can_read,
            "update": self.can_update,
            "delete": self.can_delete,
        }
        return permission_map.get(action, False)


class ApiToken(models.Model):
    """Armazena o token opaco do usuario apenas como hash persistido."""

    RAW_TOKEN_BYTES = 32
    PREFIX_LENGTH = 12

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_token",
    )
    token_prefix = models.CharField(max_length=PREFIX_LENGTH, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Token de API"
        verbose_name_plural = "Tokens de API"

    def __str__(self) -> str:
        """Retorna um identificador amigavel sem expor o segredo completo."""

        return f"Token {self.token_prefix}... de {self.user}"

    @property
    def is_active(self) -> bool:
        """Indica se o token ainda pode ser usado pela API."""

        return self.revoked_at is None

    @classmethod
    def generate_raw_token(cls) -> str:
        """Gera um token opaco adequado para autenticacao Bearer."""

        return secrets.token_urlsafe(cls.RAW_TOKEN_BYTES)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Calcula o hash persistido do token bruto informado."""

        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def issue_for_user(cls, user) -> tuple["ApiToken", str]:
        """Cria ou substitui o token ativo do usuario e retorna o valor bruto."""

        raw_token = cls.generate_raw_token()
        issued_at = timezone.now()
        token, _ = cls.objects.update_or_create(
            user=user,
            defaults={
                "token_prefix": raw_token[: cls.PREFIX_LENGTH],
                "token_hash": cls.hash_token(raw_token),
                "issued_at": issued_at,
                "last_used_at": None,
                "revoked_at": None,
            },
        )
        return token, raw_token

    def matches(self, raw_token: str) -> bool:
        """Compara um token bruto com o hash persistido de forma segura."""

        return hmac.compare_digest(self.token_hash, self.hash_token(raw_token))

    def mark_used(self) -> None:
        """Registra o instante do ultimo uso bem-sucedido do token."""

        timestamp = timezone.now()
        self.last_used_at = timestamp
        self.updated_at = timestamp
        type(self).objects.filter(pk=self.pk).update(
            last_used_at=timestamp,
            updated_at=timestamp,
        )

    def revoke(self) -> None:
        """Invalida o token atual sem apagar o historico do registro."""

        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])


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
