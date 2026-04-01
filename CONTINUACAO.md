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
  - `core/admin/users.py`

## Últimos Commits Relevantes

- `13f3e09` `refactor(core): split models by domain`
- `4a22c4f` `refactor(apps): split core and panel by domain`
- `054aee9` `refactor(api): reorganize core and panel api packages`
- `d6aca54` `feat(api): standardize v1 responses and docs`
- `8491f92` `feat(api): add versioned openapi docs and request ids`

## Última Validação

Executado após a separação de `core/tests.py`, `panel/tests.py` e `core/admin.py`:

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
- `core/tests/` criado
- `panel/tests/` criado
- `core/admin/` criado
- `CONTINUACAO.md` atualizado

Observação:

- existe uma alteração local em `.gitignore` que não faz parte desta etapa; tratar com cuidado antes de qualquer commit

## Próximo Passo

Próximo corte recomendado em `core/`:

- dividir `core/audit.py`
  - separar contexto de request/auditoria
  - separar snapshot e sanitização
  - separar criação de log e helpers de serialização

Validação mínima depois desse corte:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test core.tests panel.tests
```

## Próximos Cortes de Arquitetura

### Core

Arquivos da raiz que ainda valem refactor depois da pasta `tests/` e `admin/`:

- `core/audit.py`
  - dividir contexto, snapshot/sanitização e criação de log
- `core/middleware.py`
  - dividir auth da API, request id, auditoria e rate limit
- `core/signals.py`
  - dividir sinais de modelo, M2M e autenticação

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
- `core/tests.py`, `panel/tests.py` e `core/admin.py` não existem mais; a convenção agora é por pacote
- o próximo trabalho sugerido é a separação de `core/audit.py`
- o SQLite dentro do OneDrive já apresentou `disk I/O error` em etapas anteriores de migration; se isso voltar, revisar o uso do banco dentro da pasta sincronizada
