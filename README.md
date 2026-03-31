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

Depois acesse:

- `http://127.0.0.1:8000/login/`
- `http://127.0.0.1:8000/admin/`

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

Os módulos são gerenciados pelo admin do Django em [`core/admin.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\admin.py).

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

- [`config/settings.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\settings.py): apps instalados, templates, idioma, fuso e autenticação
- [`config/urls.py`](c:\Users\sidne\OneDrive\Desktop\base_django\config\urls.py): composição das rotas do projeto
- [`core/services.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\services.py): monta os módulos visíveis para o usuário
- [`panel/forms.py`](c:\Users\sidne\OneDrive\Desktop\base_django\panel\forms.py): regras de formulário e tradução das permissões
- [`templates/base.html`](c:\Users\sidne\OneDrive\Desktop\base_django\templates\base.html): layout principal

## Estado atual e limitações

- o `README` agora descreve a base, mas o projeto ainda está em fase inicial
- a página de entrada do módulo em [`templates/module_page.html`](c:\Users\sidne\OneDrive\Desktop\base_django\templates\module_page.html) é genérica e serve como placeholder até cada app ter sua própria área
- o context processor [`core/context_processors.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\context_processors.py) ainda devolve `modules` vazio; hoje o dashboard exibe os módulos corretamente, mas o sidebar ainda não usa a mesma fonte
- os arquivos de teste em [`core/tests.py`](c:\Users\sidne\OneDrive\Desktop\base_django\core\tests.py) e [`panel/tests.py`](c:\Users\sidne\OneDrive\Desktop\base_django\panel\tests.py) ainda estão sem cobertura real
- `DEBUG=True` e `sqlite3` indicam configuração voltada para desenvolvimento local

## Próximos passos sugeridos

- sincronizar o sidebar com a mesma lógica do dashboard
- criar fixtures ou comando de seed para módulos iniciais
- adicionar testes para permissões, login e fluxo do painel
- separar configurações de desenvolvimento e produção
