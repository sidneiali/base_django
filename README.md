# Base Django

Base de sistema em Django com:

- autenticação por login
- dashboard orientado a módulos
- controle de acesso por permissões do Django
- painel interno para gestão de usuários e grupos
- interface em Tabler com assets locais em `static/vendor/tabler`

O projeto foi pensado como ponto de partida para sistemas administrativos em que cada área do produto pode ser cadastrada como um módulo e liberada por grupo/permissão.

## Stack

- Python 3.13+
- Django
- django-bootstrap5
- SQLite em desenvolvimento
- PostgreSQL em produção
- GitHub Actions para CI
- Tabler vendorizado em `static/vendor/tabler`

## Como rodar

Com `uv`:

```bash
uv sync --no-install-project
# opcional: instala lint, testes e tipagem
# uv sync --no-install-project --extra dev
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Com `pip`:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install django django-bootstrap5 "psycopg[binary]"
# opcional: instala lint, testes e tipagem
# python -m pip install pytest pytest-django ruff mypy django-stubs
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Por padrão, o projeto sobe em modo de desenvolvimento (`APP_ENV=development`).

Depois acesse:

- `http://127.0.0.1:8000/login/`
- `http://127.0.0.1:8000/admin/`

## Recuperação de senha e e-mail

O projeto já inclui o fluxo externo de recuperação de senha em:

- `/recuperar-senha/`
- `/recuperar-senha/enviado/`
- `/recuperar-senha/confirmar/<uid>/<token>/`
- `/recuperar-senha/concluido/`

Em desenvolvimento, o envio pode continuar no console. Para usar envio real com SMTP, copie os valores de [`.env.example`](c:\Users\sidne\OneDrive\Desktop\base_django\.env.example) para as variáveis de ambiente do processo.

## Ambientes de configuração

O ponto de entrada continua sendo `config.settings`, mas agora ele seleciona o perfil
de ambiente com base em `APP_ENV`.

Perfis disponíveis:

- `APP_ENV=development`: defaults locais, `DEBUG=True`, static por `STATICFILES_DIRS` e e-mail no console por padrão
- `APP_ENV=production`: `DEBUG=False` por padrão, exige `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD` e `DATABASE_HOST`, usa PostgreSQL por padrão, `STATIC_ROOT` e SMTP por padrão

Arquivos principais:

- [`config/settings/__init__.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\__init__.py): seletor do ambiente
- [`config/settings/base.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\base.py): configuração compartilhada
- [`config/settings/development.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\development.py): defaults de desenvolvimento
- [`config/settings/production.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\production.py): defaults de produção

Exemplo de produção:

```text
APP_ENV=production
SECRET_KEY=<chave_forte>
ALLOWED_HOSTS=seudominio.com,www.seudominio.com
CSRF_TRUSTED_ORIGINS=https://seudominio.com,https://www.seudominio.com
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=base_django
DATABASE_USER=base_django
DATABASE_PASSWORD=<senha_forte>
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_CONN_MAX_AGE=60
DATABASE_CONN_HEALTH_CHECKS=True
DATABASE_SSLMODE=require
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
APP_FORCE_HTTPS=True
STATIC_ROOT=/var/app/staticfiles
```

Configuração recomendada com `Resend`:

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=465
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<sua_api_key>
EMAIL_USE_SSL=True
DEFAULT_FROM_EMAIL=BaseApp <no-reply@seudominio.com>
PASSWORD_RESET_TIMEOUT=3600
APP_FORCE_HTTPS=True
SECURE_HSTS_SECONDS=31536000
```

Com `APP_FORCE_HTTPS=True`, a aplicação passa a marcar cookies como seguros e habilita redirecionamento SSL/HSTS, o que é importante para o reset em produção.

## Deploy de produção

Fluxo mínimo recomendado:

1. provisionar as variáveis de ambiente de produção, com PostgreSQL e HTTPS
2. validar a configuração:

```bash
uv run python manage.py check --deploy
```

3. aplicar migrations:

```bash
uv run python manage.py migrate
```

4. publicar os arquivos estáticos:

```bash
uv run python manage.py collectstatic --noinput
```

5. subir a aplicação via servidor WSGI/ASGI da sua infraestrutura

## Healthcheck operacional

O projeto já expõe um healthcheck público e leve em:

- `/api/core/health/`
- `/api/v1/core/health/`

Exemplo:

```bash
curl http://127.0.0.1:8000/api/v1/core/health/
```

Esse endpoint responde com `status`, `timestamp`, `timezone`, dados básicos de rate limit e `request_id`, o que já atende monitoramento simples e smoke checks de plataforma.

Por ora, o projeto mantém apenas esse `healthcheck` leve. Um endpoint separado de `readiness` passa a fazer mais sentido quando houver dependências operacionais adicionais, como fila, cache distribuído ou integrações obrigatórias para o boot.

## CI

O repositório agora possui pipeline em [ci.yml](c:\Users\sidne\OneDrive\Desktop\base_django\.github\workflows\ci.yml) com:

- `uv run ruff check config core panel`
- `uv run pytest`
- `uv run python manage.py check`
- `uv run python manage.py check --deploy`
- `uv run python manage.py collectstatic --noinput`

## Visão geral

O sistema possui dois apps principais:

- `core`: dashboard, cadastro de módulos, montagem de acesso por permissão e páginas base
- `panel`: gestão de usuários, grupos, módulos e superfícies operacionais sem depender diretamente do admin do Django

Fluxo principal:

1. o usuário faz login
2. o dashboard consulta os módulos ativos
3. cada módulo pode ou não exigir uma permissão do Django
4. se o usuário tiver acesso, entra na rota do módulo
5. se não tiver, recebe `403`

## Estrutura do projeto

```text
config/     configuração global, settings e rotas principais
core/       módulos centrais, dashboard, API, auditoria e shell autenticado
panel/      telas e endpoints internos para usuários e grupos
templates/  layout base, login, dashboard, páginas e partials
static/     CSS customizado
```

## Modelo central: Module

O model [`core/models/modules.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\models\modules.py) define os módulos exibidos no dashboard.

Campos principais:

- `name`: nome do módulo
- `slug`: identificador usado na rota genérica
- `description`: texto curto do card
- `icon`: classe de ícone usada na interface
- `url_name`: nome da URL Django que será aberta ao clicar no módulo
- `app_label`: app da permissão
- `permission_codename`: codename da permissão
- `menu_group`: agrupamento visual no dashboard
- `order`: ordem de exibição
- `is_active`: ativa ou oculta o módulo

Regra de permissão:

- se `app_label` e `permission_codename` estiverem preenchidos, o acesso depende de `app_label.permission_codename`
- se estiverem vazios, qualquer usuário autenticado pode acessar o módulo
- superusuário sempre tem acesso

## Como cadastrar um módulo

Os módulos são gerenciados pelo admin do Django no pacote [`core/admin`](c:\Users\sidne\OneDrive\Desktop\base_django\core\admin).

Exemplo prático:

- `name`: Usuários
- `slug`: usuarios
- `description`: Gestão de usuários do sistema
- `url_name`: `panel_users_list`
- `app_label`: `auth`
- `permission_codename`: `view_user`
- `menu_group`: Configurações
- `order`: `10`

Com isso, o card abrirá a rota nomeada `panel_users_list` e só ficará disponível para quem tiver a permissão `auth.view_user`.

Se um módulo ainda não tiver área dedicada, ele também pode usar `url_name=module_entry`.
Nesse caso, o dashboard resolve a rota genérica por `slug` em `/modulo/<slug>/`, o que
permite publicar o módulo no shell enquanto a tela final ainda está em construção.

## Seed inicial dos módulos

Para bootstrap local, o projeto possui um comando idempotente para criar ou atualizar
os módulos iniciais do dashboard:

```bash
uv run python manage.py seed_initial_modules
```

Hoje o seed cria o conjunto mínimo de módulos internos:

- `Módulos`
- `Usuários`
- `Grupos`
- `Auditoria`
- `Documentação da API`

O comando pode ser executado novamente sem duplicar registros; ele reconcilia os
campos canônicos por `slug`.

## Rotas principais

- `/login/`: tela de autenticação
- `/logout/`: logout
- `/`: dashboard
- `/modulo/<slug>/`: entrada genérica de módulo
- `/painel/usuarios/`: listagem de usuários
- `/painel/usuarios/novo/`: criação de usuário
- `/painel/usuarios/<id>/editar/`: edição de usuário
- `/painel/modulos/`: listagem de módulos do dashboard
- `/painel/modulos/novo/`: criação de módulo
- `/painel/modulos/<id>/editar/`: edição de módulo
- `/painel/grupos/`: listagem de grupos
- `/painel/grupos/novo/`: criação de grupo
- `/painel/grupos/<id>/editar/`: edição de grupo
- `/painel/auditoria/`: trilha HTML de auditoria com filtros
- `/painel/auditoria/<id>/`: drill-down completo de um evento de auditoria
- `/api/v1/panel/users/`: coleção JSON de usuários do painel
- `/api/v1/panel/users/<id>/`: detalhe JSON de usuário
- `/api/v1/panel/groups/`: coleção JSON de grupos do painel
- `/api/v1/panel/groups/<id>/`: detalhe JSON de grupo
- `/api/v1/panel/modules/`: coleção JSON de módulos do dashboard
- `/api/v1/panel/modules/<id>/`: detalhe JSON de módulo
- `/admin/`: admin do Django

## Painel interno

O app [`panel`](c:\Users\sidne\OneDrive\Desktop\base_django\panel) oferece uma camada mais amigável para administração:

- usuários comuns podem ser criados e editados sem virar `staff` ou `superuser`
- módulos do dashboard podem ser cadastrados, editados e publicados sem depender do admin
- módulos canônicos do seed podem ser inativados, mas não podem ser excluídos pelo painel
- módulos customizados precisam estar inativos antes de poderem ser excluídos com segurança
- grupos protegidos não aparecem para edição: `Superadmin`, `Root` e `Infra`
- permissões de apps internos do Django como `admin`, `contenttypes` e `sessions` não são exibidas no formulário de grupos
- os nomes de permissões são traduzidos para uma leitura mais amigável em português

Permissões exigidas por tela:

- módulos: `core.view_module`, `core.add_module`, `core.change_module`
- usuários: `auth.view_user`, `auth.add_user`, `auth.change_user`
- grupos: `auth.view_group`, `auth.add_group`, `auth.change_group`
- auditoria: `core.view_auditlog`

Na tela de auditoria, operadores podem filtrar eventos por ator, ação e data, navegar por paginação mais rica e abrir o detalhe completo de cada evento com `before`, `after`, `changes`, `metadata`, request e objeto associado.

Na API do painel, o projeto agora expõe recursos versionados para usuários, grupos e módulos, todos protegidos por Bearer token, envelope JSON padronizado e matriz CRUD por recurso.

## Arquivos importantes

- [`config/settings/base.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\base.py): configuração compartilhada entre ambientes
- [`config/settings/development.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\development.py): defaults locais
- [`config/settings/production.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\production.py): defaults de produção
- [`config/urls.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\urls.py): composição das rotas do projeto
- [`core/navigation.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\navigation.py): monta e reaproveita a navegação do dashboard e do sidebar por request
- [`core/models/audit.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\models\audit.py): trilha de auditoria do sistema
- [`panel/forms.py`](c:\Users\sidne\OneDrive\Desktop\base_django\panel\forms.py): fachada compatível para os formulários do painel
- [`templates/base.html`](c:\Users\sidne\OneDrive\Desktop\base_django\templates\base.html): layout principal
- [`.github/workflows/ci.yml`](c:\Users\sidne\OneDrive\Desktop\base_django\.github\workflows\ci.yml): pipeline de validação contínua

## Estado atual e limitações

- a página de entrada do módulo em [`templates/module_page.html`](c:\Users\sidne\OneDrive\Desktop\base_django\templates\module_page.html) continua genérica, mas agora já exibe metadados úteis do módulo enquanto a área final ainda está em preparação
- o sidebar autenticado reutiliza a mesma estrutura agrupada de módulos do dashboard via [`core/context_processors.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\context_processors.py) e [`core/navigation.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\navigation.py), evitando recalcular a navegação duas vezes no mesmo request
- os testes agora vivem em [`core/tests`](c:\Users\sidne\OneDrive\Desktop\base_django\core\tests) e [`panel/tests`](c:\Users\sidne\OneDrive\Desktop\base_django\panel\tests), mas ainda faltam mais cenários de erro, edição e paridade HTML/API
- o painel agora já possui CRUD HTML para módulos com ativação segura e exclusão protegida, mas ainda não cobre API JSON equivalente
- a API do painel agora cobre usuários, grupos e módulos; os próximos ganhos de paridade passam a ser cenários de erro, auditoria e fluxos mais avançados

## Próximos passos sugeridos

- evoluir os módulos iniciais além de `Usuários` e `Grupos`
- ampliar a cobertura para erros de validação, `403`, redirects e fluxos de edição
