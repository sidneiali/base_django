"""Geração da especificação OpenAPI e da estrutura usada na docs pública."""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any, cast

from panel.api.groups import build_groups_ninja_openapi_fragment

from .openapi_components import build_openapi_components
from .openapi_paths import build_openapi_paths
from .types import DocsOperation, DocsSection

TAG_ORDER = [
    "Operacional",
    "Acesso à API",
    "Usuários do painel",
    "Grupos do painel",
    "Módulos do painel",
    "Logs de auditoria",
]


def build_public_base_url(request) -> str:
    """Retorna a URL base absoluta da instância atual sem barra final."""

    return request.build_absolute_uri("/").rstrip("/")


def _slugify_label(value: str) -> str:
    """Converte um rótulo humano em slug simples para ids HTML."""

    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "section"


def build_openapi_schema(request) -> dict[str, object]:
    """Monta a especificação OpenAPI real da API pública versionada."""

    base_url = build_public_base_url(request)
    components = build_openapi_components()
    paths = build_openapi_paths(base_url)
    groups_fragment = build_groups_ninja_openapi_fragment()
    paths.update(groups_fragment.get("paths", {}))
    ninja_components = groups_fragment.get("components", {})
    ninja_schemas = cast(dict[str, Any], ninja_components.get("schemas", {}))
    if ninja_schemas:
        components.setdefault("schemas", cast(dict[str, Any], {})).update(ninja_schemas)
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "BaseApp API",
            "version": "1.0.0",
            "description": (
                "API versionada da BaseApp para introspecção da conta, gestão de usuários "
                "grupos e módulos do painel, além da leitura dos logs de auditoria."
            ),
        },
        "servers": [
            {
                "url": base_url,
                "description": "Instância atual da aplicação",
            }
        ],
        "security": [{"BearerAuth": []}],
        "components": components,
        "paths": paths,
    }


def build_docs_sections(schema: dict[str, object]) -> list[DocsSection]:
    """Converte a spec OpenAPI em seções simples para a documentação HTML."""

    sections_map: OrderedDict[str, DocsSection] = OrderedDict(
        (
            tag,
            {
                "id": f"section-{_slugify_label(tag)}",
                "label": tag,
                "base_url": "",
                "operations": [],
            },
        )
        for tag in TAG_ORDER
    )

    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return []

    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue

        for method, operation in methods.items():
            if not isinstance(method, str) or not isinstance(operation, dict):
                continue

            tags = operation.get("tags", [])
            if not isinstance(tags, list) or not tags or not isinstance(tags[0], str):
                continue

            tag = tags[0]
            section = sections_map.setdefault(
                tag,
                {
                    "id": f"section-{_slugify_label(tag)}",
                    "label": tag,
                    "base_url": "",
                    "operations": [],
                },
            )
            if not section["base_url"]:
                base_url = operation.get("x-base-url", path)
                section["base_url"] = base_url if isinstance(base_url, str) else path

            code_samples: dict[str, str] = {}
            raw_samples = operation.get("x-codeSamples", [])
            if isinstance(raw_samples, list):
                for sample in raw_samples:
                    if not isinstance(sample, dict):
                        continue
                    lang = sample.get("lang")
                    source = sample.get("source")
                    if isinstance(lang, str) and isinstance(source, str):
                        code_samples[lang.lower()] = source

            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str):
                operation_id = f"{method}_{path}"

            summary = operation.get("summary", "")
            if not isinstance(summary, str):
                summary = ""

            docs_operation: DocsOperation = {
                "id": operation_id.replace("_", "-"),
                "method": method.upper(),
                "path": path,
                "summary": summary,
                "code_samples": code_samples,
            }
            section["operations"].append(docs_operation)

    return [section for section in sections_map.values() if section["operations"]]
