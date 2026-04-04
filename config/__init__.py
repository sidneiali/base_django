"""Pacote de configuracao central do projeto Django.

Este pacote concentra os modulos de settings, roteamento e entrypoints
ASGI/WSGI usados para carregar a aplicacao.
"""

from .celery import app as celery_app

__all__ = ["celery_app"]
