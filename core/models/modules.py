"""Models relacionados aos módulos visíveis no shell autenticado."""

from django.db import models
from django.urls import reverse

from core.module_catalog import is_initial_module_slug


class Module(models.Model):
    """Representa uma area funcional exibida no dashboard."""

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

    @property
    def uses_generic_entry(self) -> bool:
        """Indica se o módulo ainda usa a entrada genérica por slug."""

        return self.url_name == "module_entry"

    @property
    def permission_label(self) -> str:
        """Expõe uma label amigável da permissão exigida pelo módulo."""

        return self.full_permission or "Apenas login no sistema"

    @property
    def is_initial_module(self) -> bool:
        """Indica se o módulo pertence ao seed canônico do projeto."""

        return is_initial_module_slug(self.slug)

    @property
    def delete_block_reason(self) -> str:
        """Explica por que o módulo não pode ser excluído com segurança."""

        if self.is_initial_module:
            return "Módulos canônicos do seed não podem ser excluídos pelo painel."
        if self.is_active:
            return "Inative o módulo antes de solicitar a exclusão."
        return ""

    def get_absolute_url(self) -> str:
        """Resolve a URL nomeada configurada para o modulo."""

        if self.uses_generic_entry:
            return reverse("module_entry", kwargs={"slug": self.slug})
        return reverse(self.url_name)
