"""Ponto de entrada unico das configuracoes do projeto.

Mantem ``config.settings`` como modulo padrao e seleciona o perfil de
ambiente a partir de ``APP_ENV``.
"""

from __future__ import annotations

import os
from importlib import import_module

ENVIRONMENT_ALIASES = {
    "dev": "development",
    "development": "development",
    "local": "development",
    "prod": "production",
    "production": "production",
}

raw_environment = os.getenv("APP_ENV", "development").strip().lower()
SETTINGS_ENVIRONMENT = ENVIRONMENT_ALIASES.get(raw_environment)

if SETTINGS_ENVIRONMENT is None:
    supported = ", ".join(sorted(ENVIRONMENT_ALIASES))
    raise RuntimeError(
        f"APP_ENV invalido: {raw_environment!r}. Use um destes valores: {supported}.",
    )

environment_settings = import_module(f"{__name__}.{SETTINGS_ENVIRONMENT}")

for setting_name in dir(environment_settings):
    if setting_name.isupper():
        globals()[setting_name] = getattr(environment_settings, setting_name)
