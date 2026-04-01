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

## Últimos Commits Relevantes

- `13f3e09` `refactor(core): split models by domain`
- `4a22c4f` `refactor(apps): split core and panel by domain`
- `054aee9` `refactor(api): reorganize core and panel api packages`
- `d6aca54` `feat(api): standardize v1 responses and docs`
- `8491f92` `feat(api): add versioned openapi docs and request ids`

## Última Validação

Executado após a separação de `core/models.py`:

- `python manage.py check`
- `python manage.py test core.tests panel.tests`

Resultado:

- `check` ok
- `36` testes passando

## Worktree Atual

- o único arquivo local fora do Git é este `CONTINUACAO.md`

## Próximo Passo

Separar os testes conforme convenção:

- `core/tests.py` -> `core/tests/`
- `panel/tests.py` -> `panel/tests/`

Estrutura sugerida:

- `core/tests/test_account.py`
- `core/tests/test_admin.py`
- `core/tests/test_audit.py`
- `core/tests/test_api_access.py`
- `core/tests/test_api_operational.py`
- `core/tests/test_auth.py`
- `core/tests/test_models.py`
- `panel/tests/test_api.py`
- `panel/tests/test_forms.py`

Depois disso, validar com:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test core.tests panel.tests
```

## Próximos Cortes de Arquitetura

### Core

Arquivos da raiz que ainda valem refactor depois da pasta `tests/`:

- `core/admin.py`
  - dividir em admin de módulo, auditoria e usuário
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
- o próximo trabalho confirmado é a separação dos testes em pasta `tests/`
- o SQLite dentro do OneDrive já apresentou `disk I/O error` em etapas anteriores de migration; se isso voltar, revisar o uso do banco dentro da pasta sincronizada
