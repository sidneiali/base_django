"""Ponto de entrada WSGI do projeto.

Inicializa o ambiente Django com ``config.settings`` e expoe a variavel
``application`` para servidores compativeis com WSGI.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
