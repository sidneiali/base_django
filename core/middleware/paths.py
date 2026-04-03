"""Regras de roteamento usadas pelos middlewares da API."""

OPERATIONAL_HEALTH_PATHS = frozenset(
    {
        "/api/core/health/",
        "/api/v1/core/health/",
    }
)


def is_json_api_request(path: str) -> bool:
    """Indica se a rota pertence aos endpoints JSON protegidos/operacionais."""

    if path.startswith("/api/docs/"):
        return False
    if path in {
        "/api/docs/",
        "/api/docs/postman.json",
        "/api/openapi.json",
        "/api/v1/openapi.json",
    }:
        return False
    return (
        path.startswith("/api/core/")
        or path.startswith("/api/panel/")
        or path.startswith("/api/v1/core/")
        or path.startswith("/api/v1/panel/")
    )


def is_operational_health_path(path: str) -> bool:
    """Identifica os healthchecks leves que ficam fora de controles extras."""

    return path in OPERATIONAL_HEALTH_PATHS


def is_rate_limited_path(path: str) -> bool:
    """Define quais rotas JSON entram no controle de rate limit."""

    if not is_json_api_request(path):
        return False
    return not is_operational_health_path(path)
