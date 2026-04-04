"""Serviços do domínio de módulos do painel."""

from __future__ import annotations

from core.models import Module
from django.contrib.auth.models import Permission


class ModuleDeletionBlockedError(Exception):
    """Indica que o módulo não pode ser removido com segurança."""


def save_panel_module(
    module: Module,
    *,
    permission: Permission | None,
    commit: bool = True,
) -> Module:
    """Aplica a permissão escolhida e persiste o módulo quando necessário."""

    if permission is None:
        module.app_label = ""
        module.permission_codename = ""
    else:
        module.app_label = permission.content_type.app_label
        module.permission_codename = permission.codename

    if commit:
        module.save()

    return module


def set_module_active_state(module: Module, *, is_active: bool) -> Module:
    """Ativa ou inativa o módulo sem repetir lógica nas views HTML."""

    if module.is_active != is_active:
        module.is_active = is_active
        module.save(update_fields=["is_active"])

    return module


def delete_panel_module(module: Module) -> None:
    """Remove o módulo quando ele estiver elegível para exclusão."""

    block_reason = module.delete_block_reason
    if block_reason:
        raise ModuleDeletionBlockedError(block_reason)

    module.delete()
