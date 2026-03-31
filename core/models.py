"""Models centrais usados para compor o dashboard por modulos."""

from django.db import models
from django.urls import reverse


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
