# Estudo de Arquitetura Multiempresa

## Objetivo

Desenhar uma evolução do `base_django` para rodar em **um servidor central**, atendendo **múltiplas empresas** no mesmo sistema, com o contexto operacional orientado a:

- uma identidade global de usuário
- associação `1:N` entre usuário e empresas
- grupos, apps, permissões, auditoria, API e preferências atrelados à empresa ativa
- uma área própria para **gestão da empresa**
- uma área separada para **administração da plataforma**

## Leitura do estado atual

Hoje a base é essencialmente **single-tenant lógico**.

Os pontos centrais do estado atual são:

- o projeto usa `auth.User` e `auth.Group` diretamente em [panel/users/forms.py](../panel/users/forms.py), [panel/groups/forms.py](../panel/groups/forms.py) e [panel/admin_accounts/forms.py](../panel/admin_accounts/forms.py)
- preferências de interface são globais por usuário ou por grupo em [core/models/ui.py](../core/models/ui.py)
- acesso à API é global por usuário em [core/models/api.py](../core/models/api.py)
- módulos são um catálogo global em [core/models/modules.py](../core/models/modules.py)
- auditoria não possui `empresa_id`; o contexto atual é usuário, objeto, request e metadata em [core/models/audit.py](../core/models/audit.py)

Ou seja: hoje o sistema assume que o “universo de permissões e operação” é único.

## Conclusão principal

Para suportar **multiempresa real**, a melhor direção para esta base é:

- manter **um banco compartilhado com chave de empresa** nas entidades de domínio
- manter **usuário como identidade global**
- mover a maior parte do contexto operacional para uma camada de **membresia por empresa**
- separar com clareza o que é:
  - **global da plataforma**
  - **configurável por empresa**

Essa abordagem encaixa melhor no desenho atual do projeto do que tentar duplicar toda a estrutura por banco ou por schema.

## Recomendação de modelo

### 1. Identidade global + membresia por empresa

O usuário deve continuar sendo uma identidade global.

Modelo sugerido:

- `Company`
- `CompanyMembership`

Exemplo conceitual:

```python
class Company(models.Model):
    slug = models.SlugField(unique=True)
    legal_name = models.CharField(max_length=200)
    trade_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=32, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CompanyMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_company_admin = models.BooleanField(default=False)
    is_company_owner = models.BooleanField(default=False)
    job_title = models.CharField(max_length=120, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"],
                name="core_unique_company_membership",
            )
        ]
```

### Por que assim

Isso permite:

- um mesmo usuário operar em várias empresas
- trocar a empresa ativa no shell
- bloquear acesso por empresa sem apagar a identidade global
- auditar a operação por `usuário + empresa`

## Perfis recomendados

### Perfis da plataforma

São perfis globais, fora do contexto de uma empresa específica.

- `Platform Superadmin`
  - gerencia empresas
  - gerencia catálogo global de apps
  - gerencia suporte operacional da plataforma
  - pode atravessar tenants para suporte e auditoria
- `Platform Support`
  - consulta empresas, acessos, auditoria e saúde operacional
  - não altera billing ou políticas críticas sem permissão extra
- `Platform Auditor`
  - acesso somente leitura a contexto global

### Perfis por empresa

São perfis aplicados dentro da empresa ativa.

- `Company Owner`
  - maior autonomia dentro da empresa
  - define admins da empresa
  - aprova módulos/apps liberados para a empresa
- `Company Admin`
  - gerencia usuários, grupos e apps da empresa
  - gerencia permissões e API da empresa
- `Company Manager`
  - opera módulos com poder de gestão parcial
- `Company Operator`
  - usa os módulos liberados, sem governança estrutural
- `Company Auditor`
  - leitura de auditoria e trilhas operacionais da empresa
- `Company API Client`
  - uso de API restrito ao escopo da empresa

## O que deve ser global e o que deve ser por empresa

### Global da plataforma

Esses elementos não devem ser duplicados por empresa:

- identidade do usuário
- catálogo canônico de módulos/apps
- catálogo técnico de permissões do sistema
- configuração base de infraestrutura
- observabilidade da plataforma

### Atrelado à empresa

Esses elementos devem passar a ser resolvidos pelo contexto da empresa ativa:

- participação do usuário
- perfil efetivo do usuário
- grupos da empresa
- apps habilitados para a empresa
- permissões operacionais da empresa
- preferências de interface com efeito operacional
- tokens e permissões de API
- auditoria funcional
- qualquer entidade de negócio futura

## Grupos e permissões

### Problema do estado atual

Hoje o projeto usa `auth.Group` diretamente.

Isso é ruim para multiempresa porque `Group` é global. Se uma empresa criar um grupo chamado `Financeiro`, esse grupo passa a existir no banco inteiro, não só naquele tenant.

### Direção recomendada

Não usar `auth.Group` como grupo de negócio multiempresa.

Criar algo como:

- `CompanyGroup`
- `CompanyGroupPermission`
- `CompanyGroupMembership`

Exemplo conceitual:

```python
class CompanyGroup(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "slug"],
                name="core_unique_company_group_slug",
            )
        ]
```

### Regra importante

O sistema pode continuar usando permissões técnicas do Django como catálogo global, mas a **atribuição efetiva** precisa ser feita por empresa.

Ou seja:

- permissão técnica continua global: `auth.view_user`, `core.view_module`
- vínculo dessa permissão com uma pessoa passa a ser contextual: “nesta empresa, esta membresia possui esta permissão”

## Apps e módulos

### Problema do estado atual

Hoje [core/models/modules.py](../core/models/modules.py) descreve um catálogo global e também o estado operacional de visibilidade.

Isso funciona para single-tenant, mas não para várias empresas com combinações diferentes de apps.

### Direção recomendada

Separar:

- `Module`: catálogo global
- `CompanyModule`: habilitação do módulo para uma empresa

Exemplo conceitual:

```python
class CompanyModule(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=True)
    show_in_sidebar = models.BooleanField(default=True)
    show_in_dashboard = models.BooleanField(default=True)
    menu_group_override = models.CharField(max_length=100, blank=True)
    order_override = models.PositiveIntegerField(null=True, blank=True)
```

### Efeito prático

Com isso:

- o catálogo global continua único
- cada empresa escolhe quais apps usa
- o shell mostra só o que está habilitado na empresa ativa

## Preferências e políticas

Hoje as preferências em [core/models/ui.py](../core/models/ui.py) são globais por usuário ou por grupo.

Em multiempresa, o ideal é mover isso para:

- `CompanyUserPreference` ou `CompanyMembershipPreference`
- `CompanyGroupPreference`

Porque o mesmo usuário pode precisar de:

- refresh diferente por empresa
- timeout de sessão diferente por empresa
- política operacional diferente por tenant

## API

### Problema do estado atual

O acesso à API em [core/models/api.py](../core/models/api.py) é global por usuário.

Isso não é suficiente em um cenário multiempresa porque:

- o mesmo usuário pode ter acesso à API em uma empresa e não em outra
- as permissões CRUD precisam ser avaliadas por empresa
- o token precisa carregar ou resolver o tenant

### Direção recomendada

Trocar o eixo de autenticação de:

- `ApiAccessProfile -> user`

para algo como:

- `CompanyApiAccessProfile -> membership`
- `CompanyApiToken -> membership`
- `CompanyApiResourcePermission -> company_api_access_profile`

### Regra recomendada

Todo token de API precisa estar atrelado a:

- usuário
- empresa
- membresia

Assim a autorização deixa de ser só “quem é a pessoa” e passa a ser “quem é a pessoa **nesta empresa**”.

## Auditoria

### Problema do estado atual

O [AuditLog](../core/models/audit.py) hoje não tem `company`.

Num ambiente multiempresa central, isso vira um problema porque:

- filtros por empresa ficam caros ou indiretos
- trilhas operacionais de tenants se misturam
- suporte e auditoria por empresa ficam mais difíceis

### Direção recomendada

Adicionar no mínimo:

- `company`
- `membership`

Exemplo conceitual:

```python
company = models.ForeignKey(
    "core.Company",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="audit_logs",
)
membership = models.ForeignKey(
    "core.CompanyMembership",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="audit_logs",
)
```

### Resultado

Isso permite:

- auditoria por empresa
- auditoria por operador dentro da empresa
- trilha global da plataforma separada da trilha do tenant

## Contexto de request

Para multiempresa funcionar de forma consistente, o request precisa carregar:

- `request.user`
- `request.company`
- `request.membership`

### Como resolver a empresa ativa

A recomendação para esta base é começar com:

- empresa ativa armazenada em sessão
- seletor visível no shell autenticado

E suportar no futuro:

- subdomínio por empresa
- header de tenant para API

## Ambientes do produto

## 1. Ambiente da plataforma

Área para operação central.

Sugestão:

- `/plataforma/empresas/`
- `/plataforma/usuarios/`
- `/plataforma/auditoria/`
- `/plataforma/modulos/`

Responsabilidades:

- criar, ativar, inativar e suspender empresas
- gerenciar catálogo global de apps
- suporte operacional
- observabilidade e auditoria globais

## 2. Ambiente da empresa

Área operacional do tenant.

Sugestão:

- continuar usando o shell atual como base
- sempre com uma empresa ativa selecionada

Responsabilidades:

- gerir usuários da empresa
- gerir grupos/perfis da empresa
- gerir apps habilitados da empresa
- gerir API da empresa
- gerir auditoria da empresa

## 3. Tela de gestão da empresa

Esse é o “ambiente para gerir a empresa” pedido.

Sugestão de escopo:

- dados cadastrais da empresa
- branding básico
- status operacional
- admins da empresa
- módulos/apps habilitados
- políticas de sessão e API
- limites ou plano

Nome sugerido:

- `Empresa`
- `Configurações da empresa`
- `Administração da empresa`

## Estratégia de migração recomendada

### Fase 1. Introduzir a raiz multiempresa

- criar `Company`
- criar `CompanyMembership`
- criar middleware/contexto de empresa ativa
- criar seletor de empresa no shell

### Fase 2. Mover o painel para o contexto de empresa

- filtrar usuários pela empresa ativa
- introduzir grupos por empresa
- mover preferências de usuário/grupo para escopo de empresa

### Fase 3. Mover apps e navegação

- manter `Module` global
- criar `CompanyModule`
- fazer dashboard/sidebar respeitarem empresa ativa

### Fase 4. Mover API e auditoria

- company-aware token
- company-aware permissions
- company-aware audit log

### Fase 5. Abrir a área da plataforma

- CRUD de empresas
- gestão de admins da empresa
- governança global de módulos e suporte

## Decisões importantes

### 1. Não usar `Group` global como grupo da empresa

Para multiempresa real, isso gera conflito conceitual e operacional.

### 2. Não duplicar `User` por empresa

O melhor encaixe para esta base é:

- uma identidade global
- várias membresias

### 3. Não atrelar tudo fisicamente à empresa desde o primeiro dia

Nem tudo precisa ter `company_id`.

A regra certa é:

- catálogo global permanece global
- operação do tenant recebe `company_id`

### 4. Separar “admin da plataforma” de “admin da empresa”

Misturar esses dois perfis no mesmo painel tende a gerar acoplamento, risco operacional e regras confusas.

## Impacto nos arquivos atuais

Os hotspots mais afetados por essa evolução seriam:

- [panel/users/forms.py](../panel/users/forms.py)
- [panel/groups/forms.py](../panel/groups/forms.py)
- [panel/admin_accounts/forms.py](../panel/admin_accounts/forms.py)
- [core/preferences.py](../core/preferences.py)
- [core/models/api.py](../core/models/api.py)
- [core/models/modules.py](../core/models/modules.py)
- [core/models/audit.py](../core/models/audit.py)
- [core/navigation.py](../core/navigation.py)
- [panel/api/users.py](../panel/api/users.py)
- [panel/api/groups.py](../panel/api/groups.py)
- [panel/api/modules.py](../panel/api/modules.py)

## Recomendação final

Se o sistema realmente vai operar em servidor central para várias empresas, a recomendação é oficializar a arquitetura como:

- **multiempresa por banco compartilhado**
- **usuário global**
- **membresia por empresa**
- **grupos, API, preferências e auditoria contextualizados por empresa**
- **duas superfícies administrativas**:
  - plataforma
  - empresa

Essa é a direção que melhor preserva a base atual e, ao mesmo tempo, abre caminho para crescimento consistente.

## Próximo passo recomendado

Abrir um lote de arquitetura com:

1. `Company`
2. `CompanyMembership`
3. `request.company`
4. seletor de empresa no shell
5. área inicial de gestão da empresa

Esse é o menor corte que já muda a fundação na direção correta.
