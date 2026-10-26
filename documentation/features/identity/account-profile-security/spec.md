---
title: SHIFU-97 — Perfil e segurança em Minha conta
status: implemented
revision: 1
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-97
scope:
  - Identity
  - Web autenticado e integração BFF
last_updated_at: 2026-10-25
---

# Objective

Entregar as abas Perfil e Segurança de Minha conta com dados reais e persistência. A conta ativa poderá atualizar nome e fuso e trocar a senha. A troca preservará o acesso iniciador, encerrará os demais e invalidará recuperações pendentes.

Modo complete. O risco material está na autorização, concorrência com recuperação, alteração do esquema de Identity e integração com a sessão técnica do BFF. Hoje /account é uma página provisória. Os campos de perfil já existem, mas faltam as operações desta entrega.

# Scope

| Área / ator | Incluído | Excluído ou adiado |
| --- | --- | --- |
| Aprendiz ativo e autenticado | Consulta e edição do próprio nome e fuso; e-mail somente leitura | Edição de e-mail, avatar, biografia, conta de terceiros |
| Credenciais | Senha atual, nova senha válida, preservação do acesso iniciador, revogação dos demais e invalidação dos links anteriores | Fluxo novo de recuperação, aviso adicional por e-mail, gestão de dispositivos |
| Minha conta | Perfil e Segurança em /account, menu navegável, teclado e mobile | Exclusão de conta e sua aba; ação nova “Sair de todos” |
| Integração existente | Política /privacy, contato da SHIFU-96 e saída atual | Alteração da política, atendimento de solicitações ou correção geral de logout |
| Consumidores | Atualização do nome no menu; disponibilização do fuso atual por Identity | Recalcular história de Gamification, alterar fusos fixados por outras telas ou manter operações assíncronas antigas após mudança de credenciais |

Cobertura do PRD: RP-05 full; RP-06 partial para perfil, fuso e integração dos pontos de privacidade, com exclusão adiada; RP-07 partial para as operações e a revogação afetadas; RP-10 partial para esta página e seus controles; RP-11 partial para consulta e contato já entregues. JN-05 e JN-06 contextualizam as ações. Não se declara concluído o restante de Identity.

As referências e as adaptações aceitas estão em [design/handoff.md](design/handoff.md). O usuário aprovou o escopo e delegou a aceitação das recomendações restantes. O pedido de implementação aprovou o contrato escrito em 25/10/2026.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | RP-05, RP-06, RP-07 | Somente conta ativa com acesso válido consulta ou altera seu perfil e senha. Conta e sessão são derivadas da autenticação verificada. Campos do cliente não selecionam outro proprietário. Revalidar o contexto antes de uma escrita concorrente. |
| RF-02 | RP-06, JN-06 | Consultar nome, e-mail e fuso reais. Salvar nome obrigatório, normalizado nas extremidades, não exclusivo e limitado aos 160 caracteres suportados pela persistência. Não exigir senha para perfil. Preservar referência da conta, e-mail e propriedade dos dados. |
| RF-03 | RP-06 | O fuso salvo tem prioridade. Sem valor salvo, sugerir o fuso IANA detectado no navegador e marcar a sugestão como ainda não salva. Se a detecção falhar, exigir escolha antes de salvar. A leitura não altera a conta. Salvar um fuso válido não recalcula datas históricas. |
| RF-04 | RP-06, RP-07, JN-06 | O menu usa o nome canônico atualizado após salvar e em novo acesso. Um erro ao sincronizar a cópia técnica não transforma o salvamento canônico em falha. Na indisponibilidade de Identity, o menu usa identificação neutra em vez de um nome possivelmente antigo. |
| RF-05 | RP-05, JN-05 | Exigir senha atual correta e nova senha de pelo menos oito caracteres. Não exigir combinações de classes de caracteres nem confirmação adicional. Não remover espaços das senhas. Rejeição confirmada não muda hash, acessos ou tokens. |
| RF-06 | RP-05, JN-05 | Confirmar senha, revogação dos outros acessos, preservação do iniciador e invalidação das recuperações anteriores na mesma transação Identity. O iniciador mantém cookie, identificador e vencimento. Duas trocas pela mesma sessão continuam possíveis. Recuperação posterior remove essa preservação. Não enviar aviso adicional por e-mail. |
| RF-07 | RP-05, RP-07 | Falhas anteriores ao commit revertem todos os efeitos. Uma resposta perdida depois do commit não desfaz a senha nem encerra o iniciador. A interface distingue rejeição conhecida de resultado não confirmado. Não repetir automaticamente a troca de senha. |
| RF-08 | RP-05, RP-06, RP-10 | Formulários expõem validação, carga, envio, sucesso e falha recuperável. Manter rascunho não sensível em falha e ao alternar abas. Limpar senhas após uma tentativa concluída no servidor ou resultado incerto. Impedir envios duplicados enquanto pendente. Permitir teclado e mobile sem depender só de cor. |
| RF-09 | RP-06, RP-10, RP-11 | Oferecer política e contato da SHIFU-96. Abrir e-mail não envia solicitação. Tornar “Sua conta” navegável no menu e reutilizar a saída atual. |
| RF-10 | RP-05, RP-07 | O navegador não pode alterar a versão técnica de acesso nem atualizar nome fora da operação canônica. Segredos, senhas, hashes, JWTs e concessão da sessão preservada não aparecem em respostas da página, URLs, armazenamento do navegador ou telemetria. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Conta ativa, pendente, excluída; acesso ausente, expirado, adulterado ou revogado; segundo proprietário | Consultar ou alterar conta | Só o proprietário ativo com contexto válido é aceito; nenhum efeito protegido na rejeição | CI-01–CI-06, CI-09 |
| CA-02 | RF-02 | Conta com perfil persistido | Abrir Perfil e retornar depois | Nome, e-mail somente leitura e fuso correspondem à conta, sem valores fictícios | CI-01, CI-03, CI-07–CI-09, VM-01 |
| CA-03 | RF-02 | Nome vazio, só espaços, 1, 160 e 161 caracteres; nome duplicado | Salvar o perfil | Vazio e excesso são rejeitados; limites válidos e duplicação são aceitos; dados e proprietário permanecem íntegros | CI-01, CI-03, CI-08 |
| CA-04 | RF-03 | Fuso salvo ou null; navegador com detecção válida ou indisponível | Abrir e salvar Perfil | Valor salvo prevalece; sugestão não altera persistência até Salvar; somente fuso válido de até 64 caracteres é salvo; não há limpeza para null pela edição | CI-01, CI-03, CI-07–CI-09, VM-01 |
| CA-05 | RF-03 | Histórico de prática já reconhecido para a conta e outro proprietário | Alterar fuso | Identity disponibiliza o valor novo; datas, fusos reconhecidos, XP e sequência históricos não são reescritos | CI-03 |
| CA-06 | RF-04 | Perfil salvo, incluindo falha da sincronização técnica | Atualizar menu, reabrir página ou entrar novamente | Nome canônico aparece quando Identity responde; na indisponibilidade posterior aparece “Minha conta”; nunca se declara que o save falhou após commit | CI-08–CI-09, VM-01 |
| CA-07 | RF-05 | Senha atual correta/incorreta; nova vazia, 7, 8 e mais caracteres | Solicitar troca | Erro da senha atual é distinto da nova; oito é aceito; senhas idênticas não são proibidas; rejeição preserva credenciais, acessos e recuperações | CI-02, CI-04, CI-07–CI-09 |
| CA-08 | RF-06 | Duas sessões anteriores e uma sessão iniciadora | Trocar senha e repetir pela iniciadora; depois entrar com a nova senha | Iniciadora continua válida sem renovar vencimento; outras são recusadas; senha antiga não inicia acesso; uma nova sessão que troca a senha substitui a preservação anterior | CI-02, CI-04, CI-06, CI-09, VM-02 |
| CA-09 | RF-06 | Recuperações pendentes, expiradas, usadas e invalidadas | Trocar a senha; depois executar recuperação válida emitida posteriormente | Links anteriores pendentes ficam inválidos; estados terminais não são reabertos; recuperação posterior revoga também a sessão preservada | CI-02, CI-04–CI-06, CI-09 |
| CA-10 | RF-07 | Falha de hash, escrita ou evento; resposta perdida após commit | Processar a troca | Antes do commit não há efeito parcial; depois dele o iniciador continua autorizado e o cliente não afirma rejeição nem repete a ação automaticamente | CI-02, CI-04, CI-08–CI-09 |
| CA-11 | RF-01, RF-06, RF-07 | Trocas simultâneas, recuperação/reenvio/solicitação concorrentes e contexto autenticado antes de outra revogação | Serializar as operações | Ordem coerente de bloqueios, sem deadlock; autorização antiga não grava após revogação; cada resultado corresponde à ordem efetiva dos commits | CI-04–CI-06 |
| CA-12 | RF-08 | Desktop, mobile, teclado, movimento reduzido e respostas pendentes/falhas | Usar as duas abas e formulários | Rótulos, foco e anúncios acessíveis; dados não sensíveis preservados; envios duplicados impedidos; senhas limpas; sem overflow | CI-07–CI-08, VM-01–VM-04 |
| CA-13 | RF-09 | Menu e aba Perfil | Abrir Minha conta, política, contato e saída | Destinos canônicos e URI de contato preservados; clique de contato não afirma envio; saída mantém seu contrato existente | CI-07–CI-09, VM-01 |
| CA-14 | RF-10 | Sessão revogada ou cliente enviando campos técnicos | Chamar endpoints genéricos ou adulterar o corpo | Atualização genérica de sessão/usuário/senha nativa é bloqueada; nenhum acesso é recuperado; campos desconhecidos não mudam propriedade ou autorização | CI-04, CI-06, CI-09 |
| CA-15 | RF-06 | Base anterior com contas e acessos existentes | Aplicar e reverter a migração em base descartável | Upgrade preserva dados e inicia concessão vazia; restrições rejeitam pares inválidos; downgrade remove só os campos novos e pode encerrar sessões preservadas antigas | CI-14 |

# Technical Contract

## Architecture Mapping

Identity mantém regras, identidade, credenciais e concessão de acesso. O BFF mantém cookie e emissão de JWT. Shared apenas expõe contexto técnico autenticado e infraestrutura existente. Não há importação entre núcleos de módulos de negócio.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Identity Core / REST | Casos de uso, entradas e controladores de perfil/senha abaixo | Expor três ações da própria conta e seus contratos |
| Modify | Identity Core / Database | Account, AccountModel, AccountMapper, AccountFaker | Persistir e validar a única sessão preservada; normalizar perfil sem alterar credenciais |
| Modify | Shared Core / Identity Provider | AuthenticatedUser, AuthenticationProvider, provedor JWKS | Carregar sid e duas versões confiáveis; aceitar concessão exata sem enfraquecer assinatura ou estado ativo |
| Modify | Identity recovery | ResetPasswordUseCase, RetryPasswordRecoveryUseCase, port/adaptador de tokens | Adotar conta antes de token nas operações que bloqueiam ambos; reset remove concessão |
| Modify | REST wiring / errors | IdentityRouter, AppErrorHandler, IdentityPipe se necessário | Registro explícito, contexto verificado e erros específicos seguros |
| Create | Alembic | Revisão gerada em apps/server/migrations/versions | Duas colunas e uma restrição; sem preenchimento retroativo ou nomes de revisão inventados |
| Modify | Web provision / REST | BetterAuthProvider, CookieSessionAuthProvider, IdentityService, AuthError | Operações canônicas, bloqueio de mutações técnicas, tradução tipada e reconciliação de nome |
| Modify | Web routing / shell | Rota account, useNavigation, AccountMenu | Composição fina, atualização da identidade da rota e acesso navegável ao perfil |
| Modify / Create | Identity UI | AccountPage, formulários e cartão de privacidade | Composição do handoff; estado local com um único proprietário |
| Modify / Create | Shared primitives | Input e Select | Foco do Input conforme regra UI; Select acessível com Base UI já instalado |
| Modify / Create | Test boundaries / fixtures | Arquivos abaixo | Cobertura nos limites permitidos e preparação descartável/reutilizável |

Árvore esperada. [N] é novo e [M] é modificado. Caminhos de teste novos são planejados. Arquivos de entrada compartilhados mantidos sem mudança não ganham testes ou edições artificiais.

~~~text
apps/server/
├── src/shifu/
│   ├── identity/
│   │   ├── core/domain/
│   │   │   ├── entities/account.py [M]
│   │   │   ├── structures/{account_profile_update,password_change_request}.py [N]
│   │   │   ├── structures/__init__.py [M]
│   │   │   ├── errors/invalid_time_zone_error.py [N]
│   │   │   └── errors/__init__.py [M]
│   │   ├── core/interfaces/account_action_tokens_repository.py [M]
│   │   ├── core/use_cases/
│   │   │   ├── {get_account_profile,update_account_profile,change_password}_use_case.py [N]
│   │   │   ├── {reset_password,retry_password_recovery}_use_case.py [M]
│   │   │   └── __init__.py [M]
│   │   ├── database/sqlalchemy/
│   │   │   ├── models/account_model.py [M]
│   │   │   ├── mappers/account_mapper.py [M]
│   │   │   └── repositories/account_action_tokens_repository.py [M]
│   │   ├── providers/auth/jwt/jwks/jwks_jwt_authentication_provider.py [M]
│   │   └── rest/
│   │       ├── router.py [M]
│   │       └── controllers/{get_account_profile,update_account_profile,change_password}_controller.py [N]
│   ├── shared/core/
│   │   ├── domain/structures/authenticated_user.py [M]
│   │   └── interfaces/authentication_provider.py [M]
│   ├── fakers/identity/entities/account_faker.py [M]
│   └── rest/handlers/app_error_handler.py [M]
├── migrations/versions/ [N: revisão Alembic gerada; identificador determinado na implementação]
├── rest-client/identity/identity.rest [M]
└── tests/identity/
    ├── core/use_cases/test_{get_account_profile,update_account_profile,change_password}_use_case.py [N]
    ├── core/use_cases/test_{reset_password,retry_password_recovery}_use_case.py [M]
    └── server/controllers/
        ├── test_{get_account_profile,update_account_profile,change_password}_controller.py [N]
        └── test_get_current_session_controller.py [M]

apps/web/
├── src/
│   ├── core/errors/auth-error.ts [M]
│   ├── rest/services/identity-service.ts [M]
│   ├── provision/auth/
│   │   ├── cookie-session-auth-provider.ts [M]
│   │   └── better-auth/better-auth-provider.ts [M]
│   ├── routes/account/index.tsx [M]
│   ├── ui/shadcn/{input,select}.tsx [M input / N select]
│   ├── ui/shared/
│   │   ├── hooks/use-navigation.ts [M]
│   │   ├── contexts/auth-context/tests/use-auth-context-provider.test.ts [M]
│   │   └── widgets/layouts/
│   │       ├── app-layout/account-menu/
│   │       │   ├── index.tsx [M]
│   │       │   ├── use-account-menu.ts [M]
│   │       │   └── tests/{account-menu.test.tsx,use-account-menu.test.ts} [M]
│   │       └── root-layout/tests/use-root-layout.test.ts [M somente se o teste consumidor exigir atualização]
│   ├── ui/identity/constants/privacy-contact.ts [N]
│   ├── ui/identity/widgets/pages/privacy-policy-page/index.tsx [M: somente importar contato comum]
│   └── ui/identity/widgets/pages/account-page/
│       ├── index.tsx [M]
│       ├── use-account-page.ts [N]
│       ├── use-account-profile-query.ts [N]
│       ├── tests/{account-page.test.tsx,use-account-page.test.ts} [M componente / N hook]
│       ├── profile-form/
│       │   ├── index.tsx [N]
│       │   ├── use-profile-form.ts [N]
│       │   ├── use-update-account-profile-action.ts [N]
│       │   └── tests/{profile-form.test.tsx,use-profile-form.test.ts} [N]
│       ├── security-form/
│       │   ├── index.tsx [N]
│       │   ├── use-security-form.ts [N]
│       │   ├── use-change-account-password-action.ts [N]
│       │   └── tests/{security-form.test.tsx,use-security-form.test.ts} [N]
│       └── privacy-card/index.tsx [N: apresentação pura]
└── tests/
    ├── fixtures/identity-module-fixture.ts [M]
    ├── identity/account-page.test.ts [M: transporte simulado]
    ├── identity/account-auth-api.test.ts [N: handler real]
    └── shared/app-layout.test.ts [M: apenas grupo de navegação da conta]
~~~

A notação com chaves na árvore expande para arquivos individuais, não para arquivos que agreguem classes. O pipe Identity existente e o barrel Shared de estruturas só mudam se a composição/exportação realmente exigir. A rota mantém /account; não há nova rota nem alteração manual de routeTree.gen.ts. Se a composição alterar os metadados gerados, usar pnpm --filter web generate-routes e revisar só o resultado pertinente.

### Perfil e entradas Core

AccountProfile permanece a estrutura existente em identity/core/domain/structures/account_profile.py. Nenhum novo modelo de domínio é criado para duplicar seus campos. As novas entradas são estruturas imutáveis com validação local, sem I/O ou dependência de framework:

~~~python
@structure
class AccountProfileUpdate:
    display_name: str
    time_zone: str

@structure
class PasswordChangeRequest:
    current_password: str
    new_password: str

class InvalidTimeZoneError(ValidationError):
    message: str = 'Selecione um fuso horário válido.'

class GetAccountProfileUseCase:
    def __init__(self, identity_database: IdentityDatabase) -> None: ...
    def execute(self, user: AuthenticatedUser) -> AccountProfile: ...

class UpdateAccountProfileUseCase:
    def __init__(
        self, identity_database: IdentityDatabase, clock_provider: ClockProvider
    ) -> None: ...
    def execute(
        self, user: AuthenticatedUser, update: AccountProfileUpdate
    ) -> AccountProfile: ...

class ChangePasswordUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        password_hashing_provider: PasswordHashingProvider,
    ) -> None: ...
    def execute(
        self, user: AuthenticatedUser, request: PasswordChangeRequest
    ) -> None: ...
~~~

AccountProfileUpdate normaliza somente o nome nas extremidades e aplica CA-03. O fuso deve ser chave IANA resolvível por zoneinfo, com no máximo 64 caracteres. Não aceitar offset livre ou caminho arbitrário. A edição exige fuso concreto; null continua permitido apenas para perfis legados ainda não editados. Senhas usam contagem coerente de caracteres Unicode no Web e Server, com casos de teste não ASCII. Nova senha igual à atual é permitida.

### Concessão da sessão preservada

A concessão é uma exceção de autorização de Identity para um único identificador de sessão assinado. Não é um novo cookie, token ou sessão. Resolve a atomicidade sem acoplar Identity à base técnica configurável do Better Auth.

Acrescentar ao resultado de AuthenticatedUser, mantendo os três campos atuais e compatibilidade dos construtores existentes:

~~~python
@structure
class AuthenticatedUser:
    account_id: str
    display_name: str
    time_zone: str | None
    session_id: str | None = None
    token_access_version: int | None = None
    account_access_version: int | None = None
~~~

O provedor real preenche os três campos novos após verificar assinatura, emissor, audiência, prazo e tipos. Eles são internos. /identity/session continua com sua resposta atual. Casos de uso desta entrega exigem contexto completo; defaults não autorizam mutações.

Acrescentar estes campos opcionais a Account e Account.create, com default None. Todos os campos e argumentos existentes permanecem:

~~~python
retained_session_id: str | None = None
retained_session_access_version: int | None = None
~~~

A transição pública replace_password mantém os argumentos atuais e recebe dois argumentos opcionais nomeados:

~~~python
def replace_password(
    self,
    password_hash: str,
    updated_at: datetime,
    *,
    retained_session_id: str | None = None,
    retained_session_access_version: int | None = None,
) -> None: ...
~~~

O par deve estar todo vazio ou todo preenchido. Quando preenchido, o identificador não é vazio e a versão é positiva e inferior à nova access_version da conta. A troca incrementa a versão e substitui o par. Sem os novos argumentos, replace_password remove a concessão, preservando a semântica de recuperação. confirm, expire, delete e invalidate_other_accesses removem qualquer concessão anterior quando revogam ou encerram acesso. Nome e fuso não alteram o par ou a versão.

A autenticação de conta ativa aceita a versão atual da conta ou o par exato de sid e versão preservados. Nenhuma outra versão antiga ou outro sid recebe a exceção. Exemplo: sessão A assinada na versão 3 continua válida após a conta ir à versão 4 com par (A, 3). Uma segunda troca por A mantém (A, 3) e avança a conta a 5.

Dentro do bloqueio da conta, Get/Update/Change verificam estado ativo, o mesmo account_access_version observado na autenticação e a aceitação atual do par assinado. Isso impede que uma autorização obtida antes de outra revogação execute a escrita depois dela. Rejeição desse contexto é autorização inválida, não erro da senha atual.

AccountModel usa Text anulável para retained_session_id e Integer anulável para retained_session_access_version. A restrição nomeada ck_identity_accounts_retained_session exige os dois NULL ou os dois preenchidos, identificador não vazio e 0 < versão preservada < access_version. Sem FK para Better Auth e sem índice novo: a conta já é buscada pela chave primária. AccountMapper mapeia ambos nos dois sentidos. AccountFaker ganha overrides opcionais correspondentes.

A migração é gerada com uv run poe db:migrate "preserve current session on password change" contra ambiente descartável, após configurar explicitamente seu DATABASE_URL e verificar ausência de .env.local que possa substituí-lo. Revisar o arquivo gerado. Registros anteriores começam sem concessão; não há preenchimento retroativo. Upgrade de esquema deve preceder os novos writers. Não executar versões antigas que não conheçam a concessão depois de sua ativação. Downgrade em janela controlada pode encerrar as sessões cujo JWT antigo dependia dela, sem alterar senhas ou outros dados. Não rodar migração ou reset na base compartilhada durante a autoria.

O BFF conserva sid, accessVersion, token e vencimento da sessão técnica. Não chama updateSession para sincronizar revisões nem deleteUserSessions após a troca. Revogação dos outros acessos é lógica e imediata na API. Operações Mentor/Planejador anteriores continuam sujeitas à revisão atual da conta por IdentityMentorAccessProvider. Sua interrupção não encerra a sessão preservada. Não substituir essa revisão pela versão antiga do JWT.

### Recuperação, bloqueios e eventos

AccountActionTokensRepository recebe estas buscas sem bloqueio, além dos métodos atuais inalterados:

~~~python
def find_account_id_by_hash(self, token_hash: str) -> str | None: ...
def find_account_id_by_pending_handle_hash(
    self, pending_handle_hash: str
) -> str | None: ...
~~~

ResetPasswordUseCase e RetryPasswordRecoveryUseCase usam a referência apenas para localizar o proprietário. Depois bloqueiam a conta e relêem o token com o método bloqueante existente. Revalidam proprietário, tipo, prazo e estado sob bloqueio. A referência preliminar nunca autoriza sozinha.

Operações que bloqueiam conta e tokens usam conta antes de tokens. Solicitação de recuperação já segue essa ordem. Leituras ou atualizações de entrega que bloqueiam só tokens não passam a bloquear contas. Uma recuperação solicitada e confirmada depois da troca pode criar um link novo normalmente; não se promete invalidar pedidos futuros.

ChangePasswordUseCase invalida todos os tokens PASSWORD_RECOVERY ainda PENDING. Para tokens com comunicação associada, persiste AccountActionTokenCancelledEvent com o payload e razão RESET existentes na mesma transação. Esse contrato já é traduzido para cancelamento da comunicação pela composição. Não incluir senha, hash, JWT ou sid em eventos. Não criar job, broker, e-mail de aviso ou consumidor novo. Os eventos AccountPasswordChangedEvent e AccountDisplayNameChangedEvent já declarados, sem consumidores ativos, não precisam ser publicados para cumprir esta entrega. Não acrescentar eventos sem destino só para atualizar o menu.

### HTTP e integração do BFF

Cada controlador novo declara Request quando aplicável e Response local conforme a regra REST. Respostas de perfil validam AccountProfile com TypeAdapter. Corpos novos rejeitam campos desconhecidos. Todos exigem o segredo BFF e Bearer JWT verificado, sem account_id ou session_id selecionável no corpo.

| Método e caminho Server | Entrada | Resposta 200 |
| --- | --- | --- |
| GET /identity/accounts/me | Sem corpo | AccountProfile completo com nomes snake_case e datas ISO: account_id, display_name, email, time_zone, status, created_at, confirmed_at |
| PATCH /identity/accounts/me | {display_name: string, time_zone: string} | Mesmo perfil canônico persistido |
| POST /identity/accounts/me/password | {current_password: string, new_password: string} | {changed: true} |

Erros: 401 unauthorized para credencial ausente/inválida ou contexto revogado; 403 invalid_current_password exclusivamente para senha atual incorreta; 400 invalid_display_name, invalid_time_zone ou invalid_new_password para a validação de domínio destas operações; 422 validation_error para formato inválido/campos desconhecidos; 503 service_unavailable para falha antes de confirmar a operação. Mensagens são seguras e em pt-BR. Mapear os erros específicos antes dos genéricos no AppErrorHandler e limitar as novas traduções às operações da conta para preservar cadastro/recuperação existentes. Para esses caminhos, AuthorizationError de revalidação vira 401; fora deles mantém o mapeamento atual. A resposta 401 do IdentityPipe mantém seu envelope seguro atual. O BFF normaliza os dois envelopes existentes, sem alterar outros endpoints.

Atualizar apps/server/rest-client/identity/identity.rest com os três exemplos, placeholders de segredo/JWT e corpos não secretos. Não incluir credenciais locais reais.

O plugin existente registra GET /api/auth/account, POST /api/auth/account/profile e POST /api/auth/account/password. O servidor do BFF obtém cookie e JWT. A página só recebe contratos seguros em camelCase. A chamada REST vai pelo IdentityService existente, com Authorization e o segredo BFF da composição.

Em identity-service.ts reutilizar IdentityProfile e acrescentar:

~~~typescript
getAccountProfile(accessToken: string): Promise<IdentityProfile>
updateAccountProfile(
  accessToken: string,
  input: { displayName: string; timeZone: string },
): Promise<IdentityProfile>
changeAccountPassword(
  accessToken: string,
  input: { currentPassword: string; newPassword: string },
): Promise<{ changed: true }>
~~~

O serviço apenas traduz método, corpo e caminho. Não autentica, decide negócio, valida resposta bem-sucedida ou duplica contratos de domínio. A transformação snake_case/camelCase pertence ao provisionamento que já integra Identity. As declarações existentes permanecem.

Em cookie-session-auth-provider.ts acrescentar os contratos seguros completos:

~~~typescript
export type AccountProfile = {
  accountId: string
  displayName: string
  email: string
  timeZone: string | null
}
export type UpdateAccountProfileInput = {
  displayName: string
  timeZone: string
}
export type ChangeAccountPasswordInput = {
  currentPassword: string
  newPassword: string
}
getAccountProfile(): Promise<AccountProfile>
updateAccountProfile(input: UpdateAccountProfileInput): Promise<AccountProfile>
changeAccountPassword(input: ChangeAccountPasswordInput): Promise<{ changed: true }>
~~~

AuthErrorKind mantém suas opções atuais e acrescenta 'validation-failed', 'invalid-current-password' e 'result-uncertain'. AuthErrorOptions e AuthError ganham field opcional 'displayName' | 'timeZone' | 'newPassword'. Os demais membros permanecem. O estado result-uncertain representa perda de resposta ou resposta ilegível após envio da mutação de senha, sem confirmação de rejeição. Não significa que o servidor a aplicou. Não criar recibo idempotente nem reenvio automático nesta entrega.

No BetterAuthProvider:
- Definir input:false em session.additionalFields.accessVersion.
- Bloquear disabledPaths ['/update-session', '/update-user', '/change-password']; são relativos a /api/auth. Não remover o bloqueio existente de /api/auth/token.
- Operações da conta exigem dados canônicos. Não usam fallback técnico para ler perfil ou decidir uma escrita.
- Após leitura/salvamento canônico, reconciliar name do usuário técnico uma vez quando necessário. Falha nessa cópia é telemetria segura, sem derrubar a sessão ou retornar erro de save já confirmado.
- O ramo de indisponibilidade já existente de getCurrentAccess mantém a política de acesso, mas apresenta displayName='Minha conta'. Não usar um nome técnico possivelmente antigo nesse ramo.
- Não incluir os campos internos de sessão nos JSONs novos da conta. Respostas da conta usam Cache-Control: no-store. Mutações conservam a validação de origem/CSRF do handler e seus schemas Zod rejeitam campos desconhecidos.
- Usar o HTTP_STATUS_CODE real de src/constants/http-status-code.ts. A referência a @hms/core na regra UI não existe neste repositório.

Essa proteção é baseada no Better Auth 1.6.23 instalado. Seu /update-session aceita campos adicionais configurados; /update-user aceita name/image por uma via própria. O bloqueio evita rotas paralelas de escrita. A sessão preservada não autoriza atualizar livremente sua versão.

### Composição e estado Web

AccountPage recebe AccountPageProps = { accountEmail: string }. A rota passa o e-mail obtido pelo middleware para discriminar apenas o cache em memória. Ele não identifica o ator de uma chamada e não é enviado como autorização ou seletor ao BFF.

O contexto Auth existente permanece montado no RootLayout. Seu index.tsx, types/auth-context-value.ts, use-auth-context-provider.ts e use-auth-context.ts mantêm os caminhos atuais. O valor já é ReturnType de CookieSessionAuthProvider e incorpora as operações novas sem estado duplicado. Atualizar seu teste de construção. Não criar outro contexto de perfil. LayoutAccount permanece inalterado.

useNavigation acrescenta refreshCurrentRoute(): Promise<void>, que aguarda router.invalidate({sync:true}) pelo wrapper compartilhado. Não navega, renova sessão nem apaga drafts. O consumidor usa o wrapper, não TanStack Router diretamente.

Contratos dos hooks:
- useAccountProfileQuery(accountEmail: string) retorna accountProfile: AccountProfile | null, isLoadingAccountProfile: boolean, accountProfileError: AuthError | null e refetchAccountProfile(): Promise<void>. O hook normaliza a promessa do cliente de consulta, sem expor seu resultado técnico ao consumidor. Lê somente o próprio perfil. Chave ['identity','account-profile',accountEmail], staleTime:0, gcTime:0, retry:false, sem persistência local nem dados anteriores como placeholder. Refetch ao retomar foco é permitido. Não compartilhar dados entre contas; desmontagem remove o cache inativo.
- useUpdateAccountProfileAction() retorna updateAccountProfile(input): Promise<AccountProfile>, isPending e error. Escreve pelo contexto Auth, substitui a resposta canônica na consulta da conta, aguarda atualização da identidade da rota e separa falha de atualização visual de save já confirmado. Não repete automaticamente. Tentativa explícita com o mesmo perfil é segura.
- useChangeAccountPasswordAction() retorna changeAccountPassword(input): Promise<{changed:true}>, isPending e error. Sem cache ou estado otimista; retry:false. Não considera falha da leitura posterior como falha da troca confirmada.
- useAccountPage recebe as props da página, controla aba 'profile' | 'security' e consome accountProfile, isLoadingAccountProfile, accountProfileError e refetchAccountProfile. Expõe os dados e handlers da página com esses nomes de domínio. Não guarda drafts ou senhas.
- ProfileFormProps = { profile: AccountProfile }. O formulário possui draft de nome/fuso, detecção local, validação e feedback. Refetch não sobrescreve campos alterados ainda não salvos. Após sucesso, adota o retorno canônico.
- SecurityForm não recebe perfil nem segredos por props. Possui os campos de senha, visibilidade, validação e feedback.
- As abas mantêm os formulários montados com conteúdo inativo fora da árvore acessível e da sequência de foco. Draft de perfil sobrevive à alternância. Senhas são limpas ao sair da aba e após tentativa concluída, inclusive rejeição conhecida ou resultado incerto. Não persistir senhas em contexto/cache.
- PrivacyCard é renderizador puro. Reutiliza a rota privacy e os valores do contato da SHIFU-96. As constantes hoje privadas em privacy-policy-page/index.tsx passam sem alteração para ui/identity/constants/privacy-contact.ts. A página pública e PrivacyCard importam essa única definição. Não modificar a política ou duplicar seu endereço/URI.

~~~typescript
export const PRIVACY_CONTACT_EMAIL = 'shifu.ctrlaltdel@gmail.com'
export const PRIVACY_CONTACT_MAILTO =
  'mailto:shifu.ctrlaltdel@gmail.com?subject=Solicita%C3%A7%C3%A3o%20sobre%20meus%20dados%20%E2%80%94%20Shifu&body=Ol%C3%A1!%20Gostaria%20de%20solicitar%3A%20%5Bdescreva%20seu%20pedido%5D.'
~~~

Opções de fuso vêm dos identificadores IANA suportados pelo navegador, mais UTC e os valores salvo/detectado quando válidos. Não restringir o produto a fusos brasileiros. Apresentar rótulos pt-BR e manter o identificador canônico no valor. O Server continua autoridade de validade. Não fixar um GMT que fique incorreto no horário de verão.

Select é um primitivo compartilhado, com props públicas: id/name/className/placeholder opcionais string; value string | null; options readonly {value:string;label:string}[]; onValueChange(value:string|null):void; disabled/required opcionais boolean; aria-label/aria-labelledby/aria-describedby opcionais string; aria-invalid opcional boolean. Sua composição usa Select Root/Trigger/Value/Portal/Positioner/Popup/Item do Base UI 1.8.0. Valor fechado e item aberto mostram o rótulo, não apenas o discriminador técnico. Não recebe regra de Identity.

Reutilizar TanStack Form e validação Zod local dos formulários/handler. Não criar pacote de validação, dependência externa ou família de schemas reutilizáveis nesta entrega. Ajustar somente o foco do Input compartilhado para a regra vigente e verificar consumidores de autenticação afetados. Os tokens globais, o shell e a API do Input permanecem.

## Runtime Flow

1. O aprendiz entra por “Sua conta”. A rota protegida obtém a identidade e compõe AccountPage. Sua consulta pede o perfil ao BFF com cookie de mesma origem. O BFF emite JWT interno e o controlador Identity autentica e carrega o perfil da própria conta.
2. Perfil prepara o draft. O valor salvo prevalece sobre o navegador. Uma detecção sem valor salvo é só sugestão, claramente não persistida. Salvar valida corpo, contexto e domínio. Uma única transação bloqueia a conta, revalida a revisão, atualiza nome/fuso e retorna o perfil.
3. O BFF tenta reconciliar sua cópia do nome. A página substitui a consulta e atualiza os contextos da rota. Falha da cópia/refresh não inventa rollback do perfil. Uma nova leitura canônica permite recuperar a apresentação.
4. Segurança envia as duas senhas ao handler próprio. Identity bloqueia a conta, revalida revisão e par autenticado, verifica a senha atual, calcula o hash novo e persiste hash, versão, concessão do iniciador e invalidações. Eventos de cancelamento com comunicação associada participam da mesma transação.
5. Um erro que escape antes do commit reverte a transação. Sem confirmação de transporte depois do envio, o cliente anuncia resultado incerto e não repete sozinho. A sessão iniciadora continua aceita tanto se nada mudou quanto se o commit ocorreu. O botão não declara sucesso antes da resposta confirmada.
6. JWTs dos outros sid antigos falham na verificação atual. Novo login usa senha nova e versão atual. Recuperação posterior usa a ordem conta→token, troca credencial e remove a concessão. Nenhum efeito novo depende de apagar fisicamente sessões Better Auth antigas.
7. O fuso novo é disponibilizado pela identidade atual para operações futuras. Não publicar trabalho de recálculo e não reescrever registros históricos de Gamification. A saída continua pelo fluxo existente.

# Verification Contract

## Shared setup

Autoria não executa testes, migrações ou fluxos reais. Todos os cenários/arquivos novos abaixo são planejados. As evidências futuras pertencem a Evaluation, criado somente no início da implementação.

Server: usar uv e os manifests/lockfiles atuais. Testes unitários usam autospec dos ports e ClockProvider determinístico. Controladores usam FastAPIApp.register, TestClient e as fixtures tests/conftest.py, tests/fixtures/postgres_fixture.py e redis_fixture.py. Elas criam PostgreSQL pgvector:0.8.1-pg17 e Redis descartáveis, aplicam Alembic e limpam somente sua base de teste. Nunca usar Compose como substituto dessas fixtures.

Planejar no teste do controlador de sessão uma fixture local de chave Ed25519/JWKS e tokens de conta/sid/versão conhecidos. Exercitar o provedor composto por HTTP. Servir JWKS em servidor HTTP local de porta efêmera e fechar no teardown. Não substituir a autenticação real nos casos que provam revogação. Doubles de portas podem ficar nos cenários de domínio; falhas de infraestrutura são injetadas só na composição.

Para CA-05, o teste do controlador de edição prepara registros reais de PracticeDay e perfil pelo adapter Gamification usado em test_get_practice_calendar_controller.py. Usar prática perto da meia-noite com fuso reconhecido, conta A e controle B. Comparar registros persistidos de datas/fusos e saldos antes/depois da edição, além da identidade atual. Essa composição de teste não permite importação entre módulos em código de produção.

Web: Vitest usa a configuração atual, hook proprietário mockado nos componentes e wrappers de aplicação nos hooks. A rota usa tests/playwright.ts e transporte simulado com respostas mutáveis. O handler usa a mesma fixture, activeAccount/pendingAccount e PostgreSQL reais. Sua limpeza deve remover tokens/comunicações/outbox pertencentes à conta de teste e os registros técnicos associados, sem remover dados compartilhados.

Para testes do handler e percursos manuais, verificar docker compose ps e GET /health. A configuração Playwright inicia API/Web se necessário nas portas configuradas, por padrão 7777/7000. Configurar BETTER_AUTH_DATABASE_URL e DATABASE_URL para a mesma base de teste e SHIFU_IDENTITY_API_URL/SHIFU_WEB_APP_URL/SHIFU_AUTH_ISSUER para a instância correta. A concessão de Identity não exige que as bases técnicas sejam iguais em produção. Credenciais e segredo BFF são resolvidos pelos arquivos ignorados ou ambiente, sem impressão. Não copiar arquivos rastreados como se fossem segredos.

Acrescentar à fixture Identity, sem teste dedicado, os exports planejados prepareAccountForManualValidation(runId:string):Promise<SignInHandlerAccount> e cleanupAccountForManualValidation(account:SignInHandlerAccount):Promise<void>. Reusar makeAccount/seedAccount/cleanupAccount e signInPassword já presentes. Criar somente conta com runId exclusivo. A limpeza remove apenas os dados dessa conta e cobre tokens/comunicações que ela tiver criado. A conta seed compartilhada não é usada para trocar senha.

Preparação manual executável após implementar esses exports, de apps/web com Node 24 e ambiente de teste já configurado:

~~~bash
node --experimental-strip-types --input-type=module <<'JS'
import { writeFile } from 'node:fs/promises'
import { randomUUID } from 'node:crypto'
import { prepareAccountForManualValidation } from './tests/fixtures/identity-module-fixture.ts'
const account = await prepareAccountForManualValidation('shifu97-' + randomUUID())
await writeFile('.playwright-cli/states/shifu-97-account.json', JSON.stringify(account), { mode: 0o600 })
JS
~~~

Criar previamente os diretórios .playwright-cli/{states,screenshots,snapshots,logs}. Ler e-mail do arquivo local e a senha signInPassword da fixture de forma privada. Não emitir a senha, cookie ou storage state. Login acontece no formulário visível. Não há reset/reseed. Ao terminar VM-01/02, a limpeza usa o mesmo arquivo:

~~~bash
node --experimental-strip-types --input-type=module <<'JS'
import { readFile, unlink } from 'node:fs/promises'
import { cleanupAccountForManualValidation } from './tests/fixtures/identity-module-fixture.ts'
const path = '.playwright-cli/states/shifu-97-account.json'
await cleanupAccountForManualValidation(JSON.parse(await readFile(path, 'utf8')))
await unlink(path)
JS
~~~

Setup do handler não depende de envio real de e-mail para preparar um link pendente. Pode usar token próprio com hash válido pelas fixtures do módulo. A prova é sua invalidação real, não a entrega da mensagem.

Integrações são executadas em conjunto após integrar o candidato. Um runner do Orchestrator serializa comandos com containers. Selecionar somente arquivos/scenários afetados conforme [Tooling](../../../tooling.md#selecting-unit-and-integration-tests). Seleção vazia ou skipped não passa. Correções reabrem só a prova afetada. Não executar suítes completas por padrão.

## Automated

### CI-01 — Perfil e autorização em casos de uso

**Criteria:** CA-01–CA-04.
**Proof:** novos tests/identity/core/use_cases/test_get_account_profile_use_case.py e test_update_account_profile_use_case.py, de apps/server:

~~~bash
uv run pytest tests/identity/core/use_cases/test_get_account_profile_use_case.py tests/identity/core/use_cases/test_update_account_profile_use_case.py
~~~

Cobrir conta ativa/pendente/excluída/inexistente, contexto completo/ausente/stale, isolamento, limites do nome, duplicação, UTC, America/Sao_Paulo, Europe/Lisbon, Asia/Kathmandu, null de leitura, valor inválido/offset livre e excesso de 64 caracteres. Assertar perfil e ausência de escrita na rejeição. Concessão existente permanece intacta na edição. A simulação não prova persistência.

### CI-02 — Regras da troca e concessão em casos de uso

**Criteria:** CA-01, CA-07–CA-11.
**Proof:** novo tests/identity/core/use_cases/test_change_password_use_case.py.

~~~bash
uv run pytest tests/identity/core/use_cases/test_change_password_use_case.py
~~~

Cobrir senha errada, vazia, 7/8/mais caracteres, Unicode, espaços significativos, nova igual à antiga; estados/versões/sid; troca repetida pela mesma sessão e substituição do iniciador; estados finitos dos tokens e presença/ausência de comunicação; falha de hash, escrita ou outbox. Assertar retorno, novo hash, incremento, par preservado, invalidações e ausência de efeitos protegidos nas rejeições. Usar ports mockados, sem teste direto de Account ou provider.

### CI-03 — Perfil real, persistência, proprietário e história

**Criteria:** CA-01–CA-06.
**Proof:** novos tests/identity/server/controllers/test_get_account_profile_controller.py e test_update_account_profile_controller.py.

~~~bash
uv run pytest tests/identity/server/controllers/test_get_account_profile_controller.py tests/identity/server/controllers/test_update_account_profile_controller.py
~~~

Provar os três contratos de leitura/edição aplicáveis, status/envelopes/headers, read-after-write com outra conexão, e-mail/proprietário invariantes e CA-05 com registros reais não vazios. Campo extra, conta alheia, estado inválido, ausência de segredo BFF, nome/fuso inválidos não gravam. Forçar falha na composição e comparar estado anterior. Não tratar screenshot ou retorno de mock como persistência.

### CI-04 — Troca HTTP atômica e concorrência

**Criteria:** CA-01, CA-07–CA-11, CA-14.
**Proof:** novo tests/identity/server/controllers/test_change_password_controller.py.

~~~bash
uv run pytest tests/identity/server/controllers/test_change_password_controller.py
~~~

PostgreSQL real, hash real e conexões independentes. Verificar credencial antiga/nova por sign-in, concessão, tokens e cancelamentos na mesma transação. Forçar erro de evento depois de iniciar as alterações e provar rollback. Cenário com resultado não recebido confirma o commit e nova autorização do iniciador.

Executar pares determinísticos com barreiras e timeout finito, sem sleeps arbitrários: troca×troca, troca×reset válido, troca×request e troca×retry de recuperação. Testar as duas ordens de commit. Interromper após autenticar e antes de bloquear para provar rejeição de contexto antigo. Link criado antes da troca é invalidado; pedido futuro segue o contrato existente. Sem deadlock, sem efeito parcial e sem aprovação de dois resultados incompatíveis.

### CI-05 — Recuperação afetada mantém contrato e revoga concessão

**Criteria:** CA-01, CA-09, CA-11.
**Proof:** arquivos existentes abaixo. São consumidores diretos dos bloqueios de token e da transição replace_password.

~~~bash
uv run pytest tests/identity/core/use_cases/test_reset_password_use_case.py tests/identity/core/use_cases/test_retry_password_recovery_use_case.py tests/identity/core/use_cases/test_request_password_recovery_use_case.py
uv run pytest tests/identity/server/controllers/test_reset_password_controller.py tests/identity/server/controllers/test_retry_password_recovery_controller.py tests/identity/server/controllers/test_request_password_recovery_controller.py
~~~

Manter os estados/respostas existentes, cooldown e prazos. Acrescentar prova de remoção da concessão no reset e revalidação após descoberta sem bloqueio. Sem escrever teste do repositório. Os arquivos já existentes só precisam mudar quando seus cenários/fixtures realmente dependam do contrato ampliado.

### CI-06 — JWT e sessão preservada pelo controlador consumidor

**Criteria:** CA-01, CA-08–CA-11, CA-14.
**Proof:** tests/identity/server/controllers/test_get_current_session_controller.py, ampliado.

~~~bash
uv run pytest tests/identity/server/controllers/test_get_current_session_controller.py
~~~

Usar JWT/JWKS reais da fixture local. Cobrir assinatura/emissor/audiência/expiração e tipos inválidos, conta inativa, versão corrente, par preservado exato, mesmo número com outro sid, versão errada no sid correto e concessão removida por reset. Token do iniciador reemitido pelo BFF com versão original continua válido. A resposta pública de /identity/session não ganha os campos internos. Confirmar que providers não recebem arquivo de teste próprio.

### CI-07 — Componentes, hooks proprietários e consumidores de foco

**Criteria:** CA-02, CA-04, CA-07, CA-12–CA-13.
**Proof:** novos componentes/hooks dos formulários e hook da página; componentes existentes da página e menu; contexto Auth existente; componentes Identity diretamente afetados pelo Input.

Da raiz:

~~~bash
pnpm --filter web exec vitest run src/ui/identity/widgets/pages/account-page/tests/account-page.test.tsx src/ui/identity/widgets/pages/account-page/tests/use-account-page.test.ts src/ui/identity/widgets/pages/account-page/profile-form/tests/profile-form.test.tsx src/ui/identity/widgets/pages/account-page/profile-form/tests/use-profile-form.test.ts src/ui/identity/widgets/pages/account-page/security-form/tests/security-form.test.tsx src/ui/identity/widgets/pages/account-page/security-form/tests/use-security-form.test.ts src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts src/ui/shared/widgets/layouts/app-layout/account-menu/tests/account-menu.test.tsx src/ui/shared/widgets/layouts/app-layout/account-menu/tests/use-account-menu.test.ts src/ui/identity/widgets/pages/sign-in-page/tests/sign-in-page.test.tsx src/ui/identity/widgets/pages/register-page/tests/register-page.test.tsx src/ui/identity/widgets/pages/reset-password-page/tests/reset-password-page.test.tsx src/ui/identity/widgets/pages/privacy-policy-page/tests/privacy-policy-page.test.tsx
~~~

Componentes com hook mockado e filhos reais. Hooks proprietários com matriz completa de estados e funções. Query/action hooks, Select, Input, adapters e cartão estrutural não ganham testes próprios. Reduzir movimento por padrão. Estados de transporte reais pertencem à rota e ao handler. Os três consumidores existentes de Input validam que a correção compartilhada de foco não rompe controles/nome acessível; foco visual também é verificado em VM-01/02. O componente da política confirma que extrair as constantes não muda contato ou conteúdo público.

### CI-08 — Página e navegação com transporte simulado

**Criteria:** CA-02–CA-04, CA-06–CA-07, CA-10, CA-12–CA-13.
**Proof:** tests/identity/account-page.test.ts e grupo afetado de tests/shared/app-layout.test.ts.

~~~bash
pnpm --filter web exec playwright test tests/identity/account-page.test.ts
~~~

Selecionar também os dois cenários de menu desktop/mobile já existentes, cujos títulos foram conferidos no código. Ampliá-los com o acesso navegável à conta e preservar seus títulos:

~~~bash
pnpm --filter web exec playwright test tests/shared/app-layout.test.ts --grep 'opens the shared account menu at the desktop viewport and restores focus on Escape|keeps account access beside mobile navigation at 390 x 844'
~~~

Nenhum outro cenário do Mentor nesse arquivo é selecionado por esse filtro.

Cobrir acesso anônimo/pendente/ativo, URL /account, abas, detecção de fuso, dados falsos ausentes, loading, cliente inválido, 400/403/401/503, resposta malformada e recuperação, draft preservado, pending/duplicação, senhas limpas, resultado incerto sem retry, nome no menu, links/contact e teclado em 390 px. Mocks precisam mudar depois de salvar. Nenhum pedido dessa suíte chama Identity real. Parâmetros dinâmicos, paginação e estado vazio de coleção são inaplicáveis. Não há estado vazio válido de perfil autenticado.

### CI-09 — Handler real, cookies e proteção de rotas paralelas

**Criteria:** CA-01–CA-02, CA-04, CA-06–CA-10, CA-13–CA-14.
**Proof:** novo tests/identity/account-auth-api.test.ts; banco/API reais, fixture compartilhada.

~~~bash
pnpm --filter web exec playwright test tests/identity/account-auth-api.test.ts tests/identity/password-recovery-auth-api.test.ts
~~~

A segunda suíte é consumidor real da transição de recuperação afetada. Criar duas sessões da mesma conta, mais controle de outra conta. Verificar cookie HttpOnly, ausência de JWT/segredos nos JSONs, origem/CSRF, método/corpo/status e persistência. Troca preserva cookie/sid/expiração da iniciadora e bloqueia os outros acessos por chamadas reais ao BFF/API. Testar nova emissão JWT da iniciadora, segunda troca, novo login e recuperação posterior.

Tentar /api/auth/update-session com accessVersion atual da conta, /update-user e /change-password nativo deve retornar 404 e não restaurar o acesso ou modificar o nome técnico/canônico. Injetar falha de cópia técnica no seam do handler e perda de resposta posterior ao commit sem mockar o banco bem-sucedido. A consulta posterior recupera o perfil; a sessão permanece. Não importar o provider só para testar seus métodos privados. A saída só é verificada no caminho normal já existente.

### CI-10 — Tipos dos projetos afetados

**Scope:** Server e Web, incluindo consumidores do contexto autenticado.

~~~bash
# apps/server
uv run poe check:types
# raiz
pnpm --filter web check:types
~~~

Ambos usam a configuração real do projeto. Não passar arquivos diretamente ao tsc para desativar a configuração. Não afrouxar strictness.

### CI-11 — Lint e formatação restritos aos arquivos

**Scope:** arquivos Python/TS/TSX criados ou alterados na árvore, mais os testes consumidores efetivamente corrigidos.

As seleções exatas abaixo abrangem a árvore planejada e os testes de regressão diretamente afetados. Arquivos novos só existem depois da implementação. Acrescentar à seleção o caminho real da revisão Alembic gerada em CI-14 e eventuais barrels/pipes que precisarem mudar, sempre registrando o diff. Excluir um caminho apenas quando sua mudança planejada se mostrar desnecessária e registrar essa disposição. Não adicionar diretórios inteiros.

De apps/server:

~~~bash
server_paths=(
  src/shifu/identity/core/domain/entities/account.py
  src/shifu/identity/core/domain/structures/account_profile_update.py
  src/shifu/identity/core/domain/structures/password_change_request.py
  src/shifu/identity/core/domain/structures/__init__.py
  src/shifu/identity/core/domain/errors/invalid_time_zone_error.py
  src/shifu/identity/core/domain/errors/__init__.py
  src/shifu/identity/core/interfaces/account_action_tokens_repository.py
  src/shifu/identity/core/use_cases/get_account_profile_use_case.py
  src/shifu/identity/core/use_cases/update_account_profile_use_case.py
  src/shifu/identity/core/use_cases/change_password_use_case.py
  src/shifu/identity/core/use_cases/reset_password_use_case.py
  src/shifu/identity/core/use_cases/retry_password_recovery_use_case.py
  src/shifu/identity/core/use_cases/__init__.py
  src/shifu/identity/database/sqlalchemy/models/account_model.py
  src/shifu/identity/database/sqlalchemy/mappers/account_mapper.py
  src/shifu/identity/database/sqlalchemy/repositories/account_action_tokens_repository.py
  src/shifu/identity/providers/auth/jwt/jwks/jwks_jwt_authentication_provider.py
  src/shifu/identity/rest/router.py
  src/shifu/identity/rest/controllers/get_account_profile_controller.py
  src/shifu/identity/rest/controllers/update_account_profile_controller.py
  src/shifu/identity/rest/controllers/change_password_controller.py
  src/shifu/shared/core/domain/structures/authenticated_user.py
  src/shifu/shared/core/interfaces/authentication_provider.py
  src/shifu/fakers/identity/entities/account_faker.py
  src/shifu/rest/handlers/app_error_handler.py
  tests/identity/core/use_cases/test_get_account_profile_use_case.py
  tests/identity/core/use_cases/test_update_account_profile_use_case.py
  tests/identity/core/use_cases/test_change_password_use_case.py
  tests/identity/core/use_cases/test_reset_password_use_case.py
  tests/identity/core/use_cases/test_retry_password_recovery_use_case.py
  tests/identity/core/use_cases/test_request_password_recovery_use_case.py
  tests/identity/server/controllers/test_get_account_profile_controller.py
  tests/identity/server/controllers/test_update_account_profile_controller.py
  tests/identity/server/controllers/test_change_password_controller.py
  tests/identity/server/controllers/test_get_current_session_controller.py
  tests/identity/server/controllers/test_reset_password_controller.py
  tests/identity/server/controllers/test_retry_password_recovery_controller.py
  tests/identity/server/controllers/test_request_password_recovery_controller.py
)
uv run ruff check --no-fix "${server_paths[@]}"
uv run ruff format --check "${server_paths[@]}"
~~~

Da raiz:

~~~bash
web_paths=(
  apps/web/src/core/errors/auth-error.ts
  apps/web/src/rest/services/identity-service.ts
  apps/web/src/provision/auth/cookie-session-auth-provider.ts
  apps/web/src/provision/auth/better-auth/better-auth-provider.ts
  apps/web/src/routes/account/index.tsx
  apps/web/src/ui/shadcn/input.tsx
  apps/web/src/ui/shadcn/select.tsx
  apps/web/src/ui/shared/hooks/use-navigation.ts
  apps/web/src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts
  apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/index.tsx
  apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/use-account-menu.ts
  apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/tests/account-menu.test.tsx
  apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/tests/use-account-menu.test.ts
  apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts
  apps/web/src/ui/identity/constants/privacy-contact.ts
  apps/web/src/ui/identity/widgets/pages/privacy-policy-page/index.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/index.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/use-account-page.ts
  apps/web/src/ui/identity/widgets/pages/account-page/use-account-profile-query.ts
  apps/web/src/ui/identity/widgets/pages/account-page/tests/account-page.test.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/tests/use-account-page.test.ts
  apps/web/src/ui/identity/widgets/pages/account-page/profile-form/index.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/profile-form/use-profile-form.ts
  apps/web/src/ui/identity/widgets/pages/account-page/profile-form/use-update-account-profile-action.ts
  apps/web/src/ui/identity/widgets/pages/account-page/profile-form/tests/profile-form.test.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/profile-form/tests/use-profile-form.test.ts
  apps/web/src/ui/identity/widgets/pages/account-page/security-form/index.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/security-form/use-security-form.ts
  apps/web/src/ui/identity/widgets/pages/account-page/security-form/use-change-account-password-action.ts
  apps/web/src/ui/identity/widgets/pages/account-page/security-form/tests/security-form.test.tsx
  apps/web/src/ui/identity/widgets/pages/account-page/security-form/tests/use-security-form.test.ts
  apps/web/src/ui/identity/widgets/pages/account-page/privacy-card/index.tsx
  apps/web/tests/fixtures/identity-module-fixture.ts
  apps/web/tests/identity/account-page.test.ts
  apps/web/tests/identity/account-auth-api.test.ts
  apps/web/tests/shared/app-layout.test.ts
)
pnpm exec biome check "${web_paths[@]}"
~~~

Passa quando a seleção reconciliada cobrir todos os arquivos afetados suportados sem erros e sem reescrever arquivos. A lista efetivamente executada faz parte da evidência.

### CI-12 — Complexidade configurada

**Scope:** lógica afetada de autorização, bloqueios, BFF e hooks.
**Tool:** mesmo Ruff de CI-11, C90 selecionado, limite McCabe 10. Ruff 0.16.7 coincide com uv.lock e ruff check --show-settings confirmou linter.mccabe.max_complexity=10 no worktree durante a autoria. Biome 2.2.3 aplica as regras complexity configuradas em biome.json, em avisos quando assim configuradas.

Registrar diagnóstico e severidade separados do resultado de lint. Não introduzir limite quantitativo Web, baseline, percentual ou check:complexity inexistentes. Não há gate independente de métricas requerido nesta entrega. Se surgir obrigação de ferramenta indisponível, mantê-la Blocked e reconciliar explicitamente; revisão manual não prova métrica.

### CI-13 — Arquitetura, construção e integridade de testes

~~~bash
# raiz
pnpm check:test-integrity
pnpm --filter web check:architecture
pnpm --filter web build
# apps/server
uv run poe check:architecture
uv run poe build
~~~

Sem ciclos, novas dependências entre módulos, testes de fontes indiretas ou saídas geradas manuais. Os exports, novos controladores e composição devem construir. Checks de lint de projeto configurados por CI continuam aplicáveis na publicação; a autoria não os executa.

### CI-14 — Migração e compatibilidade em base descartável

**Criteria:** CA-15.
**Tool:** Alembic existente, SQL de inspeção e testes de controlador CI-03/04 sobre schema migrado. Não criar arquivo de teste da migração.

Em PostgreSQL descartável, aplicar o head anterior, criar conta representativa com valores preservados, gerar/aplicar a revisão e executar uv run alembic upgrade head e uv run alembic check com DATABASE_URL explicitamente isolado. Inspecionar as duas colunas e a restrição. Testar pares inválidos e round-trip por HTTP; rodar uv run alembic downgrade -1 e upgrade head nesse ambiente e comparar credenciais/perfil/dados históricos. Não usar a conexão compartilhada nem remover migrações antigas. Resultado precisa identificar os hashes reais gerados. O downgrade pode revogar sessões dependentes da concessão; essa perda de autorização é esperada.

## Manual

### VM-01 — Editar Perfil e alcançar privacidade

**Type:** Manual. **Criteria:** CA-02, CA-04, CA-06, CA-12–CA-13.

Playwright CLI em apps/web, sessão nomeada shifu97 e conta própria do Shared setup. Carregar storage state local existente somente se pertencer à conta preparada; caso contrário entrar pela tela visível e salvar estado novo sob .playwright-cli/states/.

Abrir /account pelo menu. Em 1440×900 e 390×844, conferir perfil, selecionar fuso, editar nome e salvar. Verificar o nome no menu, reabrir Perfil e conferir dados persistidos pela resposta real. Usar Tab/setas/Enter no seletor e nas abas. Conferir destino /privacy e URI de contato, sem enviar mensagem. Capturar os estados D-01/D-03.

Passa com URL e conteúdo corretos, requests/respostas reais, rótulos e foco visíveis, sem overflow, segredo na URL ou erro de console inesperado. Registrar paths das capturas e erros classificados. Usar somente comandos suportados pelo playwright-cli instalado.

### VM-02 — Trocar senha e continuar no acesso atual

**Type:** Manual. **Criteria:** CA-08, CA-12.

Na mesma conta descartável, abrir Segurança em desktop/mobile. Informar senha atual e uma nova válida. Confirmar sucesso e mensagem sobre os outros acessos. Navegar para Perfil e recarregar para provar continuidade do acesso atual. Senhas não permanecem nos campos nem nos artefatos. Capturar D-02/D-04 antes da ação com campos vazios, sem divulgar credenciais.

Passa com resposta real confirmada, cookie preservado e nova leitura autenticada. A matriz de revogação negativa pertence a CI-04/06/09. Ao fim, executar cleanup do Shared setup, fechar a sessão CLI e somente os processos iniciados para a tarefa; preservar serviços compartilhados. Não restaurar senha de uma conta compartilhada porque ela não foi usada.

## Visual

### VM-03 — Perfil desktop e mobile

**Type:** Visual. **Criteria:** CA-12–CA-13.
Comparar capturas atuais de VM-01 a D-01 e à adaptação D-03 no handoff. Inspecionar título, largura editorial interna, cartões, espaçamentos, e-mail somente leitura, seletor, foco e bloco de privacidade. Respeitar os desvios listados e movimento reduzido. Salvar screenshot sem inspecioná-la não passa.

### VM-04 — Segurança desktop e mobile

**Type:** Visual. **Criteria:** CA-12.
Comparar capturas de VM-02 a D-02 e D-04. Inspecionar duas senhas, texto explicativo, ação primária, foco e adaptação sem overflow. Não acrescentar abas/ações excluídas para copiar a imagem. Estados negativos são automatizados, sem novos percursos manuais.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Shifu — PRD — Identity](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83001345/Shifu+PRD+Identity), content ID 83001345, versão 2; leitura completa em 25/10/2026 nesta sessão, versão novamente confirmada às 21:39 UTC | RP-05/06/07/10/11; JN-05/06 | Confirmar versão antes de ready/conclusão; sem copiar PRD ou editar checkboxes | Pai 82804737, “PRD's”, verificado pelo grafo e leitura; atualização da página 04/10/2026 22:58:18.420 UTC, mensagem “Aplicar política comum de privacidade, atendimento e ciclo de vida dos dados” |
| [SHIFU-97](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-97), issue 12607 | Escopo e exclusões desta entrega | Pai SHIFU-24; atualizado em 24/10/2026 00:18:17.768 -03; ticket referência PRD v2 | Leitura completa; nenhuma escrita Jira autorizada ou realizada |
| [SHIFU-96](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-96) e [Spec existente](../privacy-policy-page/spec.md) rev. 3 | Política, contato e pontos de acesso | Reutilizar implementação existente, sem assumir sua disposição só pelo Jira | Jira Concluído; rota e link de conta confirmados em source. Divergência de retenção registrada naquele contrato fica fora desta entrega |
| [SDD](../../../sdd.md), [Architecture](../../../architecture.md), [Modules](../../../modules.md), [Tooling](../../../tooling.md), [Rules router](../../../rules.md) | Propriedade, formato, fronteiras e seleção de comandos | Confirmar alinhamento | Nenhuma alteração dessas autoridades |
| [Python](../../../rules/python-conventions-rules.md), [Core](../../../rules/core-layer-rules.md), [Use case tests](../../../rules/use-case-testing-rules.md) | Declarações, estruturas, casos de uso e ports | Um arquivo por estrutura; testes nos casos de uso | Sem testes diretos de domínio nesta entrega |
| [REST](../../../rules/rest-layer-rules.md), [Controllers tests](../../../rules/controllers-testing-rules.md), [Server app](../../../rules/server-app-layer-rules.md) | HTTP, erros, composição e provas reais | Response local e TypeAdapter; wiring explícito | Sem controller usando SQLAlchemy ou tratamento local de falha |
| [Database](../../../rules/database-layer-rules.md), [Provision](../../../rules/provision-layer-rules.md), [Messaging](../../../rules/messaging-layer-rules.md) | Transações, migração, autenticação e cancelamentos | Uma transação Identity; provider compacto; eventos existentes | Sem arquivo de teste de provider/repositório/migração; nenhum job novo |
| [TypeScript](../../../rules/typescript-conventions-rules.md), [UI](../../../rules/ui-layer-rules.md), [Routing](../../../rules/web-app-routing-rules.md), [Widget tests](../../../rules/widget-testing-rules.md), [Design](../../../design.md) | Página, composição, foco, navegação e testes | Handoff e árvore espelhados nos testes; correção de foco compartilhada localizada | O trecho antigo de Design T08 menciona Sair de todos, mas RP-06 e o ticket excluem controles novos. Referência UI @hms/core é resolvida pelo HTTP_STATUS_CODE local existente, sem importar pacote inexistente |
| [Handoff](design/handoff.md) e Pencil Zhv5S/w3b63H | Intenção visual | Duas referências salvas e inspecionadas; adaptação mobile explícita | Ausência da aba Excluir conta é desvio aceito pelo escopo |
| Better Auth 1.6.23 instalado; documentação versionada via Context7; [Base UI Select](https://base-ui.com/react/components/select), versão 1.8.0 consultada | API técnica e campos de sessão | Bloquear writes genéricos e usar primitives instalados | Fonte instalada confirma update-session/update-user. Não atualizar dependências incidentalmente |

Base pesquisada: 8ee992a750bd526aafcf1b5db396677a3ebdc3c1. Worktree codex/shifu-97-account-spec, separado do checkout original com mudanças do usuário preservadas. O worktree não tem .codegraph. A pesquisa inicial usou o índice existente do original antes das buscas, confirmou o mesmo HEAD e verificou as fontes no worktree. Consultas: perfil/senha/sessão Identity; recuperação e bloqueios; consumidores de access_version; BetterAuthProvider; composição do perfil e menu; primitives e testes. O índice não cobriu CSS e teve resultados amplos incompletos; os caminhos exatos e configurações foram lidos localmente. Não criar ou reconstruir índice.

Revisão independente de compatibilidade concluída em 25/10/2026 sobre a revisão 1. O Spec Reviewer auditou arquitetura, propriedade, direção de dependências, árvore, declarações, todas as regras selecionadas e limites de teste. A observação sobre nomes genéricos da consulta foi corrigida e revalidada. Não restam achados de compatibilidade. Essa revisão é de contrato e não constitui prova de implementação ou de fidelidade visual em execução.

O usuário aprovou o contrato escrito ao invocar implement-spec em 25/10/2026. A revisão1 está implementada com provas e revisões registradas em Evaluation. A invocação explícita conclude-spec autorizou sincronização, commits e PR. A manutenção dos14testes foi autorizada em seguida. O usuário aprovou reduzir somente o mínimo de Recall@10 do eval existente de0.90para0.89; RF/CA e revisão da funcionalidade permanecem inalterados. Publicação e CI remoto ainda pendentes. Jira/Confluence não foram alterados.

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-25 | Contrato inicial de perfil e segurança, sessão preservada atomicamente, fuso sugerido sem gravação automática e cobertura focada | SHIFU-97; PRD Identity v2; escopo aprovado e recomendações aceitas pelo usuário |
