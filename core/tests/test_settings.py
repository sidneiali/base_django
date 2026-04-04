"""Testes das helpers de configuração dos settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast
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


class ObservabilitySettingsBuilderTests(SimpleTestCase):
    """Valida os builders auxiliares de observabilidade e staticfiles."""

    def test_insert_middleware_after_keeps_order_and_avoids_duplicates(self) -> None:
        """WhiteNoise deve entrar logo após o SecurityMiddleware."""

        result = base_settings.insert_middleware_after(
            [
                "django.middleware.security.SecurityMiddleware",
                "django.middleware.common.CommonMiddleware",
            ],
            anchor="django.middleware.security.SecurityMiddleware",
            middleware="whitenoise.middleware.WhiteNoiseMiddleware",
        )

        self.assertEqual(
            result,
            [
                "django.middleware.security.SecurityMiddleware",
                "whitenoise.middleware.WhiteNoiseMiddleware",
                "django.middleware.common.CommonMiddleware",
            ],
        )

    def test_build_storage_settings_allows_manifest_backend(self) -> None:
        """Produção deve conseguir trocar apenas o backend dos staticfiles."""

        storages = base_settings.build_storage_settings(
            staticfiles_backend="whitenoise.storage.CompressedManifestStaticFilesStorage"
        )

        self.assertEqual(
            storages["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )
        self.assertEqual(
            storages["default"]["BACKEND"],
            "django.core.files.storage.FileSystemStorage",
        )

    def test_build_logging_config_adds_optional_file_handler(self) -> None:
        """Quando houver arquivo configurado, o handler deve ser materializado."""

        logging_config = base_settings.build_logging_config(
            level="INFO",
            json_logs=True,
            log_file="logs/app.log",
        )
        formatters = cast(dict[str, dict[str, object]], logging_config["formatters"])
        handlers = cast(dict[str, dict[str, object]], logging_config["handlers"])
        root = cast(dict[str, object], logging_config["root"])
        root_handlers = cast(list[str], root["handlers"])

        self.assertEqual(
            formatters["structured"]["()"],
            "core.logging.StructuredLogFormatter",
        )
        self.assertIn("file", handlers)
        self.assertIn("file", root_handlers)

    def test_initialize_sentry_skips_when_dsn_is_empty(self) -> None:
        """Sem DSN, a inicialização do Sentry não deve ser chamada."""

        with patch("sentry_sdk.init") as sentry_init:
            base_settings.initialize_sentry(
                dsn="",
                environment="production",
                traces_sample_rate=0.0,
                profiles_sample_rate=0.0,
                send_default_pii=False,
            )

        sentry_init.assert_not_called()

    def test_initialize_sentry_passes_expected_options(self) -> None:
        """Com DSN, o helper deve propagar os parâmetros principais."""

        with patch("sentry_sdk.init") as sentry_init:
            base_settings.initialize_sentry(
                dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
                environment="production",
                traces_sample_rate=0.25,
                profiles_sample_rate=0.1,
                send_default_pii=True,
            )

        sentry_init.assert_called_once()
        kwargs = sentry_init.call_args.kwargs
        self.assertEqual(kwargs["environment"], "production")
        self.assertEqual(kwargs["traces_sample_rate"], 0.25)
        self.assertEqual(kwargs["profiles_sample_rate"], 0.1)
        self.assertEqual(kwargs["send_default_pii"], True)
        self.assertTrue(kwargs["integrations"])
