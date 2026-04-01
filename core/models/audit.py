"""Models relacionados à trilha de auditoria."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


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
