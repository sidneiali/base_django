# Estudo de Arquitetura Multiempresa

## Objetivo

Desenhar uma evolucao do `base_django` para rodar em **um servidor central**, atendendo
**multiplas empresas** no mesmo sistema, com a seguinte regra de produto:

- usuarios comuns pertencem a **uma unica empresa**
- somente `superadmin` atravessa empresas
- usuarios, grupos, apps, API, auditoria e contexto operacional ficam atrelados a
  empresa
- o produto precisa de uma area propria para **gestao da empresa**
- a plataforma central precisa de uma area separada para **administracao global**

## Mudanca de premissa

A versao anterior deste estudo partia de:

- usuario global
- membresia por empresa

Depois da definicao funcional mais recente, essa ja nao e a melhor direcao.

Se a regra do produto e que cada conta comum nasce dentro da sua empresa e nao deve ser
uma identidade global compartilhada, a arquitetura alvo precisa refletir isso desde a
fundacao.

## Leitura do estado atual

Hoje a base e essencialmente **single-tenant logico**.

Os pontos centrais do estado atual sao:

- o projeto usa `auth.User` e `auth.Group` diretamente em
  [panel/users/forms.py](../panel/users/forms.py),
  [panel/groups/forms.py](../panel/groups/forms.py) e
  [panel/admin_accounts/forms.py](../panel/admin_accounts/forms.py)
- o login publico ja usa e-mail como identificador principal em
  [core/auth/forms.py](../core/auth/forms.py) e
  [core/auth/views.py](../core/auth/views.py)
- preferencias de interface sao globais por usuario ou por grupo em
  [core/models/ui.py](../core/models/ui.py)
- acesso a API e global por usuario em [core/models/api.py](../core/models/api.py)
- modulos sao um catalogo global em [core/models/modules.py](../core/models/modules.py)
- auditoria nao possui `company_id`; o contexto atual e usuario, objeto, request e
  metadata em [core/models/audit.py](../core/models/audit.py)

Ou seja: hoje o sistema assume que o universo de operacao e unico.

## Conclusao principal

Para suportar **multiempresa real** nessa nova regra de produto, a melhor direcao para a
base deixa de ser "usuario global + membresia" e passa a ser:

- **banco compartilhado com chave de empresa**
- **usuarios comuns pertencendo a uma unica empresa**
- **superadmin como excecao global de plataforma**
- **modulos, grupos, API, auditoria e configuracoes resolvidos pela empresa da conta**

Essa direcao combina melhor com a regra de negocio que voce descreveu e simplifica o
shell autenticado: usuarios comuns nao precisam trocar de empresa ativa.

## Recomendacao de modelo

### 1. Company como raiz do tenant

O primeiro pilar continua sendo uma entidade `Company`.

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
```

### 2. Usuario atrelado a empresa

O usuario comum deve nascer com `company` obrigatoria.

A recomendacao alvo e adotar um **usuario customizado** cedo, porque o projeto ja
depende muito de `auth.User` e esse sera o corte mais sensivel de toda a migracao.

Modelo conceitual:

```python
class User(AbstractUser):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "email"],
                name="core_unique_company_user_email",
            ),
            models.UniqueConstraint(
                fields=["company", "username"],
                name="core_unique_company_user_username",
            ),
        ]
```

### Regra operacional

- conta comum: `company` obrigatoria
- `superadmin`: conta global de plataforma, sem empresa ou com escopo explicito de
  plataforma
- usuario comum nao troca de tenant; o tenant vem da propria conta

### Ponte de migracao possivel

Se o custo de trocar `AUTH_USER_MODEL` for alto demais logo de inicio, uma ponte
temporaria seria:

- manter `auth.User` por um ciclo
- criar `CompanyUserProfile` `1:1`
- tratar esse profile como obrigatorio para qualquer conta nao-superuser

Mas isso deve ser visto como **transicao**, nao como estado final ideal.

## Login e identidade

Esse ponto muda bastante com a nova premissa.

Se os usuarios deixam de ser globais, o login nao deveria depender para sempre de uma
busca global por e-mail.

### Decisao critica

Voce precisa escolher entre dois modelos:

#### Opcao A. E-mail globalmente unico

Vantagens:

- preserva o login atual por e-mail
- migracao inicial mais simples

Custos:

- continua impondo uma identidade global no dado mais sensivel da conta
- a mesma pessoa nao pode ter duas contas com o mesmo e-mail em empresas diferentes

#### Opcao B. Login company-aware

Exemplos:

- subdominio por empresa
- slug da empresa + e-mail
- empresa escolhida antes do login

Vantagens:

- combina melhor com a regra "usuario pertence a empresa"
- permite `email` unico por empresa, nao por plataforma inteira
- reduz a sensacao de identidade global escondida

Custos:

- aumenta a complexidade do login
- exige revisao dos convites e da recuperacao de senha

### Recomendacao

Se o objetivo e levar a serio o modelo "usuario da empresa", a direcao arquitetural mais
coerente e:

- **login company-aware**
- `email` unico por empresa

Se o projeto quiser um primeiro corte menos invasivo, pode comecar com e-mail globalmente
unico e tratar isso como restricao transitiva.

## Perfis recomendados

### Plataforma

Pelo requisito atual, o unico perfil global necessario deve ser:

- `Platform Superadmin`
  - cria, ativa, inativa e suspende empresas
  - gerencia catalogo global de apps
  - atravessa tenants para suporte e governanca
  - acessa trilhas globais de observabilidade

Se no futuro surgirem perfis globais adicionais como suporte ou auditoria, eles devem ser
criados de forma explicita, nunca herdados acidentalmente das contas de empresa.

### Empresa

Perfis efetivos dentro da empresa:

- `Company Owner`
- `Company Admin`
- `Company Manager`
- `Company Operator`
- `Company Auditor`
- `Company API Client`

Esses perfis nao atravessam empresas.

## O que fica global e o que fica por empresa

### Global da plataforma

Esses elementos continuam globais:

- cadastro de empresas
- catalogo canonico de modulos
- catalogo tecnico de permissoes
- observabilidade global da plataforma
- configuracoes de infraestrutura
- contas `superadmin`

### Atrelado a empresa

Esses elementos passam a ser resolvidos pelo `company_id` da conta:

- usuarios comuns
- grupos operacionais
- preferencias de interface
- politicas de sessao
- modulos habilitados
- tokens e permissoes de API
- auditoria funcional
- configuracoes da empresa
- qualquer entidade de negocio futura

## Grupos e permissoes

### Problema do estado atual

Hoje o projeto usa `auth.Group` diretamente, e `Group.name` e global.

Isso conflita com multiempresa porque:

- duas empresas podem querer um grupo `Financeiro`
- a atribuicao de permissoes passa a exigir escopo de empresa

### Direcao recomendada

Como `auth.Group` esta profundamente integrado ao ecossistema Django e nao e swappable,
a melhor abordagem para esta base e separar:

- **grupo tecnico** do Django
- **grupo de negocio da empresa**

Exemplo conceitual:

```python
class CompanyGroup(models.Model):
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    auth_group = models.OneToOneField(Group, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=120)
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

### Efeito pratico

Com isso:

- a UI opera em `CompanyGroup`
- o backend ainda reaproveita o motor de permissao do Django
- nomes iguais podem existir em empresas diferentes

## Apps e modulos

### Problema do estado atual

Hoje [core/models/modules.py](../core/models/modules.py) mistura catalogo global com
visibilidade operacional.

Para multiempresa, o catalogo deve continuar global, mas a habilitacao precisa ser por
empresa.

### Direcao recomendada

Separar:

- `Module`: catalogo global
- `CompanyModule`: habilitacao/configuracao daquele modulo para a empresa

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

## Preferencias e politicas

Esse ponto fica mais simples do que no modelo com membresia.

Como cada usuario comum pertence a uma unica empresa:

- preferencias por usuario podem continuar coladas ao usuario, desde que o usuario ja
  seja company-bound
- preferencias por grupo precisam acompanhar o grupo da empresa
- politicas da empresa merecem um lugar proprio, por exemplo `CompanyPolicy`

Exemplos de configuracoes por empresa:

- tempo maximo de sessao inativa
- branding basico
- defaults de API
- configuracoes de notificacao

## API

### Problema do estado atual

Hoje [core/models/api.py](../core/models/api.py) atrela acesso a API diretamente ao
usuario de forma global.

### Direcao recomendada

No modelo company-owned user, existem dois niveis possiveis:

- **resolucao por derivacao**: o perfil da API continua ligado ao usuario e a empresa vem
  de `user.company`
- **resolucao explicita**: token e perfil tambem guardam `company`

### Recomendacao

Para esta base, a melhor direcao e guardar ambos:

- `user`
- `company`

Mesmo que `company` possa ser derivado do usuario, persisti-lo no token e no perfil:

- acelera filtros
- simplifica auditoria
- protege o historico se a conta mudar de estado

## Auditoria

### Problema do estado atual

O [AuditLog](../core/models/audit.py) nao possui `company`.

Num servidor central isso vira problema porque:

- tenants se misturam na trilha
- filtros por empresa ficam indiretos
- suporte e exportacao por empresa ficam caros

### Direcao recomendada

Adicionar no minimo:

- `company`
- eventualmente um snapshot simples do tenant no `metadata`

Exemplo conceitual:

```python
company = models.ForeignKey(
    "core.Company",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="audit_logs",
)
```

### Regra importante

Mesmo quando o ator puder ser resolvido por `actor.company`, ainda vale persistir
`company` diretamente no log para:

- manter consulta barata
- preservar o tenant mesmo se o usuario for removido ou alterado
- separar melhor auditoria de plataforma e auditoria da empresa

## Contexto de request

No modelo revisado, o request fica mais simples para usuarios comuns:

- `request.user`
- `request.company`

Sem seletor de tenant para a conta comum.

### Superadmin

Para `superadmin`, o produto pode oferecer:

- modo plataforma
- entrada pontual em uma empresa para suporte ou configuracao

Esse fluxo pode carregar um `request.target_company`, mas isso deve ser excecao
controlada, nao regra do shell inteiro.

## Ambientes do produto

## 1. Ambiente da plataforma

Area restrita ao `superadmin`.

Sugestao:

- `/plataforma/empresas/`
- `/plataforma/modulos/`
- `/plataforma/auditoria/`
- `/plataforma/observabilidade/`

Responsabilidades:

- criar e gerir empresas
- gerir o catalogo global de apps
- acompanhar saude global
- operar suporte de plataforma

## 2. Ambiente da empresa

Area operacional do tenant.

Sugestao:

- manter o shell atual como base
- usar a empresa da propria conta como contexto implicito

Responsabilidades:

- gerir usuarios da empresa
- gerir grupos da empresa
- gerir apps habilitados
- gerir API da empresa
- gerir auditoria da empresa
- gerir configuracoes da empresa

## 3. Tela de gestao da empresa

Esse e o ambiente pedido para gerir a empresa.

Escopo recomendado:

- dados cadastrais da empresa
- branding basico
- status operacional
- admins da empresa
- modulos/apps habilitados
- politicas de sessao
- politica de API
- limites ou plano

Nomes possiveis:

- `Empresa`
- `Configuracoes da empresa`
- `Administracao da empresa`

## Estrategia de migracao recomendada

### Fase 0. Decidir a fundacao de identidade

Abrir um spike tecnico para fechar:

- `AUTH_USER_MODEL` customizado agora ou ponte com `CompanyUserProfile`
- login company-aware agora ou restricao temporaria de e-mail globalmente unico

Essa e a decisao mais importante do estudo inteiro.

### Fase 1. Introduzir Company e o contexto de plataforma

- criar `Company`
- criar superficie minima de plataforma para `superadmin`
- preparar `request.company`

### Fase 2. Tornar usuarios company-bound

- ligar contas comuns a `company`
- separar contas de plataforma das contas de empresa
- ajustar login, convite e recuperacao de senha

### Fase 3. Mover grupos e preferencias

- abrir `CompanyGroup` como superficie de negocio
- alinhar preferencias de usuario, grupo e empresa ao novo tenant

### Fase 4. Mover apps e navegacao

- manter `Module` global
- criar `CompanyModule`
- fazer dashboard, sidebar e topbar respeitarem a empresa da conta

### Fase 5. Mover API e auditoria

- company-aware token
- company-aware permissions
- `AuditLog.company`
- filtros e exportacoes por empresa

### Fase 6. Abrir a area completa de gestao da empresa

- cadastro da empresa
- politicas operacionais
- admins da empresa
- governanca de apps habilitados

## Decisoes importantes

### 1. O unico global deve ser o superadmin

Contas comuns nao devem atravessar empresas.

### 2. Usuario comum nao precisa de seletor de empresa

Isso simplifica shell, permissao e API.

### 3. O login precisa refletir a identidade por empresa

Se houver possibilidade de e-mails repetidos entre empresas, o login precisa ser
company-aware.

### 4. `auth.Group` nao deve continuar sendo a superficie de negocio nua e crua

Ele pode continuar existindo como motor tecnico, mas o dominio da empresa precisa de uma
camada propria.

### 5. A troca de usuario padrao e o corte mais arriscado

Se a plataforma realmente vai seguir para multiempresa estrutural, vale tratar essa
decisao cedo. Adiar demais `AUTH_USER_MODEL` tende a encarecer muito a migracao.

## Impacto nos arquivos atuais

Os hotspots mais afetados por essa evolucao seriam:

- [config/settings/base.py](../config/settings/base.py)
- [config/urls.py](../config/urls.py)
- [core/auth/forms.py](../core/auth/forms.py)
- [core/auth/views.py](../core/auth/views.py)
- [core/auth/services.py](../core/auth/services.py)
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
- [core/tests/factories.py](../core/tests/factories.py)

## Recomendacao final

Se o sistema realmente vai operar em servidor central para varias empresas, e a regra de
produto e "cada usuario pertence a sua empresa, exceto superadmin", a direcao
arquitetural recomendada passa a ser:

- **multiempresa por banco compartilhado**
- **Company como raiz do tenant**
- **usuario comum atrelado a uma unica empresa**
- **superadmin como excecao global**
- **grupos, API, apps, auditoria e configuracoes contextualizados por empresa**
- **duas superficies administrativas**:
  - plataforma
  - empresa

Essa direcao e mais coerente com a regra de negocio do que insistir em identidade global
com membresia.

## Proximo passo recomendado

Abrir um lote de arquitetura com:

1. decisao formal sobre `AUTH_USER_MODEL` versus ponte temporaria
2. decisao formal sobre login company-aware
3. `Company`
4. `request.company`
5. esqueleto da area de plataforma
6. esqueleto da area de gestao da empresa

Esse e o menor corte que ja muda a fundacao para a direcao correta.
