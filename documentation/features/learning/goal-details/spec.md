---
title: SHIFU-64 — Detalhes do Objetivo com Grafo e Lista
status: ready
revision: 5
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-64
scope:
  - apps/web
  - apps/server/src/shifu/learning
  - apps/server/src/shifu/curriculum/providers
  - apps/server/src/shifu/shared/core
last_updated_at: 2026-09-24
---

# 1. Context and scope

## Autoridade e objetivo

Modo **complete**; proprietário **Learning**. Entregar leitura autenticada de um Objetivo real, com Grafo e Lista equivalentes, substituindo os placeholders. A implementação ocorre em outra sessão; esta revisão não declara código ou testes concluídos.

| Fonte | Identificação verificada | Papel |
| --- | --- | --- |
| [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning) | content ID 83066881; versão 17; atualizado 2026-09-24T00:48:56.368Z; parent 82804737 | Intenção de produto; leitura integral, consulta 2026-09-24 |
| [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113) | content ID 83034113; versão 9; atualizado 2026-09-23T23:39:01.079Z; parent 82804737 | Conteúdo e relações oficiais; leitura integral, consulta 2026-09-24 |
| [SHIFU-64](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-64) | Fazendo; atualização 2026-09-22T22:32:14.372-0300 | Recorte full-stack; ligada a SHIFU-35 |
| Usuário e orientação de Petros reproduzida neste chat | Decisões confirmadas em 2026-09-23; [registro](../../../../SHIFU-64.md) | Rota goals, ações futuras desabilitadas, eliminação de placeholders, redirect legado |

A consulta de Learning e Curriculum foi reconfirmada em 2026-09-24. A revisão 3 reconcilia as versões 17/9: RP-01, RP-03, RP-04, RP-05, RP-15, RP-25 e JN-03 preservam o recorte desta entrega. A mudança de Learning v17 sobre material introdutório opcional não altera esta página. A projeção permanece leitura do progresso já decidido por Learning; ela não recalcula evidências, cobertura, domínio ou recomendação no endpoint ou no browser. IDs RP/JN sem prefixo de módulo nesta Spec pertencem a Learning.

## Recorte de entrega

| Área | Incluído | Excluído |
| --- | --- | --- |
| Objetivo | Leitura privada, título/descrição, vazio e recuperação | Criação, edição, remoção e progresso/conclusão agregados |
| Habilidades | Nomes, quatro estados, progresso quando learning, relações e navegação | Diagnóstico, detalhes internos da Habilidade, mutações e edição curricular |
| Ações | Adicionar como navegação; Remover objetivo e … visíveis desabilitados | Abrir menus, confirmar ou executar operações futuras |
| Navegação | Substituir detalhe placeholder; /learning → Home | Selecionar automaticamente um Objetivo; rota concorrente objectives |
| Grafo | Layout automático, pan por arrasto no canvas vazio, restauração da vista inicial, destaque temporário do caminho de pré-requisitos em hover/foco, zoom, teclado/mobile, alternativa Lista | Arrastar nós, conectar/remover arestas, salvar posições/zoom/aba |
| Shell | Reutilizar shell atual | Reformular navegação global, Mentor ou Gamification |

| Requisito de origem | Disposição nesta entrega | Limite |
| --- | --- | --- |
| RP-01 | partial | Leitura de título/descrição e Objetivo vazio; sem criação/edição |
| RP-03, JN-03 | partial | Isolamento das experiências e apresentação, sem adicionar/remover |
| RP-04 | full | Relações, Habilidades desconectadas, Grafo padrão e Lista |
| RP-05 | partial | Mostrar etapa já persistida; não executar transições |
| RP-15 | partial | Projetar média de progressos atuais; não recalcular avaliações |
| RP-25 | partial | Responsividade, acessibilidade e estados desta página |
| Curriculum RP-01 / RP-04 | partial | Consultar nomes, competências e relações, sem alterar conteúdo |
| RP-21 / RP-22 | deferred | Somente affordances desabilitadas; remoção não entregue |

## Decisões fechadas

- Rota canônica: `/learning/goals/$goalId`. Jira ainda cita `objectives` e PRD v6: registrar divergência, sem mutação externa automática.
- O placeholder específico é substituído; o genérico é removido e `/learning` passa a redirecionar para `/` após autenticação.
- **Razão do redirect:** o endereço sem ID não identifica o recurso. Encaminhar à Home preserva links antigos e permite escolha explícita, sem inventar “primeiro/último Objetivo”.
- Remoção e menus ficam visualmente prontos, semanticamente desabilitados, sem handlers fictícios ou requisições. Isso antecipa apresentação, não comportamento de outras tasks.
- Não persistir aba ou zoom; Grafo padrão também no mobile.
- SHIFU-65 é dependência de integração da navegação de adição, não autorização para implementá-la aqui.

# 2. Implementation Contract

## Requisitos funcionais

| ID | RP/JN/source coverage | Required behavior |
| --- | --- | --- |
| RF-01 | RP-01, RP-03, JN-03; SHIFU-64 isolamento | Consultar apenas Objetivo do usuário ativo autenticado; ausência e outro dono não revelam dados |
| RF-02 | RP-01, RP-04 | Exibir título e descrição sem métrica agregada; Objetivo vazio continua acessível |
| RF-03 | RP-04; Curriculum RP-01/RP-04 | Mostrar apenas Habilidades incluídas e relações oficiais com ambos extremos presentes, inclusive desconectadas |
| RF-04 | RP-03, RP-05, RP-15 | Exibir estados individuais; barra somente em aprendizado, com média de todas as Competências da experiência |
| RF-05 | RP-04, RP-25 | Grafo inicial em cada abertura; Lista equivalente; alternância não persistida |
| RF-06 | RP-04, RP-25; SHIFU-64 zoom/layout; solicitações do usuário | Grafo organizado automaticamente; canvas vazio pode ser arrastado para deslocar a vista; ícone restaura enquadramento e zoom iniciais com tooltip; hover ou foco de uma Habilidade destaca com traço animado temporário as arestas de todos os seus pré-requisitos até o Objetivo, sem destacar ramos não relacionados; movimento é removido quando o usuário prefere movimento reduzido; nós não podem ser rearranjados, inclusive por teclado |
| RF-07 | RP-25; SHIFU-64 estados | Loading, erro seguro recuperável, ausência privada e recuperação sem dados obsoletos de outro recurso |
| RF-08 | RP-04, JN-03; SHIFU-64 navegação | Abrir Habilidade no mesmo Objetivo; adicionar navega ao fluxo responsável, inclusive no vazio |
| RF-09 | RP-25; decisão do usuário | Interface pt-BR acessível; Remover objetivo e menus … visíveis desabilitados |
| RF-10 | RP-01/RP-04; decisão do usuário | Eliminar os dois placeholders; detalhe real e redirect autenticado do endereço genérico |

## Critérios observáveis

| ID | RF coverage | Requirement | Given | When | Then | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Isolamento | Contas A/B, Objetivo de A e ID ausente | A, B e anônimo consultam | A recebe seu dado; B/ausente têm mesmo 404 sem título/skills; sessão ausente é rejeitada; nada é escrito | Use case, controller, handler; VM-01 |
| CA-02 | RF-02 | Cabeçalho e vazio | Objetivo vazio/preenchido | Abrir página | Título/descrição reais; nenhuma métrica do Objetivo; vazio tem ação de adição | Página/rota; VM-02 |
| CA-03 | RF-03 | Projeção curricular | Relações A→C/B→C, relação externa e skill isolada | Alternar viewport/modo | Apenas extremos incluídos; isolada preservada; mobile mantém mesmas relações, sem bloqueios | Use case/controller/grafo/rota; VM-03 |
| CA-04 | RF-04 | Estados e média | Quatro estados; learning com progressos 30 e 90, um bloqueado | Abrir Grafo/Lista | Rótulos corretos; barra learning=60; outros sem barra; outra experiência não contribui | Use case/controller/SkillStatus/página; VM-03 |
| CA-05 | RF-05 | Aba não persistida | Página aberta | Mudar para Lista, sair/voltar, recarregar ou trocar goalId | Lista equivalente; cada nova abertura inicia Grafo; sem storage/search de preferência | Hook/rota; VM-03 |
| CA-06 | RF-06 | Grafo somente leitura | Grafo pronto com cadeia e ramo separado | Usar +/-, arrastar o canvas vazio, ativar o ícone de restauração e passar o ponteiro/foco por uma Habilidade | A vista desloca sem mover nós individualmente; ícone mostra tooltip e restaura enquadramento/zoom iniciais; somente o caminho de pré-requisitos da Habilidade até o Objetivo recebe destaque animado temporário, também por teclado; preferência de movimento reduzido mantém destaque estático; percentual reflete viewport real; nós/arestas não são editados | Grafo/hook/rota; VM-03 |
| CA-07 | RF-07 | Falha e recuperação | Consulta lenta, 503, 429 ou layout falho | Abrir e tentar novamente | Loading anunciado; erro seguro; retry funciona; sem spinner infinito, dados privados antigos ou promessas não tratadas | Página/rota/controller/handler; VM-02 |
| CA-08 | RF-08 | Destinos | Objetivo real com skills | Abrir skill e Adicionar | Rotas /learning/goals/$goalId/skills/$skillId e /skills/add, mantendo IDs; não inicia diagnóstico ou mutação | Rotas/handler; VM-04 |
| CA-09 | RF-09 | Acessibilidade e ações futuras | Desktop/mobile, quatro estados | Teclado, toque e controles desabilitados | Foco visível; nomes/status textuais; abas acessíveis; menus/remoção não abrem nem requisitam; nome do ícone acessível | Página/grafo/SkillStatus/rota; VM-03 |
| CA-10 | RF-10 | Migração de navegação | Endereço /learning e link da Home | Entrar autenticado/anônimo | Autenticado chega à Home, anônimo ao login; card abre detalhe real; nenhum placeholder remanescente ou loop | Suites de learning e goal-detail; VM-01 |

## Design Contract

Inventário, tokens, correções de inconsistências e screenshots em [design/manifest.md](design/manifest.md). Sete referências originais exportadas em escala 1, sem editar `design/shifu.pen`. Os frames demonstram composição, não autorizam comportamento contrário ao PRD.

Ações desabilitadas usam `disabled`, ícone e nome acessível; explicação “Disponível em uma próxima atualização” em texto de apoio acessível. Não aninhar botão em link. Apenas links/nome da Habilidade navegam. Loading inicial usa skeleton no cabeçalho: não inventar título já que a resposta é atômica. Diagnosing usa neutro + ícone, conforme design.md, em vez do latão do mockup. Foco segue token Selo, não apenas o destaque sutil do frame.

Lista apresenta justificativa de inclusão somente leitura quando existente, conforme design.md; nunca inventa justificativa para inclusão manual. Grafo mantém título completo acessível, sem copiar a abreviação fixa do exemplo mobile. Estados suplementares estão especificados no manifest e terão screenshots runtime; não alegar que há mockups originais para eles.

# 3. Technical Contract

## Base e versões

Base: `05d36a2d63f8c1b442ca1b4205b0658590d77751`, `main`. [Diagnóstico detalhado](../../../../SHIFU-64.md). Já existem LearningDatabase, CurriculumDatabase, CurriculumContentProvider, serviço Learning, server functions autenticadas e QueryClient no RootLayout. Não reconstruí-los.

Root lockfile resolve TanStack Start 1.168.56 e Router 1.170.38; manifesto declara React Query ^5.103.2. React Flow/ELK/Radix Tabs serão dependências novas, instaladas apenas na implementação, com versões compatíveis resolvidas e registradas no lockfile. Não declarar uma versão ainda não instalada.

## Fluxo e fronteiras

Browser → GoalDetailPage/hook → query → server function GET → provision server-only → LearningService/Axios → FastAPI controller → GetGoalDetailUseCase → LearningDatabase + porta Shared implementada por Curriculum.

| Fronteira | Produtor → consumidor | Contrato | Garantias/falhas |
| --- | --- | --- | --- |
| Curricular | DatabaseCurriculumContentProvider → use case | CurriculumSkillOverview[] | Metadados mínimos, sem estado do usuário ou conteúdo de questões |
| Aplicação | GetGoalDetailUseCase → controller | GoalDetail imutável | Ownership antes de consultar Curriculum; ausência privada; falha segura |
| API | GET /learning/goals/{goal_id} → LearningService | JSON GoalDetail camelCase | 200, 401/403 auth, 404 privado, 422 entrada, 429 limite existente, 503 infraestrutura |
| BFF | getGoalDetail → query | GoalDetailResult | Sessão por request; nunca retorna JWT/cookies/configuração |
| UI | query → página/filhos | GoalDetail e estados locais | Mesmos dados Grafo/Lista; nenhuma regra pedagógica no browser |

### Schema completo e leitura

Python usa `@structure`, tuplas, Decimal e enums existentes. Campos Python snake_case; HTTP usa aliases camelCase. Uma estrutura por arquivo, sem bare `id` em novas estruturas.

- `CurriculumSkillOverview`: `skill_id: str`, `name: str`, `competency_ids: tuple[str, ...]`, `foundation_skill_ids: tuple[str, ...]`.
- `GoalSkillDetail`: `skill_experience_id: str`, `skill_id: str`, `name: str`, `status: SkillExperienceStatus`, `progress: Decimal | None`, `inclusion_reason: str | None`.
- `GoalSkillRelation`: `foundation_skill_id: str`, `skill_id: str`.
- `GoalDetail`: `goal_id: str`, `title: str`, `description: str`, `skills: tuple[GoalSkillDetail, ...]`, `relations: tuple[GoalSkillRelation, ...]`.
- `CurriculumContentProvider.get_skill_overviews(skill_ids: tuple[str, ...]) -> tuple[CurriculumSkillOverview, ...]`: retorna somente IDs pedidos encontrados, sem duplicatas; faltantes são detectados pelo use case; lista vazia não faz consulta. `get_skill_content` permanece inalterado.
- `GetGoalDetailUseCase(database: LearningDatabase, curriculum_content_provider: CurriculumContentProvider).execute(account_id: str, goal_id: str) -> GoalDetail`.
- `GoalDetailResult` TS: `{kind:'success'; detail:GoalDetail}` ou `{kind:'unauthorized'|'forbidden'|'not-found'|'invalid-request'|'unavailable'; statusCode?:number}`. Nenhuma exceção bruta serializada.

JSON de sucesso: `{goalId,title,description,skills:[{skillExperienceId,skillId,name,status,progress,inclusionReason}],relations:[{foundationSkillId,skillId}]}`. `progress` é número finito de 0 a 100 somente em learning; é `null` nos demais estados. Enum técnico: `not-started|diagnosing|learning|completed`. Aresta visual orientada foundationSkillId → skillId. Não retornar accountId, respostas, atividades ou histórico.

Usar os métodos atuais de repos: goals.find_by_id, skill_experiences.find_many_by_goal_id, competency_progresses.find_many_by_skill_experience_id; no adapter curricular, skills.find_by_id, competencies.find_many_by_skill_id, skill_foundations.find_many_by_skill_id. Não introduzir migrations/modelos ou novas queries genéricas sem necessidade demonstrada.

O use case valida dono antes de consultar relações; valida goal_id de cada experiência; mantém uma experiência por skill. Ordena skills por nome casefold e skill_id para estabilidade de apresentação, sem prioridade pedagógica. Dedupe relações por par, filtrar ambos extremos e ordenar por IDs. Não percorrer bases recursivamente.

Para learning, ler progressos da própria experiência e calcular média Decimal dos valores current_progress de **todas** as competências oficiais. Não usar média dos registros disponíveis, somente liberadas, tentativas ou outro Objetivo. Metadado ausente, IDs duplicados, conjunto de progresso incompleto ou valor inválido tornam a projeção indisponível: `ServiceUnavailableError`, sem inventar zero ou resultado parcial. Não aplicar arredondamento pedagógico: somente apresentação pode arredondar.

Cada database existente controla sua transação e encerra sua sessão. O adapter curricular faz uma leitura consistente de seu catálogo; nenhuma escrita curricular. A operação de Learning é leitura, sem timestamps novos, eventos, outbox, diagnóstico ou atualização de progresso. Não promete snapshot global entre bancos: currículo estável do MVP; uma atualização de aprendizado concorrente pode aparecer na próxima consulta. Consultas repetidas não geram efeitos.

### HTTP, autenticação e BFF

Controller síncrono com handler `_`, path pattern de ID igual ao endpoint atual de Competência (`^[0-9A-Z]{26}$`), dependências tipadas AuthenticationPipe/LearningPipe e status 200 explícito. Response e modelos aninhados ficam no controller; `TypeAdapter.validate_python(..., from_attributes=True)` adapta estrutura e aliases, com Decimal serializado como número finito. Não reconstruir um DTO paralelo no serviço web.

Reutilizar GoalNotFoundError (subclasse de NotFoundError), ServiceUnavailableError e AppErrorHandler existentes. Não adicionar try/except no controller ou alterar handler global sem contrato adicional. Ausente/outro dono usam mesmo 404/code/message. Nenhuma busca por accountId recebido do browser.

Provision compõe `AxiosRestClient(BetterAuthConfig().identityURL, {withCredentials:false})` com LearningService; identityURL é atualmente o endereço do mesmo FastAPI, como em Competência. Reutilizar configuração existente sem nova env nesta entrega; o nome imperfeito é dívida documentada, não razão para propagar segredos ao browser. Provider recebe Request e goalId, obtém sessão via getBetterAuthProvider e usa accessToken só no header entre servidores.

Server function valida entrada desconhecida antes do uso, obtém getRequest no handler, carrega provider exclusivamente no lado servidor e traduz falhas para GoalDetailResult. Headers de sucesso do BFF/API: `Cache-Control: private, no-store`; nunca cache HTTP compartilhado. Nenhum token em payload, logs, URL, state ou storage do cliente. Guard de rota permanece sem retorno do JWT.

Query exclusiva da página: chave `['learning','goal-detail',goalId,instanceScope]`, escopo estável apenas durante a montagem; `gcTime:0`, `staleTime:0`, sem placeholderData, persistência ou retry automático. Retry é explícito, botão desabilitado enquanto pendente. Abandonar resultados obsoletos ao trocar goalId/desmontar. Erro 401/403 esconde dados e encaminha pelo wrapper de navegação ao login; 404/422 gera ausência privada; 429/5xx/falha de rede gera erro recuperável. Em qualquer erro, não renderizar query.data antigo como sucesso. Cada volta da adição refaz leitura.

### Widgets e responsabilidades

| Widget | Kind | Parent/entry | Direct children | Public contract | Behavior owner |
| --- | --- | --- | --- | --- | --- |
| GoalDetailPage | Page | Rota parametrizada | Header, Switcher, Feedback, List ou Graph | goalId:string | useGoalDetailPage |
| GoalDetailHeader | Component interno | Página | Button/Icon existentes | title, description; botão disabled fixo | Puro |
| GoalViewSwitcher | Component interno | Página | Tabs primitives + Link de adição | goalId, view:graph/list, onViewChange | Página |
| GoalDetailFeedback | Component interno | Página | Ícone, textos, links/retry | state, goalId, isRetrying, onRetry | Página |
| GoalSkillList | Component interno | Página | GoalSkillRow | goalId, skills | Puro |
| GoalSkillRow | Component interno | Lista | SkillStatus, link, progress, botão disabled | goalId, skill | Puro |
| GoalSkillGraph | Component interno com comportamento | Página | ReactFlow, GoalGraphNode, GoalGraphControls | goalId,title,skills,relations | useGoalSkillGraph |
| GoalGraphNode | Component interno | ReactFlow | SkillStatus ou contexto do Objetivo | união de data tipo goal/skill; goalId e dados tipados | Puro |
| GoalGraphControls | Component interno | Grafo | Botões +/- e percentual | zoom, canZoomIn/Out, onZoomIn/Out | Hook do grafo |
| SkillStatus | Component Learning reutilizado | Node/Row | Icon e rótulo | status:SkillExperienceStatus | Puro; mapa de apresentação |

Árvore de arquivos novos da página (cada entrada corresponde a uma linha do ledger):

```text
apps/web/src/ui/learning/widgets/pages/goal-detail-page/
index.tsx
use-goal-detail-page.ts
use-goal-detail-query.ts
tests/goal-detail-page.test.tsx
tests/use-goal-detail-page.test.ts
goal-detail-header/index.tsx
goal-view-switcher/index.tsx
goal-detail-feedback/index.tsx
goal-skill-list/index.tsx
goal-skill-list/goal-skill-row/index.tsx
goal-skill-graph/index.tsx
goal-skill-graph/use-goal-skill-graph.ts
goal-skill-graph/goal-graph-node/index.tsx
goal-skill-graph/goal-graph-controls/index.tsx
goal-skill-graph/tests/goal-skill-graph.test.tsx
goal-skill-graph/tests/use-goal-skill-graph.test.ts
apps/web/src/ui/learning/widgets/components/skill-status/
  index.tsx
  tests/skill-status.test.tsx
apps/web/src/ui/learning/constants/skill-status-presentation.ts
```

useGoalDetailPage expõe detail, state (loading/success/empty/not-found/error), view, isRetrying, handleViewChange, handleRetry; hook da query expõe goalDetail, goalDetailError, isLoadingGoalDetail, isFetchingGoalDetail, refetchGoalDetail. Valores antes de handlers; destructuring direto. O hook da página trata UI, não autorização de domínio. Remount por goalId reinicia aba e escopo da query.

ELK e React Flow ficam no hook/componente do grafo; nenhum SDK no core. Layout top-down, dimensões reais de nós, sem coordenadas fixas copiadas do exemplo. `nodesDraggable=false`, `nodesConnectable=false`, proibir remoção/reconexão, desabilitar seleção de arestas sem função. Preservar navegação acessível por links e não desligar acessibilidade global. Zoom entre 0,25 e 2, passos por botões do viewport e percentual real arredondado; fit inicial respeita viewport, não rotular sempre 100%. Controles continuam utilizáveis em mobile, com alvos de 44px.

Nó contextual do Objetivo separado semanticamente das skills; conexões decorativas para raízes não são relações de pré-requisito. Relações entre skills são exatamente as retornadas pelo servidor em qualquer viewport. ELK não filtra nem altera relações. Calcular em mudança de dados/dimensões relevantes, não continuamente; descartar promise antiga após unmount/novos dados. Em falha de layout, mensagem “Não foi possível organizar o grafo”, retry e Lista continuam acessíveis.

Nenhuma rota de adição será criada por SHIFU-64. O Link tipado para /skills/add requer rota da SHIFU-65 integrada; não usar cast para esconder sua ausência no route tree. A integração é gate antes de compilar a navegação definitiva. Rota de skill existente é somente destino: não substituir sua implementação/placeholder em outra task.

## Affected paths

Ledger único de implementação; caminhos inexistentes são propostas Create, não afirmações de código já disponível. SDD permanece propriedade do Orchestrator.

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/tests |
| --- | --- | --- | --- | --- |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_skill_overview.py` | Create | CurriculumSkillOverview | Snapshot mínimo curricular; schema abaixo | CurriculumContentProvider |
| `apps/server/src/shifu/shared/core/domain/structures/__init__.py` | Modify | Re-export CurriculumSkillOverview | Export explícito, sem I/O | provider e use case |
| `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py` | Modify | get_skill_overviews(skill_ids) | Adicionar método sem alterar get_skill_content | adapter curricular e Learning |
| `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Modify | DatabaseCurriculumContentProvider.get_skill_overviews | Ler habilidades, IDs de competências e bases diretas em uma transação curricular | port Shared; teste pelo controller Learning |
| `apps/server/src/shifu/learning/core/domain/structures/goal_detail.py` | Create | GoalDetail | Projeção imutável de leitura | use case e Response |
| `apps/server/src/shifu/learning/core/domain/structures/goal_skill_detail.py` | Create | GoalSkillDetail | Estado e progresso individual; sem bare id | GoalDetail |
| `apps/server/src/shifu/learning/core/domain/structures/goal_skill_relation.py` | Create | GoalSkillRelation | Par foundation_skill_id / skill_id | GoalDetail |
| `apps/server/src/shifu/learning/core/domain/structures/__init__.py` | Modify | Re-exports das três estruturas | Sem definições no barrel | use case e controller |
| `apps/server/src/shifu/learning/core/use_cases/get_goal_detail_use_case.py` | Create | GetGoalDetailUseCase.execute(account_id, goal_id) | Autorização, projeção e cálculo de leitura | LearningDatabase + CurriculumContentProvider |
| `apps/server/src/shifu/learning/core/use_cases/__init__.py` | Modify | Re-export GetGoalDetailUseCase | Preservar demais exports | controller |
| `apps/server/src/shifu/learning/rest/controllers/get_goal_detail_controller.py` | Create | GetGoalDetailController; Response | GET /goals/{goal_id}, TypeAdapter e aliases camelCase | AuthenticationPipe, LearningPipe |
| `apps/server/src/shifu/learning/rest/controllers/__init__.py` | Modify | Re-export GetGoalDetailController | Preservar controllers existentes | LearningRouter |
| `apps/server/src/shifu/learning/rest/router.py` | Modify | LearningRouter.register | Registrar controller uma vez por aplicação | FastAPIApp existente |
| `apps/server/rest-client/learning/learning.rest` | Modify | Exemplos GET collection e detail | Preservar listagem; adicionar detalhe e variáveis não secretas | paridade HTTP |
| `apps/server/tests/learning/core/use_cases/test_get_goal_detail_use_case.py` | Create | TestGetGoalDetailUseCase | Mocks autospec dos ports; CA-01 a CA-04 e CA-07 | CI-S |
| `apps/server/tests/learning/server/controllers/test_get_goal_detail_controller.py` | Create | TestGetGoalDetailController | HTTP real + PostgreSQL descartável; sem teste direto do provider | CI-S |
| `apps/web/src/core/learning/goal-detail.ts` | Create | GoalDetail, GoalSkillDetail, GoalSkillRelation, SkillExperienceStatus | Shape camelCase equivalente ao HTTP; sem React | service, provision e UI |
| `apps/web/src/constants/http-status-code.ts` | Create | HTTP_STATUS_CODE | Constantes locais para estados HTTP usados; não importar pacote @hms inexistente | novo adapter de falhas |
| `apps/web/src/provision/learning/goal-detail-provider.ts` | Create | GoalDetailProvider | Compor LearningService e Axios apenas no servidor; sessão por Request | server function |
| `apps/web/src/provision/learning/get-goal-detail.ts` | Create | getGoalDetail; GoalDetailResult | createServerFn GET, validação do goalId e resposta segura; provider apenas no handler | query da página |
| `apps/web/src/rest/services/learning-service.ts` | Modify | getGoalDetail(accessToken, goalId) | GET tipado, Bearer somente BFF→API; sem validação duplicada do corpo | provider servidor |
| `apps/web/src/routes/learning/goals/$goalId/index.tsx` | Modify | Route e RouteComponent | Middleware existente + GoalDetailPage key={goalId}; sem fetch na rota | página |
| `apps/web/src/routes/learning/index.tsx` | Modify | Route.beforeLoad | Após autenticar, redirect para ROUTES.root com replace | CA-10 |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/index.tsx` | Remove | GoalDetailPlaceholderPage | Substituído pela página real | sem consumidores residuais |
| `apps/web/src/ui/learning/widgets/pages/learning-page/index.tsx` | Remove | LearningPage | Placeholder genérico substituído pelo redirect | sem consumidores residuais |
| `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` | Remove | Suite do placeholder | Substituída pela suite GoalDetailPage | não perder proteção da rota |
| `apps/web/tests/learning/learning-page.test.ts` | Modify | Regressão /learning e contrato da Habilidade | Atualizar expectativa de redirect, preservar casos de skill | CI-W |
| `apps/web/tests/learning/goal-detail-page.test.ts` | Create | Suite browser com transporte mockado | Página/hook reais, navegação, estados e requests RPC | CI-W |
| `apps/web/tests/learning/goal-detail-handler.test.ts` | Create | Suite de integração real do BFF | Sessão e GET real, headers privados, isolamento; via shared factory | CI-W; serviços reais |
| `apps/web/tests/fixtures/learning-module-fixture.ts` | Create | Fixture modular de Learning | Compor fixture Identity existente; cenários determinísticos e limpeza | playwright.ts |
| `apps/web/tests/playwright.ts` | Modify | Factory compartilhada | Re-exportar composição sem perder fixtures Identity | todas as suites |
| `apps/web/src/ui/shared/styles/global.css` | Modify | Tokens e estilos React Flow | Adicionar tokens ausentes sem redefinir os existentes; CSS scoped ao grafo | visual |
| `apps/web/src/ui/shared/widgets/components/icon/index.tsx` | Modify | IconName e ICON_COMPONENTS | Registrar circle, circle-dashed, circle-check, search, plus, minus, trash-2, ellipsis, network | widgets |
| `apps/web/src/ui/shared/widgets/components/icon/tests/icon.test.tsx` | Modify | Cobertura do mapa público | Cobrir novos nomes sem duplicar teste de Lucide | CI-W |
| `apps/web/src/ui/shadcn/tabs.tsx` | Create | Tabs/TabsList/TabsTrigger/TabsContent | Primitive acessível via Radix; teclado/foco, controlled value | GoalViewSwitcher |
| `apps/web/package.json` | Modify | Dependências da tela | Adicionar @xyflow/react, elkjs, @radix-ui/react-tabs compatíveis; sem upgrades amplos | Orchestrator |
| `pnpm-lock.yaml` | Generate | Lockfile workspace | pnpm --filter web add; revisar somente mudança pretendida | Orchestrator |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/index.tsx` | Create | GoalDetailPage | Compor cabeçalho, toolbar, feedback e visualização | hook da página |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/use-goal-detail-page.ts` | Create | useGoalDetailPage | Aba, estado, falhas, retry, remount e sessão rejeitada | query; useNavigation |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/use-goal-detail-query.ts` | Create | useGoalDetailQuery | Consulta por goalId+instância, sem cache persistido | getGoalDetail; sem teste direto |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/tests/goal-detail-page.test.tsx` | Create | GoalDetailPage tests | Mock do hook proprietário e filhos reais | CA-02 a CA-09 |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/tests/use-goal-detail-page.test.ts` | Create | useGoalDetailPage tests | Transições e handlers; mock da query | CA-05, CA-07 |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-detail-header/index.tsx` | Create | GoalDetailHeader | Título, descrição e remoção desabilitada | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-view-switcher/index.tsx` | Create | GoalViewSwitcher | Abas controlled e link de adição | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-detail-feedback/index.tsx` | Create | GoalDetailFeedback | Loading, empty, not-found, error e retry | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-list/index.tsx` | Create | GoalSkillList | Lista semântica da projeção | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-list/goal-skill-row/index.tsx` | Create | GoalSkillRow | Link, estado, progresso e menu desabilitado | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/index.tsx` | Create | GoalSkillGraph | ReactFlow, nós customizados e controles | hook do grafo |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/use-goal-skill-graph.ts` | Create | useGoalSkillGraph | ELK async, medidas, viewport, zoom, cleanup e erro de layout | ReactFlow/ELK |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/goal-graph-node/index.tsx` | Create | GoalGraphNode | Discriminador contexto/skill; links e menus separados | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/goal-graph-controls/index.tsx` | Create | GoalGraphControls | Botões +/- e percentual real | renderer puro |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/tests/goal-skill-graph.test.tsx` | Create | GoalSkillGraph tests | Mock do hook do grafo, controles reais | CA-03, CA-06, CA-09 |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/tests/use-goal-skill-graph.test.ts` | Create | useGoalSkillGraph tests | Layout assíncrono, zoom, identidade de arestas e resultados obsoletos | CA-03, CA-06 |
| `apps/web/src/ui/learning/widgets/components/skill-status/index.tsx` | Create | SkillStatus; SkillStatusProps | Ícone+rótulo comuns à Lista e ao Grafo; sem progresso agregado | renderer puro |
| `apps/web/src/ui/learning/widgets/components/skill-status/tests/skill-status.test.tsx` | Create | SkillStatus tests | Quatro estados e texto acessível | CA-04 |
| `apps/web/src/ui/learning/constants/skill-status-presentation.ts` | Create | SKILL_STATUS_PRESENTATION | Mapa exaustivo pt-BR → IconName/tokens | SkillStatus |

A geração de `apps/web/src/routeTree.gen.ts` não é mudança prevista por esta task isolada: as duas rotas já existem. Rodar generate-routes para verificar paridade; incluir diff gerado somente se decorrente da integração autorizada de SHIFU-65, sob propriedade do Orchestrator e revisão do ledger. Não editar arquivo gerado manualmente.

Sem alterações de migrations, seed, .env, auth provider, outras telas, Jira, Confluence ou design.pen. Sem upgrade amplo, outbox ou Inngest. Infraestrutura/fixtures existentes são reutilizadas; helper específico de teste servidor pode ficar no próprio teste, sem novo fixture global desnecessário.

## Decisões técnicas

| Decisão | Abordagem | Alternativa | Razão | Trade-off |
| --- | --- | --- | --- | --- |
| Grafo | React Flow + ELK | SVG/coordenadas manuais | Arquitetura já determina bibliotecas; suporta grafo real | Novas dependências e teste de layout async |
| Metadados | Método mínimo no port existente | Carregar todo conteúdo de skill | Não trafegar materiais/questões nem duplicar provider | Uma extensão de interface, preservando consumidor atual |
| Consulta | Uma projeção autenticada | Várias chamadas browser por skill | Estados consistentes e privacidade centralizada | Sem conteúdo parcial se projeção incompleta |
| Cache | Consulta por montagem sem persistência | Reuso global duradouro | Evitar vazamento/resultado antigo entre sessões e atualizar após adição | Mais GETs ao revisitar |
| Integração de adição | Dependência explícita SHIFU-65 | Placeholder novo ou fluxo implementado aqui | Preservar escopo e navegação tipada real | CA-08 final depende da rota integrada |
| Shell/tokens | Shell atual + tokens canônicos | Reconstruir shell dos mockups | Limitar regressões e obedecer UI Rules | Diferenças documentadas no manifest |

Referências técnicas primárias consultadas: [React Flow layout](https://reactflow.dev/learn/layouting/layouting), [acessibilidade](https://reactflow.dev/learn/advanced-use/accessibility), [API](https://reactflow.dev/api-reference/react-flow), [TanStack server functions](https://tanstack.com/start/latest/docs/framework/react/guide/server-functions). Context7 não estava disponível nesta sessão. Conferir APIs contra versões efetivamente instaladas antes de implementar; não copiar exemplos de versões antigas.

# 4. Validation Contract

## Testes e aceitação

| Acceptance | Automated boundary | Manual scenario | Evidence target |
| --- | --- | --- | --- |
| CA-01 | test_get_goal_detail_use_case.py; test_get_goal_detail_controller.py; goal-detail-handler.test.ts | VM-01 | evaluation.md, HTTP/status/dados privados |
| CA-02 | goal-detail-page.test.tsx; goal-detail-page.test.ts | VM-02 | evaluation.md + imagens |
| CA-03 | use case/controller; use-goal-skill-graph.test.ts; rota | VM-03 | evaluation.md, equivalência de conjuntos/arestas |
| CA-04 | use case/controller; skill-status.test.tsx; página | VM-03 | evaluation.md, média e visibilidade |
| CA-05 | use-goal-detail-page.test.ts; rota | VM-03 | evaluation.md, URL/storage/reabertura |
| CA-06 | goal-skill-graph.test.tsx; use-goal-skill-graph.test.ts; rota | VM-03 | evaluation.md, zoom e imutabilidade |
| CA-07 | página/hook/rota; controller/handler | VM-02 | evaluation.md, falha/retry |
| CA-08 | goal-detail-page.test.ts; integração real | VM-04 | evaluation.md, destinos e GET atualizado |
| CA-09 | página/grafo/SkillStatus/rota | VM-03 | evaluation.md, foco e controles disabled |
| CA-10 | learning-page.test.ts; goal-detail-page.test.ts | VM-01 | evaluation.md, redirects e consumidores |

Caminhos completos das suites estão no ledger. Descrições de casos em inglês, classes Test<UseCase/Controller> e métodos test_should_* no servidor. Casos adicionais obrigatórios: ID malformado, metadata faltante, progresso incompleto, quatro estados em ambas as visões, grafo vazio/sem arestas, mudança de goalId durante request/layout, nenhuma escrita/evento, sessão expirada, auth unavailable, erro de layout, título longo e justificação opcional. Manter testes existentes de Home/Competência/skill e regredir o port estendido.

Component tests mockam somente o owning hook e renderizam filhos reais. Hook tests cobrem comportamento próprio, não React Query. Proibidos testes dedicados de core structures/enums, repos, provider, REST service e query hook. Integração controller usa PostgreSQL Testcontainers migrado e adapter curricular real; auth pode ter double controlado nesse limite, mas handler/browser real prova sessão/JWT.

Browser route suite usa transporte RPC mockado pela factory compartilhada; não pode afirmar que isso prova FastAPI. Suite goal-detail-handler usa serviços reais e passa pela server function registrada, sem importar provider concreto. Helpers de seed somente banco/contas descartáveis; nunca resetar Compose. Não criar testes que passam apenas por skip de migration/dependência.

## Validação manual

Pré-condições comuns: verificar docker compose ps, API GET /health, web /login, PostgreSQL e Redis; contas descartáveis A/B e Objetivos vazio/preenchido. A fixture inclui quatro estados, duas bases de uma skill, skill isolada, relação para skill não incluída, progressos 30/90 e mesmo skill em outro Objetivo. Usar ambiente de teste isolado; não executar db:seed no banco compartilhado.

### VM-01 — Privacidade e rotas (CA-01, CA-10)

1. Em 1440×900, abrir /learning sem sessão; confirmar login e ausência de dados.
2. Entrar como A, abrir /learning e confirmar Home; abrir card e verificar URL com goalId e detalhe real.
3. Em sessão B, abrir ID de A e depois um ID ausente; confirmar mesma ausência, sem título/skills de A na UI/resposta.
4. Expirar sessão durante uso; confirmar que o próximo retorno rejeitado não mantém detalhe antigo.
5. Inspecionar requests, console, cookies/URL e payload; sem JWT no browser e sem mutações.
6. Registrar URLs/status e evidência na Evaluation; remover apenas dados/contas descartáveis criados pelo teste.

### VM-02 — Loading, vazio, erro e recovery (CA-02, CA-07)

1. Em 1440×900, usar atraso controlado de transporte de teste e comparar uNYG9; skeleton de cabeçalho quando ainda não há dado.
2. Usar Objetivo vazio e comparar KQvnQ; confirmar adição disponível.
3. Forçar 503 no seam de teste, comparar f9ra1, recuperar serviço e acionar Tentar novamente.
4. Repetir 429 sem retry em loop, sem multiplicar requisições; inspecionar loading, disabled e mensagem.
5. Em 390×844, repetir estados e verificar leitura sem overflow da página, live region e toque.
6. Salvar screenshot por estado, requests/status/console; restaurar interceptações. Mock não substitui VM-01 real.

### VM-03 — Grafo, Lista e teclado (CA-03 a CA-06, CA-09)

1. Em 1440×900, abrir preenchido: comparar HZQyi; conferir três arestas esperadas e skill isolada da fixture, sem intermediários.
2. Mudar para Lista: comparar Eu1jl; conferir mesmos IDs/nomes/estados e progresso 60 somente learning.
3. Navegar com Tab/Shift+Tab; abas com setas/Home/End; ativar links com Enter. Comparar foco com TmJTW e token de foco especificado.
4. Confirmar que menus e remoção estão disabled; toque/click não navega por bubbling nem gera request.
5. +/- atualizam percentual real; arrastar canvas vazio desloca a vista; ícone mostra tooltip no hover/foco e restaura posição/zoom iniciais por click/Enter; hover/foco em uma skill destaca com traço animado somente sua cadeia de pré-requisitos até o Objetivo e limpa o destaque ao sair; em reduced-motion, o traço permanece estático; arrastar nós ou usar setas não altera posições individuais; não criar/apagar relações.
6. Reabrir, recarregar e trocar objetivo: Grafo novamente; conferir ausência de preferências em storage/URL.
7. Em 390×844, comparar dNtGs sem copiar relações incorretas do mockup; testar Lista, zoom, texto longo e quatro estados. Repetir com reduced-motion.
8. Capturar todos os estados suplementares do manifest; inspecionar console/requests e ausência de overflow global; encerrar apenas processos iniciados nesta validação.

### VM-04 — Integração dos destinos (CA-08)

1. Com SHIFU-65 integrada, em 1440×900 e 390×844, acionar Adicionar na toolbar e no vazio: confirmar /learning/goals/<goalId>/skills/add e destino real.
2. Voltar ao Objetivo: Grafo e novo GET; se validar adição real, usar exclusivamente fluxo da SHIFU-65 e banco descartável.
3. Abrir a mesma skill pela Lista e Grafo: mesma rota com goalId/skillId curricular; não disparar diagnóstico.
4. Registrar estado efetivo dos destinos. Rota de skill ainda não entregue é limitação externa, não “página de Habilidade implementada”.
5. Limpar fixtures/interceptações e registrar evidência; sem SHIFU-65 integrada, manter critério pendente, não substituir por cast/link quebrado.

## Comandos e qualidade

| ID | CWD | Comandos reais | Escopo |
| --- | --- | --- | --- |
| CI-W | raiz | pnpm --filter web generate-routes; pnpm --filter web check:lint; pnpm --filter web check:architecture; pnpm --filter web check:types; pnpm --filter web test:unit; pnpm --filter web test:integration; pnpm --filter web build | Gerado, lint, arquitetura, tipos, componentes, browser e build |
| CI-S | apps/server | uv run poe check:lint; uv run poe check:architecture; uv run poe check:types; uv run poe test:unit; uv run poe test:integration; uv run poe build | Core, API real e regressões |
| CI-F | apps/server | uv run pytest tests/learning/core/use_cases/test_get_goal_detail_use_case.py; uv run pytest tests/learning/server/controllers/test_get_goal_detail_controller.py | Iteração focada; não substitui gates completos |
| CI-D | raiz | git diff --check | Higiene do diff, sem evidência de comportamento |

Comandos da tabela são operações separadas, não uma única string de shell. Poe test:* usa shell POSIX; no Windows executar em shell compatível ou registrar indisponibilidade e a seleção equivalente executada, sem reportar o gate original como aprovado. Testcontainers exige Docker. CLI Playwright manual: descobrir comando realmente disponível antes de usar; não inventar script. Usar somente Playwright CLI para inspeção, nunca CUA/CDP como substituto.

Evidence futura em evaluation.md: matriz CA/VM, comandos/resultados, screenshots frescos, status de serviços, paridade de learning.rest (collection+detail), achados ACH e disposição por RP. Uma captura de mockup não é screenshot runtime. Nenhuma validação de aplicação foi executada durante autoria.

# 5. Documentation alignment and revision history

| Documento | Autoridade | Estado | Alinhamento |
| --- | --- | --- | --- |
| Learning v13 / Curriculum v6 | Produto | confirmed | Recorte acima; não modificar PRDs ou checkboxes |
| Jira SHIFU-64 | Escopo de entrega | confirmed com drift | Rota e versão antigas; correção externa separada |
| architecture.md / modules.md | Ownership/tecnologia | confirmed | Learning decide; Curriculum fornece; Shared neutro |
| design.md | Tokens e visual geral | confirmed com drift | Grafo padrão segue PRD; neutralizar diagnóstico; shell atual; diferenças no manifest |
| tooling.md / manifests / CI | Comandos | confirmed com drift | Root pnpm-lock e pipelines existentes prevalecem sobre texto “sem CI” |
| sdd.md / create-spec-prompt.md | Ciclo documental | confirmed com drift | Usar draft/ready nesta etapa; divergência implemented/in_progress só importa no kickoff |
| SHIFU-64.md | Decisões do usuário/retomada | updated no handoff | Não duplicar o contrato; apontar a Spec e o Plan |

| Rule | Applies to | Evaluated revision |
| --- | --- | --- |
| documentation/rules/typescript-conventions-rules.md | Web | 05d36a2 |
| documentation/rules/python-conventions-rules.md | Server | 05d36a2 |
| documentation/rules/ui-layer-rules.md | Widgets/provision/tokens | 05d36a2 |
| documentation/rules/web-app-routing-rules.md | Routes/RPC/navigation | 05d36a2 |
| documentation/rules/widget-testing-rules.md | Testes UI e browser | 05d36a2 |
| documentation/rules/core-layer-rules.md | Structures/ports/use case | 05d36a2 |
| documentation/rules/use-case-testing-rules.md | Teste unitário | 05d36a2 |
| documentation/rules/rest-layer-rules.md | Controller/serviço/API | 05d36a2 |
| documentation/rules/controllers-testing-rules.md | HTTP/Testcontainers | 05d36a2 |
| documentation/rules/server-app-layer-rules.md | Registro/router | 05d36a2 |
| documentation/rules/database-layer-rules.md | Transações e fixtures | 05d36a2 |
| documentation/rules/provision-layer-rules.md | BFF/adapter curricular | 05d36a2 |
| documentation/rules/commit-rules.md | Handoff de commits | 05d36a2 |

Conflitos localizados: Widget Testing define tests/ e suites module-first; prevalece para colocação sobre exemplos antigos em UI/Routing. Não importar @hms de exemplos: pacote inexistente; criar constante equivalente local. Não copiar declaração antiga de middleware que retorna credencial: manter guard seguro atual. Templates mencionados por sdd.md não estão presentes; estrutura segue create-spec-prompt.md. Sem edição global de Rules/Architecture/Design nesta entrega.

| Revision | Date | Material change | Reason |
| --- | --- | --- | --- |
| 1 | 2026-09-23 | Contrato inicial sobre base atual, ações disabled e redirect legado | SHIFU-64, PRD atual, Pencil e decisões explícitas |
| 3 | 2026-09-24 | Pan da vista e restauração pelo ícone com tooltip; nós permanecem fixos; Learning PRD v17 reconciliado | Pedido explícito do usuário, RP-04/RP-25 |
| 4 | 2026-09-24 | Destaque temporário do caminho de pré-requisitos no hover e foco de Habilidade | Pedido explícito do usuário, RP-04/RP-25; sem mudar relações oficiais |
| 5 | 2026-09-24 | Animação do traço do caminho destacado e respeito a reduced-motion | Correção explícita do usuário ao tratamento visual da revisão 4 |

Revisão independente concluída em 2026-09-23 por goal_details_spec_reviewer, somente leitura, sobre revisão 1 e base 05d36a2: nenhum achado blocking/high/medium. Architecture, ownership, direção das dependências, Rules e as 56 classificações de caminhos foram conferidas. O Orchestrator reconciliou o resultado com o contrato e declara a revisão 1 ready para planejamento e implementação condicionada aos gates do Plan. Essa revisão não prova fidelidade runtime, testes aprovados ou entrega da SHIFU-65.
