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
python -m pip install django django-bootstrap5
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
- `APP_ENV=production`: `DEBUG=False` por padrão, exige `SECRET_KEY` e `ALLOWED_HOSTS`, usa `STATIC_ROOT` e SMTP por padrão

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
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=/var/app/db.sqlite3
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

## Visão geral

O sistema possui dois apps principais:

- `core`: dashboard, cadastro de módulos, montagem de acesso por permissão e páginas base
- `panel`: gestão de usuários e grupos sem depender diretamente do admin do Django

Fluxo principal:

1. o usuário faz login
2. o dashboard consulta os módulos ativos
3. cada módulo pode ou não exigir uma permissão do Django
4. se o usuário tiver acesso, entra na rota do módulo
5. se não tiver, recebe `403`

## Estrutura do projeto

```text
config/     configuração global, settings e rotas principais
core/       model Module, dashboard, serviços e admin de módulos
panel/      formulários e telas para usuários e grupos
templates/  layout base, login, dashboard, páginas e partials
static/     CSS customizado
```

## Modelo central: Module

O model [`core/models.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\models.py) define os módulos exibidos no dashboard.

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

## Seed inicial dos módulos

Para bootstrap local, o projeto possui um comando idempotente para criar ou atualizar
os módulos iniciais do dashboard:

```bash
uv run python manage.py seed_initial_modules
```

Hoje o seed cria o conjunto mínimo de módulos internos:

- `Usuários`
- `Grupos`

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
- `/painel/grupos/`: listagem de grupos
- `/painel/grupos/novo/`: criação de grupo
- `/painel/grupos/<id>/editar/`: edição de grupo
- `/admin/`: admin do Django

## Painel de usuários e grupos

O app [`panel`](c:\Users\sidne\OneDrive\Desktop\base_django\panel) oferece uma camada mais amigável para administração:

- usuários comuns podem ser criados e editados sem virar `staff` ou `superuser`
- grupos protegidos não aparecem para edição: `Superadmin`, `Root` e `Infra`
- permissões de apps internos do Django como `admin`, `contenttypes` e `sessions` não são exibidas no formulário de grupos
- os nomes de permissões são traduzidos para uma leitura mais amigável em português

Permissões exigidas por tela:

- usuários: `auth.view_user`, `auth.add_user`, `auth.change_user`
- grupos: `auth.view_group`, `auth.add_group`, `auth.change_group`

## Arquivos importantes

- [`config/settings/base.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\base.py): configuração compartilhada entre ambientes
- [`config/settings/development.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\development.py): defaults locais
- [`config/settings/production.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings\production.py): defaults de produção
- [`config/urls.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\urls.py): composição das rotas do projeto
- [`core/services.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\services.py): monta os módulos visíveis para o usuário
- [`panel/forms.py`](c:\Users\sidne\OneDrive\Desktop\base_django\panel\forms.py): regras de formulário e tradução das permissões
- [`templates/base.html`](c:\Users\sidne\OneDrive\Desktop\base_django\templates\base.html): layout principal

## Estado atual e limitações

- o `README` agora descreve a base, mas o projeto ainda está em fase inicial
- a página de entrada do módulo em [`templates/module_page.html`](c:\Users\sidne\OneDrive\Desktop\base_django\templates\module_page.html) é genérica e serve como placeholder até cada app ter sua própria área
- o sidebar autenticado reutiliza a mesma estrutura agrupada de módulos do dashboard via [`core/context_processors.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\context_processors.py)
- os testes agora vivem em [`core/tests`](c:\Users\sidne\OneDrive\Desktop\base_django\core\tests) e [`panel/tests`](c:\Users\sidne\OneDrive\Desktop\base_django\panel\tests), mas a cobertura ainda é parcial
- a separação entre desenvolvimento e produção existe, mas o banco padrão ainda continua em `sqlite3` até a infraestrutura final ser definida

## Próximos passos sugeridos

- evoluir o banco e a estratégia de deploy de produção além do `sqlite3`
