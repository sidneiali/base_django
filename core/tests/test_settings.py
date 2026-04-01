"""Testes das helpers de configuração dos settings."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from config.settings import base as base_settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class DatabaseConfigBuilderTests(SimpleTestCase):
    """Valida a montagem do banco por ambiente."""

    def test_build_database_config_defaults_to_sqlite(self) -> None:
        """Sem overrides, o builder deve manter sqlite no fluxo local."""

        with patch.dict(os.environ, {}, clear=True):
            config = base_settings.build_database_config(Path("db.sqlite3"))

        self.assertEqual(config["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["default"]["NAME"], "db.sqlite3")

    def test_build_database_config_uses_postgresql_defaults_when_requested(self) -> None:
        """Produção deve nascer com os defaults operacionais de PostgreSQL."""

        with patch.dict(
            os.environ,
            {
                "DATABASE_NAME": "base_django",
                "DATABASE_USER": "base_django",
                "DATABASE_PASSWORD": "segredo",
                "DATABASE_HOST": "127.0.0.1",
            },
            clear=True,
        ):
            config = base_settings.build_database_config(
                "app",
                default_engine="django.db.backends.postgresql",
                require_non_sqlite_fields=(
                    "DATABASE_NAME",
                    "DATABASE_USER",
                    "DATABASE_PASSWORD",
                    "DATABASE_HOST",
                ),
            )

        database = config["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(database["NAME"], "base_django")
        self.assertEqual(database["PORT"], "5432")
        self.assertEqual(database["CONN_MAX_AGE"], 60)
        self.assertEqual(database["CONN_HEALTH_CHECKS"], True)

    def test_build_database_config_requires_fields_for_non_sqlite(self) -> None:
        """Produção não deve aceitar PostgreSQL sem credenciais mínimas."""

        with patch.dict(
            os.environ,
            {"DATABASE_ENGINE": "django.db.backends.postgresql"},
            clear=True,
        ):
            with self.assertRaises(ImproperlyConfigured):
                base_settings.build_database_config(
                    "app",
                    default_engine="django.db.backends.postgresql",
                    require_non_sqlite_fields=(
                        "DATABASE_NAME",
                        "DATABASE_USER",
                        "DATABASE_PASSWORD",
                        "DATABASE_HOST",
                    ),
                )
