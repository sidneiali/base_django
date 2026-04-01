# Continuação da Base

## Resumo Rápido

Estado atual da arquitetura:

- `core/views.py` já foi quebrado por domínio em:
  - `core/account/`
  - `core/auth/`
  - `core/docs/`
  - `core/errors/`
  - `core/web/`
- `panel/views.py` e `panel/forms.py` já foram quebrados por domínio em:
  - `panel/users/`
  - `panel/groups/`
- `core/models.py` já foi separado e commitado em `13f3e09`:
  - `core/models/__init__.py`
  - `core/models/ui.py`
  - `core/models/audit.py`
  - `core/models/api.py`
  - `core/models/modules.py`
- a API já está organizada em:
  - `core/api/`
  - `panel/api/`
- os testes já foram separados em pacote:
  - `core/tests/`
  - `panel/tests/`
- o admin do `core` já foi separado em pacote:
  - `core/admin/__init__.py`
  - `core/admin/modules.py`
  - `core/admin/audit.py`
  - `core/admin/users/__init__.py`
  - `core/admin/users/forms.py`
  - `core/admin/users/admin.py`
- a auditoria transversal do `core` já foi separada em pacote:
  - `core/audit/__init__.py`
  - `core/audit/context.py`
  - `core/audit/snapshots.py`
  - `core/audit/logging.py`
- os middlewares do `core` já foram separados em pacote:
  - `core/middleware/__init__.py`
  - `core/middleware/paths.py`
  - `core/middleware/api_auth.py`
  - `core/middleware/request_id.py`
  - `core/middleware/audit.py`
  - `core/middleware/rate_limit.py`
- os sinais do `core` já foram separados em pacote:
  - `core/signals/__init__.py`
  - `core/signals/shared.py`
  - `core/signals/models.py`
  - `core/signals/m2m.py`
  - `core/signals/auth.py`

## Últimos Commits Relevantes

- `13f3e09` `refactor(core): split models by domain`
- `4a22c4f` `refactor(apps): split core and panel by domain`
- `054aee9` `refactor(api): reorganize core and panel api packages`
- `d6aca54` `feat(api): standardize v1 responses and docs`
- `8491f92` `feat(api): add versioned openapi docs and request ids`

## Última Validação

Executado após a separação de `core/tests.py`, `panel/tests.py`, `core/admin.py`, `core/audit.py`, `core/middleware.py` e `core/signals.py`:

- `uv run --extra dev ruff check config core panel`
- `.\.venv\Scripts\python.exe manage.py check`
- `.\.venv\Scripts\python.exe manage.py test core.tests panel.tests`

Resultado:

- `ruff` ok
- `check` ok
- `36` testes passando
- discovery funcionando com:
  - `core/tests/test_account.py`
  - `core/tests/test_admin.py`
  - `core/tests/test_api_access.py`
  - `core/tests/test_api_operational.py`
  - `core/tests/test_audit.py`
  - `core/tests/test_auth.py`
  - `core/tests/test_models.py`
  - `panel/tests/test_api.py`
  - `panel/tests/test_forms.py`

## Worktree Atual

Alterações locais esperadas desta etapa:

- `core/tests.py` removido
- `panel/tests.py` removido
- `core/admin.py` removido
- `core/audit.py` removido
- `core/middleware.py` removido
- `core/signals.py` removido
- `core/tests/` criado
- `panel/tests/` criado
- `core/admin/` criado
- `core/audit/` criado
- `core/middleware/` criado
- `core/signals/` criado
- `CONTINUACAO.md` atualizado

Observação:

- existe uma alteração local em `.gitignore` que não faz parte desta etapa; tratar com cuidado antes de qualquer commit

## Próximo Passo

Os cortes estruturais principais listados para `core/` foram concluídos.

Próximas opções naturais:

- revisar `panel/helpers.py` e decidir se ele deve ser renomeado para algo mais específico
- iniciar uma feature nova sobre a base já modularizada
- revisar se vale separar `core/forms.py`, `core/views.py` ou `panel/forms.py` além do nível atual

## Próximos Cortes de Arquitetura

### Core

Os principais arquivos grandes da raiz já foram quebrados.

Arquivos que podem ficar como estão por enquanto:

- `core/forms.py`
- `core/views.py`
- `core/urls.py`
- `core/preferences.py`
- `core/services.py`
- `core/context_processors.py`
- `core/htmx.py`

### Panel

Depois da pasta `tests/`, `panel/` está bem mais estável.

Arquivos que podem ficar como estão por enquanto:

- `panel/forms.py`
- `panel/views.py`
- `panel/constants.py`
- `panel/models.py`
- `panel/admin.py`
- `panel/urls.py`

Observação sobre `panel/helpers.py`:

- o ideal não é mover automaticamente para `utils/`
- primeiro vale decidir a responsabilidade real dele
- se continuar ligado a formulário/apresentação, o melhor é renomear para algo mais específico e manter perto do domínio

## Observações

- `core/models.py` não está mais pendente
- `core/tests.py`, `panel/tests.py`, `core/admin.py`, `core/audit.py`, `core/middleware.py` e `core/signals.py` não existem mais; a convenção agora é por pacote
- a base estrutural do `core` está bem mais modular e pronta para features novas
- o SQLite dentro do OneDrive já apresentou `disk I/O error` em etapas anteriores de migration; se isso voltar, revisar o uso do banco dentro da pasta sincronizada
