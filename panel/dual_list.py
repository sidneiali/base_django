"""Helpers específicos para listas duplas nos formulários do painel."""

from collections.abc import Iterable
from typing import TypeAlias, cast

from django import forms

DualListChoice: TypeAlias = tuple[object, object]


def _normalize_bound_values(value: object) -> list[object]:
    """Normaliza o valor atual do campo para uma lista estável de ids."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def build_dual_list_choices(
    form: forms.BaseForm,
    field_name: str,
) -> tuple[list[DualListChoice], list[DualListChoice]]:
    """
    Separa as opcoes disponiveis e selecionadas de um campo multiplo.

    Retorna duas listas no formato ``(pk, label)`` para facilitar a
    renderizacao customizada de widgets dual-list nos templates.
    """

    field = cast(forms.ChoiceField, form.fields[field_name])
    choices = cast(Iterable[DualListChoice], field.choices)
    current_ids = {
        str(item) for item in _normalize_bound_values(form[field_name].value())
    }

    available: list[DualListChoice] = []
    chosen: list[DualListChoice] = []
    for pk, label in choices:
        if not pk:
            continue
        (chosen if str(pk) in current_ids else available).append((pk, label))

    return available, chosen
