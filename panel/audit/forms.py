"""Formulários de filtro para a trilha de auditoria no painel."""

from __future__ import annotations

from typing import Any

from core.models import AuditLog
from django import forms


class AuditLogFilterForm(forms.Form):
    """Valida os filtros expostos na listagem HTML de auditoria."""

    actor = forms.CharField(
        required=False,
        label="Ator",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Pesquisar por usuário ou identificador",
                "data-teste": "audit-filter-actor",
            }
        ),
    )
    action = forms.ChoiceField(
        required=False,
        label="Ação",
        choices=[("", "Todas")] + list(AuditLog.ACTION_CHOICES),
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "data-teste": "audit-filter-action",
            }
        ),
    )
    object_query = forms.CharField(
        required=False,
        label="Objeto",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Pesquisar por objeto, caminho ou request ID",
                "data-teste": "audit-filter-object-query",
            }
        ),
    )
    date_from = forms.DateField(
        required=False,
        label="Data inicial",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "data-teste": "audit-filter-date-from",
            },
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )
    date_to = forms.DateField(
        required=False,
        label="Data final",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "data-teste": "audit-filter-date-to",
            },
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )

    def clean(self) -> dict[str, object]:
        """Impede intervalos inválidos antes da consulta."""

        cleaned_data: dict[str, Any] = super().clean() or {}
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            self.add_error(
                "date_to",
                "A data final precisa ser igual ou posterior à data inicial.",
            )

        return cleaned_data
