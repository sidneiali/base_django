"""Testes do logging estruturado do projeto."""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

from django.test import SimpleTestCase

from core.audit import AuditContext
from core.logging import RequestContextFilter, StructuredLogFormatter


class LoggingHelpersTests(SimpleTestCase):
    """Garante o contrato básico do logging estruturado."""

    def test_request_context_filter_copies_audit_context_to_record(self) -> None:
        """Os campos da requisição devem ser expostos no record do log."""

        record = logging.LogRecord(
            name="core.tests",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="evento de teste",
            args=(),
            exc_info=None,
        )

        with patch(
            "core.logging.get_audit_context",
            return_value=AuditContext(
                actor_identifier="operador",
                request_method="GET",
                path="/painel/auditoria/",
                request_id="req-123",
            ),
        ):
            should_log = RequestContextFilter().filter(record)

        self.assertTrue(should_log)
        self.assertEqual(getattr(record, "request_id"), "req-123")
        self.assertEqual(getattr(record, "request_method"), "GET")
        self.assertEqual(getattr(record, "request_path"), "/painel/auditoria/")
        self.assertEqual(getattr(record, "actor_identifier"), "operador")

    def test_structured_log_formatter_renders_json_payload(self) -> None:
        """O formatter estruturado deve serializar o evento em JSON estável."""

        record = logging.LogRecord(
            name="core.tests",
            level=logging.ERROR,
            pathname=__file__,
            lineno=20,
            msg="falha controlada",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-999"
        record.request_method = "POST"
        record.request_path = "/api/v1/core/health/"
        record.actor_identifier = "auditor"

        payload = json.loads(StructuredLogFormatter().format(record))

        self.assertEqual(payload["level"], "ERROR")
        self.assertEqual(payload["logger"], "core.tests")
        self.assertEqual(payload["message"], "falha controlada")
        self.assertEqual(payload["request_id"], "req-999")
        self.assertEqual(payload["request_method"], "POST")
        self.assertEqual(payload["request_path"], "/api/v1/core/health/")
        self.assertEqual(payload["actor_identifier"], "auditor")
        self.assertIn("timestamp", payload)
