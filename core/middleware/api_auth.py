"""Middleware de autenticação Bearer para a API interna."""

from ..api.auth import authenticate_api_request
from .paths import is_json_api_request


class ApiTokenAuthenticationMiddleware:
    """Autentica chamadas Bearer da API antes da auditoria montar o contexto."""

    def __init__(self, get_response):
        """Armazena o próximo callable da stack de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Resolve o token Bearer em ``request.user`` para rotas JSON da API."""

        request.api_token = None
        request.api_auth_result = None

        if is_json_api_request(request.path):
            auth_result = authenticate_api_request(request)
            request.api_auth_result = auth_result
            request.api_token = auth_result.token

            if auth_result.is_authenticated:
                request.user = auth_result.user
                request._cached_user = auth_result.user

        return self.get_response(request)
