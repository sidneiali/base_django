"""Constantes usadas nas regras do painel administrativo."""

PROTECTED_GROUP_NAMES = {
    "Superadmin",
    "Root",
    "Infra",
}

BLOCKED_PERMISSION_APP_LABELS = {
    "admin",
    "contenttypes",
    "sessions",
}

APP_LABEL_TRANSLATIONS = {
    "auth": "Autenticação",
    "core": "Base",
    "panel": "Configurações",
}
