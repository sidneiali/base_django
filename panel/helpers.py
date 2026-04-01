"""Helpers compartilhados do painel administrativo."""


def build_dual_list_choices(form, field_name: str) -> tuple[list, list]:
    """
    Separa as opcoes disponiveis e selecionadas de um campo multiplo.

    Retorna duas listas no formato ``(pk, label)`` para facilitar a
    renderizacao customizada de widgets dual-list nos templates.
    """

    field = form.fields[field_name]
    current_ids = {str(v) for v in (form[field_name].value() or [])}

    available: list[tuple] = []
    chosen: list[tuple] = []
    for pk, label in field.choices:
        if not pk:
            continue
        (chosen if str(pk) in current_ids else available).append((pk, label))

    return available, chosen
