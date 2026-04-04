# Avaliação de Soft Delete

## Conclusão

O projeto **não deve adotar um `SoftDeleteModel` global neste momento**.

A fundação atual já cobre a principal necessidade de rastreabilidade com:

- trilha de auditoria append-only em [core/models/audit.py](../core/models/audit.py)
- eventos explícitos de exclusão via sinais em [core/signals/models.py](../core/signals/models.py)
- estados operacionais mais seguros como inativação, revogação e bloqueios de exclusão em vez de remoção indiscriminada

Para a base atual, o custo arquitetural de um soft delete transversal é maior do que o benefício prático.

## Principais motivos

### 1. Usuários e grupos não são models próprios da aplicação

O sistema usa diretamente `auth.User` e `auth.Group` do Django ao longo do painel, da API e dos formulários, por exemplo em [panel/users/services.py](../panel/users/services.py) e [panel/groups/services.py](../panel/groups/services.py).

Isso impede um `SoftDeleteModel` base homogêneo para as entidades mais sensíveis do projeto. Para aplicar soft delete nesses objetos, seria necessário:

- substituir o modelo padrão de usuário por um custom user model
- criar uma trilha equivalente para grupos, fora do `auth.Group` padrão
- revisar autenticação, permissões, admin, E2E, APIs e migrações

Esse tipo de mudança é estrutural e não cabe como refatoração incremental de baixo risco.

### 2. A auditoria já é um ledger histórico e não combina com soft delete

O [AuditLog](../core/models/audit.py) funciona como trilha histórica append-only. Hoje a exclusão física de uma entidade monitorada gera um evento `delete` antes da remoção real, por meio de [core/signals/models.py](../core/signals/models.py).

Se o projeto migrasse para soft delete nas entidades monitoradas:

- a semântica atual de `post_delete` deixaria de representar exclusão real
- vários eventos passariam a virar `update` em vez de `delete`
- a leitura operacional da auditoria ficaria menos clara
- a camada de testes de paridade e auditoria teria de ser reescrita

Para o próprio `AuditLog`, soft delete também não faz sentido. Quando houver necessidade de retenção, o caminho correto é política de arquivamento ou purge controlado, não esconder linhas da trilha.

### 3. Módulos dependem de unicidade e do seed canônico

O model [Module](../core/models/modules.py) depende de `name` e `slug` únicos e tem relação direta com o catálogo canônico e com os comandos de restauração e seed.

Um soft delete em módulos exigiria resolver:

- colisão de unicidade em `slug` e `name`
- comportamento dos comandos de seed e restore
- filtragem obrigatória em navegação, dashboard, sidebar, APIs e forms
- distinção entre módulo inativo e módulo excluído logicamente

Hoje a base já tem a noção certa para esse domínio: `is_active` para desligamento operacional e exclusão física só quando o módulo é realmente descartável.

### 4. O domínio de acesso à API já tem estado próprio

Em [core/models/api.py](../core/models/api.py), os objetos operacionais já possuem uma semântica mais adequada que soft delete:

- `ApiAccessProfile.api_enabled`
- `ApiToken.revoked_at`

Ou seja, o sistema já usa transições de estado quando o objetivo é preservar histórico sem destruir a identidade do registro.

### 5. O custo transversal seria alto demais

Hoje há exclusão física espalhada por serviços HTML, endpoints JSON, comandos de manutenção e fluxos operacionais, incluindo:

- usuários em [panel/users/services.py](../panel/users/services.py) e [panel/api/users.py](../panel/api/users.py)
- grupos em [panel/groups/services.py](../panel/groups/services.py) e [panel/api/groups.py](../panel/api/groups.py)
- módulos em [panel/modules/services.py](../panel/modules/services.py) e [panel/api/modules.py](../panel/api/modules.py)
- limpeza operacional do Axes em [panel/login_security/views.py](../panel/login_security/views.py)
- comandos de restauração de módulos em [core/management/commands/restore_initial_modules.py](../core/management/commands/restore_initial_modules.py)

Introduzir soft delete de forma global exigiria revisar:

- managers padrão
- querysets de leitura
- filtros de API
- serializers e OpenAPI
- sinais e auditoria
- comandos administrativos
- testes HTML, API, auditoria e E2E

Isso reabriria uma parte grande da base sem um ganho proporcional hoje.

## Recomendação para a base atual

Manter a estratégia atual:

- **exclusão física** quando o registro realmente deve sair do sistema
- **auditoria explícita** do evento de exclusão
- **inativação ou revogação** quando o domínio precisa preservar a identidade do objeto

## Quando revisitar

Vale revisitar soft delete apenas quando surgir uma entidade **própria do domínio** com necessidade real de:

- restauração após exclusão acidental
- retenção regulatória do registro “ativo vs. removido”
- ocultação operacional sem remoção física

Nesse cenário, a recomendação é abrir um piloto **pontual**, não global:

1. aplicar o mixin somente a models first-party do projeto
2. manter managers separados para leitura ativa e leitura total
3. adaptar auditoria explicitamente para o novo significado de exclusão lógica
4. evitar começar por `auth.User`, `auth.Group` ou `AuditLog`

## Próximo passo recomendado

O próximo ganho mais alinhado à base atual é **política de retenção da auditoria**, com purge/arquivamento controlado, em vez de soft delete transversal.
