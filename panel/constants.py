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
    "axes": "Segurança de login",
    "core": "Base",
    "panel": "Configurações",
}
