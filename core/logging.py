"""Helpers de logging estruturado com contexto da requisição atual."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from core.audit.context import get_audit_context


class RequestContextFilter(logging.Filter):
    """Publica campos básicos do contexto da requisição em cada record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Enriquece o record com request id, rota e ator corrente."""

        context = get_audit_context()
        record.request_id = getattr(record, "request_id", "") or context.request_id or "-"
        record.request_path = getattr(record, "request_path", "") or context.path or ""
        record.request_method = (
            getattr(record, "request_method", "") or context.request_method or ""
        )
        record.actor_identifier = (
            getattr(record, "actor_identifier", "") or context.actor_identifier or ""
        )
        return True


class StructuredLogFormatter(logging.Formatter):
    """Formata records em JSON simples e estável para operação."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializa o evento de log com campos úteis de observabilidade."""

        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "") or "",
        }

        request_method = getattr(record, "request_method", "") or ""
        if request_method:
            payload["request_method"] = request_method

        request_path = getattr(record, "request_path", "") or ""
        if request_path:
            payload["request_path"] = request_path

        actor_identifier = getattr(record, "actor_identifier", "") or ""
        if actor_identifier:
            payload["actor_identifier"] = actor_identifier

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=True, default=str)
