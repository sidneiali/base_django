"""Cliente simples para testar a API local e inspecionar a resposta.

Uso rapido:

    # Opcional: preencha scripts/.env com BASEAPP_API_TOKEN
    python scripts/api_request.py /api/v1/core/me/

    python scripts/api_request.py /api/v1/core/health/

    python scripts/api_request.py /api/v1/panel/users/ --method POST --json "{\"username\":\"api-user\",\"email\":\"api@example.com\",\"password\":\"SenhaSegura@123\"}"
    python scripts/api_request.py /api/v1/panel/groups/ --method POST --json "{\"name\":\"Grupo API\",\"permissions\":[1]}"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request


SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_ENV_FILE = SCRIPT_DIR / ".env"
ROUTE_EXAMPLES = [
    "/api/v1/core/health/",
    "/api/v1/core/me/",
    "/api/v1/core/token/",
    "/api/v1/core/audit-logs/",
    "/api/v1/core/audit-logs/1/",
    "/api/v1/panel/users/",
    "/api/v1/panel/users/1/",
    "/api/v1/panel/groups/",
    "/api/v1/panel/groups/1/",
]


def build_help_epilog() -> str:
    """Monta o rodapé do --help com rotas e exemplos práticos."""

    routes = "\n".join(f"  {route}" for route in ROUTE_EXAMPLES)
    return (
        "Rotas uteis:\n"
        f"{routes}\n\n"
        "Exemplos:\n"
        "  python scripts/api_request.py /api/v1/core/health/\n"
        "  python scripts/api_request.py /api/v1/core/me/\n"
        "  python scripts/api_request.py /api/v1/core/audit-logs/\n"
        "  python scripts/api_request.py /api/v1/panel/users/\n"
        "  python scripts/api_request.py /api/v1/panel/groups/\n"
        "  python scripts/api_request.py /api/v1/panel/users/ --method POST --json "
        "\"{\\\"username\\\":\\\"api-user\\\",\\\"email\\\":\\\"api@example.com\\\",\\\"password\\\":\\\"SenhaSegura@123\\\"}\"\n"
        "  python scripts/api_request.py /api/v1/panel/groups/ --method POST --json "
        "\"{\\\"name\\\":\\\"Grupo API\\\",\\\"permissions\\\":[1]}\""
    )


def load_local_env() -> None:
    """Carrega variáveis simples de um scripts/.env sem sobrescrever o ambiente."""

    if not LOCAL_ENV_FILE.exists():
        return

    for raw_line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    """Constroi os argumentos aceitos pelo cliente."""

    parser = argparse.ArgumentParser(
        description="Faz uma chamada HTTP para a API da BaseApp e imprime a resposta.",
        epilog=build_help_epilog(),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="/api/v1/core/health/",
        help="Path da rota da API. Ex.: /api/v1/core/me/",
    )
    parser.add_argument(
        "--method",
        default="GET",
        help="Metodo HTTP. Ex.: GET, POST, PATCH, DELETE.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("BASEAPP_API_BASE_URL", "http://127.0.0.1:8000"),
        help="URL base da aplicacao. Default: BASEAPP_API_BASE_URL ou http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("BASEAPP_API_TOKEN", ""),
        help="Bearer token. Default: BASEAPP_API_TOKEN",
    )
    parser.add_argument(
        "--json",
        dest="json_payload",
        default="",
        help='Payload JSON inline. Ex.: --json "{\\"email\\":\\"api@example.com\\"}"',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout da requisicao em segundos.",
    )
    parser.add_argument(
        "--list-routes",
        action="store_true",
        help="Lista as rotas úteis conhecidas e encerra.",
    )
    return parser


def normalize_url(base_url: str, path: str) -> str:
    """Combina base URL e path garantindo uma barra unica."""

    return parse.urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def build_request_data(json_payload: str) -> bytes | None:
    """Serializa o payload JSON quando informado."""

    if not json_payload:
        return None

    payload: Any = json.loads(json_payload)
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def print_response(response_status: int, response_headers: Any, response_body: bytes) -> None:
    """Imprime status, headers relevantes e corpo formatado."""

    print(f"Status: {response_status}")

    request_id = response_headers.get("X-Request-ID")
    if request_id:
        print(f"X-Request-ID: {request_id}")

    content_type = response_headers.get("Content-Type", "")
    if content_type:
        print(f"Content-Type: {content_type}")

    print("Headers:")
    for key, value in response_headers.items():
        print(f"  {key}: {value}")

    print("\nBody:")
    if not response_body:
        print("<empty>")
        return

    body_text = response_body.decode("utf-8", errors="replace")
    if "application/json" in content_type:
        try:
            parsed = json.loads(body_text)
        except json.JSONDecodeError:
            print(body_text)
            return

        print(json.dumps(parsed, ensure_ascii=False, indent=4))
        return

    print(body_text)


def main() -> int:
    """Executa a chamada HTTP a partir dos argumentos recebidos."""

    load_local_env()
    parser = build_parser()
    args = parser.parse_args()

    if args.list_routes:
        print("Rotas úteis:")
        for route in ROUTE_EXAMPLES:
            print(route)
        return 0

    url = normalize_url(args.base_url, args.path)
    data = build_request_data(args.json_payload)

    headers = {
        "Accept": "application/json",
    }
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    if data is not None:
        headers["Content-Type"] = "application/json"

    http_request = request.Request(
        url=url,
        data=data,
        headers=headers,
        method=args.method.upper(),
    )

    print(f"Request: {http_request.method} {url}")

    try:
        with request.urlopen(http_request, timeout=args.timeout) as response:
            print_response(response.status, response.headers, response.read())
            return 0
    except error.HTTPError as exc:
        print_response(exc.code, exc.headers, exc.read())
        return 1
    except Exception as exc:  # pragma: no cover - utilitario local
        print(f"Erro ao chamar a API: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
