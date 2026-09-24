# SHIFU-64 — Contexto e decisões para implementação

> Handoff documental de 2026-09-23. Spec revisão 1 `ready`, revisão independente concluída sem achados de compatibilidade; Plan `draft`, aguardando início da implementação e gates externos. Nenhum código da aplicação foi alterado.

## Por onde começar

1. [Spec canônica](documentation/features/learning/goal-details/spec.md): requisitos, critérios, schemas, 56 caminhos classificados e validação.
2. [Plan de execução](documentation/features/learning/goal-details/plan.md): 3 waves, 4 fases/tarefas, ownership, dependências e evidências previstas.
3. [Manifest visual](documentation/features/learning/goal-details/design/manifest.md): 7 PNGs exportados do Pencil e 16 estados suplementares a capturar no runtime.

Este guia concentra diagnóstico e justificativas; não duplica nem substitui o contrato canônico. A Spec e o Plan ficam em `documentation/features/learning/goal-details/`, conforme o SDD do projeto, enquanto este arquivo na raiz facilita a retomada no outro chat.

## Objetivo e fontes

Entregar a página autenticada de detalhes de Objetivo com Grafo e Lista, substituindo o placeholder. A entrega é full-stack: consultar dados reais, proteger a propriedade do Objetivo e apresentar estados, relações e navegação.

- Jira: [SHIFU-64 — Implementar página do Objetivo com Grafo e Lista](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-64).
- Autoridade de produto: [Shifu — PRD — Learning](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning), content ID `83066881`, versão **13**, atualizada em `2026-09-15T13:33:36.320Z`; consultada novamente em 2026-09-23. Parent ID `82804737`.
- Requisitos principais: `RP-01`, `RP-03`, `RP-04`, `RP-05`, `RP-25`; `RP-15` governa a projeção do progresso da Habilidade. Contexto de jornada: `JN-03`.
- Design: `design/shifu.pen`; frames indicados pelo ticket: `HZQyi`, `uNYG9`, `dNtGs`, `Eu1jl`, `TmJTW`.
- Base local conferida: branch `main`, commit `05d36a2d63f8c1b442ca1b4205b0658590d77751` em 2026-09-23. O diagnóstico antigo baseado em `ff6e68f` não representa mais o estado atual.

O Jira ainda referencia PRD versão 6 e `/learning/objectives/$objectiveId`. Essas referências estão defasadas em relação ao PRD consultado, à orientação da equipe, à decisão do usuário e à rota já implementada. Não alterar Jira ou Confluence automaticamente; registrar essa divergência na Spec e no PR.

## Decisões aprovadas pelo usuário

### 1. Mostrar ações futuras desabilitadas

Exibir **Remover objetivo** e os botões de menu **…** das Habilidades, desabilitados, tanto no Grafo quanto na Lista onde o design os prevê.

**Justificativa para a equipe:** preservar a composição visual e entregar os componentes de apresentação já preparados para integração nas próximas tasks, sem ampliar a SHIFU-64 para implementar remoção ou outras operações. A presença visual não significa que a funcionalidade está entregue.

Limites de implementação:

- Usar controles semanticamente desabilitados, não apenas uma aparência de desabilitado.
- Não abrir menus, diálogos ou confirmações; não executar requisições nem mutações.
- Dar nome acessível aos controles de ícone; não depender exclusivamente de tooltip para explicar indisponibilidade.
- Não criar handlers fictícios, chamadas de remoção, estados de confirmação ou contratos de API para ações futuras.
- Manter o link de abertura da Habilidade separado do botão de menu: clicar no menu desabilitado não deve abrir a Habilidade por propagação de evento.
- Preparar componentes coesos, sem construir um framework genérico para funcionalidades ainda não definidas.

“Adicionar Habilidade” permanece uma ação de **navegação** para o fluxo responsável. Implementar a adição, seleção de bases ou persistência continua fora do escopo desta task. Conferir a integração com SHIFU-65 antes da entrega.

### 2. Substituir o placeholder por detalhes reais

A página definitiva será `/learning/goals/$goalId`. Substituir o placeholder dessa rota e remover seu componente e testes específicos quando os testes da página real assumirem a cobertura.

Não manter uma segunda página “Em preparação” nem um objetivo fictício como solução final.

### 3. Redirecionar `/learning` para a Home

O usuário aprovou explicitamente redirecionar o endereço genérico `/learning` para a Home (`/`) e fazer os links de Objetivos apontarem para `/learning/goals/$goalId`.

**Justificativa para a equipe:** `/learning` não contém o identificador necessário para consultar um Objetivo. Escolher o primeiro, o último ou algum Objetivo fixo introduziria uma regra de produto não solicitada, com resultados ambíguos para usuários com nenhum ou vários Objetivos. A Home já é o ponto de seleção de Objetivos; encaminhar para ela preserva o acesso por links antigos sem inventar essa seleção.

São duas responsabilidades diferentes:

| Endereço | Comportamento final | Motivo |
| --- | --- | --- |
| `/learning/goals/$goalId` | Mostrar detalhes reais do Objetivo autorizado | O identificador define o recurso consultado |
| `/learning` | Redirecionar para `/`, sem renderizar o placeholder | Endereço genérico não identifica um Objetivo |

Preservar a proteção de autenticação existente. Acesso sem sessão deve seguir o fluxo de login; acesso autenticado ao endereço legado deve chegar à Home. Evitar loop de redirecionamento e usar substituição de histórico quando apropriado, para o botão Voltar não retornar continuamente ao endereço legado.

### 4. Grafo inicial, sem persistência

Abrir sempre na aba Grafo. Alternar para Lista apenas no estado local da página, sem salvar preferência em storage, servidor ou parâmetros de URL. Não persistir zoom. Os dois modos mostram o mesmo conjunto de Habilidades, estados e destinos.

## Diagnóstico atualizado do repositório

Os caminhos abaixo são evidências existentes, não uma lista de mudanças já executadas.

| Evidência | Estado observado | Consequência para a implementação |
| --- | --- | --- |
| `apps/web/src/routes/learning/goals/$goalId/index.tsx` | Rota protegida já recebe `goalId` e renderiza `GoalDetailPlaceholderPage` | Modificar a rota; não criar uma rota concorrente com `objectives` |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/index.tsx` | Placeholder específico do Objetivo | Substituir por página real e remover o placeholder |
| `apps/web/src/routes/learning/index.tsx` | Renderiza `LearningPage` com proteção de acesso | Substituir renderização pelo redirecionamento aprovado |
| `apps/web/src/ui/learning/widgets/pages/learning-page/index.tsx` | Página antiga ainda existe | Conferir consumidores e remover o placeholder antigo, sem apagar código usado por outras telas |
| `apps/web/src/ui/learning/widgets/components/objective-card/index.tsx` | Já navega para `/learning/goals/$goalId` usando `id` | Preservar integração da Home; não reimplementar os cards |
| `apps/web/src/rest/services/learning-service.ts` | Possui `getGoals` e `getCompetencyDetail` | Estender o serviço existente; não criar outro serviço Learning |
| `apps/web/src/ui/learning/widgets/pages/competency-detail-page/use-competency-detail-page.ts` | Exemplo atual de server function autenticada, consulta e estados seguros | Conferir e reaproveitar o padrão, sem copiar defeitos ou reconstruir a infraestrutura |
| `apps/web/src/middlewares/require-auth-middleware.ts` | Valida sessão e retorna `undefined` | A suspeita antiga de retorno do token pelo middleware não se aplica à versão atual |
| `apps/web/package.json` | React Query já instalado; React Flow não consta nas dependências | Não planejar reinstalação da infraestrutura de consultas; avaliar inclusão de `@xyflow/react` |
| `apps/server/src/shifu/learning/database/sqlalchemy/learning_database.py` | Implementação de LearningDatabase já existe | Não reconstruir a unidade de trabalho |
| `apps/server/src/shifu/learning/pipes/learning_pipe.py` | Expõe database e CurriculumContentProvider | Reutilizar composição existente |
| `apps/server/src/shifu/learning/rest/router.py` | Registra consultas de Home e detalhes de Competência | Acrescentar consulta do Objetivo sem substituir endpoints existentes |
| `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py` | Porta compartilhada `get_skill_content` | Avaliar extensão mínima ou contrato de leitura específico para relações, sem importação direta Learning → Curriculum |
| `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Adapter existente fornece conteúdo curricular | Evitar carregar materiais/atividades desnecessariamente para projetar o Grafo |
| `apps/server/tests/learning/core/use_cases/` e `apps/server/tests/learning/server/controllers/` | Taxonomia modular atual já usada por detalhes de Competência | Novos testes devem seguir os limites atuais, não o layout antigo do diagnóstico |

A existência desses arquivos não significa que a consulta de detalhes do Objetivo já esteja entregue. O router inspecionado registra Home e detalhes de Competência, mas não uma operação de detalhes de Objetivo.

## Contrato funcional a preservar na Spec

- Apenas o dono acessa o Objetivo; inexistência e recurso de outro usuário não revelam dados privados.
- Exibir título e descrição, sem nota, progresso agregado ou conclusão do Objetivo.
- Mostrar somente Habilidades incluídas; uma aresta curricular exige os dois extremos incluídos. Não criar pré-requisitos intermediários nem bloqueios de aprendizagem.
- Admitir Habilidades desconectadas. O cartão contextual do Objetivo no design não é uma Habilidade curricular.
- Estados: Não iniciada, Em diagnóstico, Em aprendizado e Concluída.
- Barra de progresso somente em aprendizado. Learning é responsável pelo valor; não calcular regras pedagógicas no componente React.
- O progresso da Habilidade considera todas as suas Competências, conforme RP-15, não apenas as liberadas ou presentes na tela.
- Manter o contexto de Objetivo ao abrir uma Habilidade. O código atual identifica a experiência pelo par `goalId`/`skillId`; não confundir `skillId` curricular com o ID da experiência.
- Layout automático do Grafo, sem arrastar/reordenar nós ou editar relações; zoom acessível com indicação do nível atual.
- Estados carregando, preenchido, vazio, erro recuperável e ausência privada; recuperação não deve mostrar dados de outro Objetivo ou sessão.
- Desktop, mobile, teclado, foco visível e rótulos em pt-BR; informação não pode depender somente de cor ou posição.
- Não iniciar diagnóstico, remover dados, editar Objetivo ou implementar SHIFU-65/66 como efeito colateral.

## Padrão de arquivos e componentes

A Spec fixa a árvore exata e classifica cada arquivo como Create, Modify, Generate ou Remove. As convenções confirmadas são:

- UI de Learning em `apps/web/src/ui/learning/widgets/`; rotas finas em `apps/web/src/routes/learning/`.
- Diretórios e arquivos kebab-case. Widget com comportamento: `index.tsx` + `use-<nome-do-widget>.ts` no mesmo diretório.
- Um widget por `index.tsx`; filhos visuais possuem seus próprios diretórios. Componentes puramente declarativos podem dispensar hook.
- Widget exportado como `const`, tipo público `<WidgetName>Props`; lógica e handlers `handle*` no hook. Imports entre diretórios usam `@/`.
- Reutilizar shell, tokens, primitives de `ui/shadcn` e wrapper `Icon`; não copiar um segundo design system dentro de Learning.
- Testes Vitest dos widgets em seu próprio `tests/`, conforme a regra específica de widget-testing e o código atual. Essa regra específica diverge de um trecho da regra UI que menciona testes ao lado do entrypoint: não copiar essa inconsistência.
- Testar composição real dos filhos; teste do componente com hook próprio usa mock tipado do hook. Consultas/actions e serviço REST não recebem testes dedicados; transporte e integração são cobertos na página/rota.
- Suites de navegação em `apps/web/tests/learning/`; testes de use case e controller nos diretórios modulares de Learning do servidor.
- Preservar o padrão de contratos e serialização mais recente da base. Não reutilizar automaticamente uma proposta antiga de DTO snake_case no browser: tipos atuais de Competência usam camelCase.
- Não editar manualmente `routeTree.gen.ts`; usar o script `generate-routes` se necessário.

## Branch, commits e rastreabilidade

Nenhuma branch ou commit foi criado neste trabalho documental.

O documento de branches prevê branch por task a partir de `main`, PR para `main` com ao menos uma aprovação e promoção para `production` após validação do PO. Contudo, ainda contém exemplos antigos de outro projeto e não resolve sozinho todos os nomes usados atualmente.

Para execução pelo Codex, o padrão da aplicação exige prefixo `codex/`: sugestão **`codex/shifu-64-goal-details`**. Se a equipe instruir explicitamente outro prefixo, seguir essa instrução e conservar a chave Jira. Não apresentar esse prefixo da ferramenta como uma nova política global da equipe.

Commits propostos, quando o usuário autorizar commit:

```text
docs: SHIFU-64 document goal details contract
feat(server): SHIFU-64 expose owned goal details
feat(web): SHIFU-64 render goal graph and list
test(web): SHIFU-64 cover goal details navigation
```

Usar Conventional Commits, chave `SHIFU-64`, descrição em inglês no imperativo, sem ponto final. A configuração executável atual é `commitlint.config.cjs`, não o `.mjs` citado na documentação. Ela aceita `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci` e `merge`; não presumir que todos os tipos listados no texto antigo passam no hook. Não ignorar hooks.

O PR deve vincular Jira, URL/content ID/versão do PRD, Spec e critérios `RF/CA`, decisões de rota, limitações das ações desabilitadas e evidências. Nunca afirmar que as remoções foram implementadas. Não usar IDs `ANI-*` ou `SHI-*` dos exemplos defasados.

## Estado atual e gates de implementação

- Pencil reconectado; sete frames inspecionados e exportados para o pacote visual. A indisponibilidade anterior foi resolvida. Nenhuma edição no design.
- Spec revisão 1 pronta após revisão independente read-only de arquitetura/Rules e conferência dos 56 caminhos; nenhum achado blocking/high/medium. Essa revisão não substitui testes ou avaliação runtime.
- Plan criado; execução ainda não iniciada. Não há Evaluation fictícia: `evaluation.md` será criado no kickoff via implement-spec.
- Revalidar base Git e versões do Confluence no próximo chat; mudanças materiais exigem reconciliação do contrato, não aplicação cega deste diagnóstico.
- SHIFU-65 estava em Code Review e a rota de adição não estava na base local. Conferir integração real antes da saída final Web/CA-08; não implementar a task dependente como efeito colateral.
- Preparar Docker/serviços/contas isoladas e descobrir o comando Playwright CLI disponível. `playwright` e `playwright-cli` não estavam no PATH; os testes Poe usam shell POSIX. Registrar limitações reais em vez de declarar gates aprovados.
- Não foram executados testes de aplicação nesta etapa documental. Não houve instalação de dependências, branch, commit, push ou alteração em Jira/Confluence.

As decisões aprovadas não precisam ser perguntadas novamente, salvo contradição material com autoridade atual. As diferenças entre mockups e contrato (mobile, foco, diagnóstico neutro, ações disabled e shell atual) estão justificadas no manifest.

## Prompt para o próximo chat

> Implemente SHIFU-64 seguindo AGENTS.md e documentation/prompts/implement-spec-prompt.md. Leia SHIFU-64.md e os arquivos spec.md, plan.md e design/manifest.md em documentation/features/learning/goal-details/. Revalide a base e as versões atuais do Confluence antes de editar; preserve mudanças existentes. A Spec revisão 1 está ready, o Plan draft tem tarefas pending. Inicie pela F1 e crie a Evaluation no kickoff. Respeite os caminhos/ownership, as ações desabilitadas e a substituição dos placeholders. Verifique a integração real de SHIFU-65 para a navegação de adição; não crie placeholder ou cast para contornar sua ausência. Execute e registre os gates, cenários e capturas previstos, com revisão integrada final. Não faça commit, push ou alterações externas sem autorização.

## Texto curto para justificar à equipe

> A SHIFU-64 substituirá o placeholder pela tela real em `/learning/goals/$goalId`. O endereço genérico `/learning` será redirecionado para a Home porque não informa qual Objetivo consultar; assim preservamos links antigos sem escolher um Objetivo arbitrariamente. “Remover objetivo” e os menus das Habilidades serão entregues visualmente, mas desabilitados: isso prepara os componentes para as próximas tasks sem incluir remoção ou outras mutações no escopo desta entrega.
