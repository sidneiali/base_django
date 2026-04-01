"""Registros read-only do admin para auditoria."""

from django.contrib import admin

from ..models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Consulta read-only dos eventos de auditoria do sistema."""

    list_display = (
        "created_at",
        "action",
        "object_verbose_name",
        "object_repr",
        "actor_identifier_display",
        "request_id_display",
        "path",
    )
    list_filter = ("action", "content_type", "created_at")
    search_fields = (
        "object_repr",
        "object_id",
        "actor_identifier",
        "path",
    )
    readonly_fields = (
        "created_at",
        "action",
        "actor",
        "actor_identifier",
        "content_type",
        "object_id",
        "object_repr",
        "object_verbose_name",
        "request_method",
        "path",
        "ip_address",
        "before",
        "after",
        "changes",
        "metadata",
    )
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        """Impede inclusao manual de logs pelo admin."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impede alteracao manual dos eventos persistidos."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Impede exclusao manual dos eventos persistidos."""

        return False

    @admin.display(description="Ator")
    def actor_identifier_display(self, obj: AuditLog) -> str:
        """Mostra o usuario autenticado ou o identificador digitado."""

        if obj.actor:
            return obj.actor.get_username()
        return obj.actor_identifier or "-"

    @admin.display(description="Request ID")
    def request_id_display(self, obj: AuditLog) -> str:
        """Mostra o identificador da requisição que originou o evento."""

        return str(obj.metadata.get("request_id", "") or "-")
