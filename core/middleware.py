"""Middleware que expõe o contexto da requisicao para a auditoria."""

from .audit import reset_audit_context, set_audit_context


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
