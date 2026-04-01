"""Models de acesso e autenticação da API."""

import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


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
