"""Middlewares de autenticacao complementar e auditoria da aplicacao."""

from .api_auth import authenticate_api_request

from .audit import reset_audit_context, set_audit_context


class ApiTokenAuthenticationMiddleware:
    """Autentica chamadas Bearer da API antes da auditoria montar o contexto."""

    def __init__(self, get_response):
        """Armazena o próximo callable da stack de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Resolve o token Bearer em ``request.user`` para rotas JSON da API."""

        request.api_token = None
        request.api_auth_result = None

        if request.path.startswith("/api/") and not request.path.startswith("/api/docs/"):
            auth_result = authenticate_api_request(request)
            request.api_auth_result = auth_result
            request.api_token = auth_result.token

            if auth_result.is_authenticated:
                request.user = auth_result.user
                request._cached_user = auth_result.user

        return self.get_response(request)


class AuditContextMiddleware:
    """Mantem usuario, rota e IP acessiveis durante o ciclo da requisicao."""

    def __init__(self, get_response):
        """Armazena o callable seguinte da stack de middlewares."""

        self.get_response = get_response

    def __call__(self, request):
        """Publica o contexto atual e o limpa ao final da resposta."""

        token = set_audit_context(request)
        try:
            return self.get_response(request)
        finally:
            reset_audit_context(token)
