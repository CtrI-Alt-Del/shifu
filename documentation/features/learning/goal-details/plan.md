---
title: SHIFU-64 goal details implementation plan
status: in_progress
spec: ./spec.md
spec_revision: 5
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-64
last_updated_at: 2026-09-23
---

# 1. Execution status

- 2026-09-24: Spec revision 5 animates the highlighted prerequisite path with reduced-motion fallback. The graph CSS and browser animation evidence join the revision 4 scope.
- 2026-09-24: Spec revision 4 adds temporary prerequisite-path emphasis on skill hover/focus. The graph hook, ReactFlow composition, graph card and browser evidence are the affected scope.
- 2026-09-24: Spec revision 3 adds canvas pan and an icon action that restores the initial fitted view. Web graph source, its route test and CA-06/VM-03 evidence are the affected scope; earlier baseline notes below are historical.
- Contrato: [Spec](spec.md), revisão **1**, **ready**, após revisão independente de compatibilidade sem achados. Decisões aprovadas e justificativas em [SHIFU-64.md](../../../../SHIFU-64.md).
- Plan **draft**, fase inicial F1, todas as tarefas pending; nenhum Builder de implementação ativo. Não houve implementação, instalação ou validação runtime.
- Coordenação justificada por contrato Shared/Curriculum/Learning, API/BFF/Web, dependência SHIFU-65 e validação visual em dois viewports.
- Próxima ação: usar [implement-spec](../../../prompts/implement-spec-prompt.md), revalidar base/fontes, criar Evaluation no kickoff e executar F1. Este Plan não autoriza commit, push, mutações Atlassian ou mudanças fora da Spec.
- Dependência crítica: destino de adição da SHIFU-65 ausente na base inspecionada; bloqueia integração final/CA-08, não a preparação nem o servidor.
- Orchestrator é dono de SDD, pacotes/lockfile, primitivas compartilhadas, fixtures compartilhadas, gerados, integração e validação final. Sem migrations previstas.
- Dois Builders poderão trabalhar em paralelo após F1: Server e Web. Nenhum terceiro é necessário. O frontend pode avançar nos componentes/testes com contrato estável enquanto a API é implementada; não declarar navegação completa antes do gate SHIFU-65.
- Mudança da revisão da Spec interrompe atribuições dependentes: reconciliar caminhos, critérios, referências e evidências antes de retomar.

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Revisão 1 ready; parecer independente registrado na seção 5 | Orchestrator | satisfied | Revalidar ausência de mudança de contrato no kickoff |
| Base e autoridades | Status/diff preservados; base 05d36a2 comparada; Learning 83066881 v16 e Curriculum 83034113 v9 conferidos completos | Orchestrator | satisfied | Spec revisada para 2 e fontes reconciliadas |
| Dependências Web | Versões compatíveis de React Flow, ELK e Radix instaladas, APIs verificadas e lock root revisado | Orchestrator | pending | Executar F1-T1; sem upgrade amplo |
| SHIFU-65 | Rota real /learning/goals/$goalId/skills/add disponível e tipada, não só status Jira | Orchestrator / responsável SHIFU-65 | pending | Conferir branch integrada; não fazer merge externo sem autorização, nem criar placeholder/cast |
| Ambiente de testes | Docker/Testcontainers, PostgreSQL/Redis e contas descartáveis; API/web saudáveis | Orchestrator | pending | Verificar compose/health e isolamento; não resetar banco compartilhado |
| Browser CLI | Comando Playwright disponível e validado contra tooling/manifests | Orchestrator | pending | Descobrir CLI local: playwright e playwright-cli não estavam no PATH; não substituir por CUA/CDP |
| Shell dos testes | Shell compatível para Poe test:* POSIX no Windows | Orchestrator | pending | Registrar comando realmente executado e limitações, sem fingir gate aprovado |

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Orchestrator | F1 | Kickoff, contratos compartilhados e dependências preparados | Spec ready | — | in_progress | Base reconciliada, Evaluation iniciada, arquivos compartilhados revisados |
| 2 | Builder Server | F2 | Leitura privada real com projeção curricular | F1 | F3 | in_progress | CI-F/CI-S e HTTP real; paridade learning.rest |
| 2 | Builder Web | F3 | Tela, BFF e testes; placeholders substituídos | F1; SHIFU-65 para saída final | F2 | in_progress | CI-W, comparação visual inicial e contrato do BFF |
| 3 | Orchestrator | F4 | Candidato integrado e evidência aceita | F2, F3; SHIFU-65; ambiente | — | pending | Gates completos, VM/visuais e um Implementation Reviewer concluídos |

## Propriedade de caminhos

Listas abaixo são atribuições exclusivas do ledger da Spec, não autorização para expandir o contrato. Create/Modify/Remove/Generate e símbolos permanecem na Spec. Builders não editam SDD nem caminhos de outro dono. Atribuir explicitamente a revisão 2, tarefa, critérios, Rules, referências e saída ao iniciar cada Builder.

### Orchestrator — F1/F4

- `apps/server/src/shifu/shared/core/domain/structures/curriculum_skill_overview.py`
- `apps/server/src/shifu/shared/core/domain/structures/__init__.py`
- `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py`
- `apps/web/tests/fixtures/learning-module-fixture.ts`
- `apps/web/tests/playwright.ts`
- `apps/web/src/ui/shared/styles/global.css`
- `apps/web/src/ui/shared/widgets/components/icon/index.tsx`
- `apps/web/src/ui/shared/widgets/components/icon/tests/icon.test.tsx`
- `apps/web/src/ui/shadcn/tabs.tsx`
- `apps/web/package.json`
- `pnpm-lock.yaml`

Também possui somente os artefatos SDD desta feature e o guia raiz. routeTree.gen.ts continua gerado e sem edição manual; qualquer diff decorrente da integração SHIFU-65 exige reconciliar o ledger. A fixture compartilhada é preparada em F1 e refinada em F4 exclusivamente pelo Orchestrator, conforme necessidades reportadas pelos Builders.

### Builder Server — F2

- `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`
- `apps/server/src/shifu/learning/core/domain/structures/goal_detail.py`
- `apps/server/src/shifu/learning/core/domain/structures/goal_skill_detail.py`
- `apps/server/src/shifu/learning/core/domain/structures/goal_skill_relation.py`
- `apps/server/src/shifu/learning/core/domain/structures/__init__.py`
- `apps/server/src/shifu/learning/core/use_cases/get_goal_detail_use_case.py`
- `apps/server/src/shifu/learning/core/use_cases/__init__.py`
- `apps/server/src/shifu/learning/rest/controllers/get_goal_detail_controller.py`
- `apps/server/src/shifu/learning/rest/controllers/__init__.py`
- `apps/server/src/shifu/learning/rest/router.py`
- `apps/server/rest-client/learning/learning.rest`
- `apps/server/tests/learning/core/use_cases/test_get_goal_detail_use_case.py`
- `apps/server/tests/learning/server/controllers/test_get_goal_detail_controller.py`

### Builder Web — F3

- `apps/web/src/core/learning/goal-detail.ts`
- `apps/web/src/constants/http-status-code.ts`
- `apps/web/src/provision/learning/goal-detail-provider.ts`
- `apps/web/src/provision/learning/get-goal-detail.ts`
- `apps/web/src/rest/services/learning-service.ts`
- `apps/web/src/routes/learning/goals/$goalId/index.tsx`
- `apps/web/src/routes/learning/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/learning-page/index.tsx`
- `apps/web/tests/learning/goal-detail-placeholder-page.test.ts`
- `apps/web/tests/learning/learning-page.test.ts`
- `apps/web/tests/learning/goal-detail-page.test.ts`
- `apps/web/tests/learning/goal-detail-handler.test.ts`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/use-goal-detail-page.ts`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/use-goal-detail-query.ts`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/tests/goal-detail-page.test.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/tests/use-goal-detail-page.test.ts`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-detail-header/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-view-switcher/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-detail-feedback/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-list/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-list/goal-skill-row/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/use-goal-skill-graph.ts`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/goal-graph-node/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/goal-graph-controls/index.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/tests/goal-skill-graph.test.tsx`
- `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/tests/use-goal-skill-graph.test.ts`
- `apps/web/src/ui/learning/widgets/components/skill-status/index.tsx`
- `apps/web/src/ui/learning/widgets/components/skill-status/tests/skill-status.test.tsx`
- `apps/web/src/ui/learning/constants/skill-status-presentation.ts`

## F1 — Preparação compartilhada

### F1-T1 — Estabelecer base e seams estáveis

- **Status/owner:** pending — Orchestrator.
- **Depends/parallel:** Spec ready; sequencial antes de F2/F3.
- **Paths:** lista exclusiva Orchestrator acima; criar evaluation.md somente no kickoff.
- **Traceability:** RP-03/04/05/15/25, JN-03; suporte a RF-01…10 e CA-01…10.
- **Outcome:** fontes/base revalidadas; porta mínima e tipos compartilhados disponíveis; dependências, tabs, ícones/tokens e factory de fixtures preparados conforme Spec. A fixture não pressupõe endpoint ainda inexistente.
- **Rules:** documentation/rules/core-layer-rules.md, python-conventions-rules.md, typescript-conventions-rules.md, ui-layer-rules.md, widget-testing-rules.md, database-layer-rules.md; caminhos relativos ao diretório documentation/rules para os nomes após o primeiro. Ler os respectivos Antipatterns to Avoid.
- **Risks/controls:** preservar trabalho alheio; não instalar React Query novamente; não ampliar Shared para regras de Learning; revisar diff do lock root, não locks legados. Se base/fontes mudaram materialmente, emendar Spec antes de delegar.
- **Exit:** revisão estrutural dos contratos e caminhos; pnpm --filter web check:types e check:lint quando aplicáveis aos arquivos preparados; registrar falhas preexistentes separadamente. Autorizar F2/F3 só com contrato compartilhado compatível; gates finais continuam obrigatórios.

## F2 — Projeção e endpoint

### F2-T1 — Implementar leitura autorizada e provar fronteira HTTP

- **Status/owner:** pending — Builder Server.
- **Depends/parallel:** F1; paralelo a F3, sem editar Shared.
- **Paths:** lista exclusiva Builder Server.
- **Traceability:** RP-01/03/04/05/15, JN-03; Curriculum RP-01/04; RF-01…04, RF-07; CA-01…04, CA-07.
- **Outcome:** adapter mínimo, use case e controller registrados; autorização, média e relações obedecem à Spec, sem escrita/evento.
- **Rules:** documentation/rules/python-conventions-rules.md, core-layer-rules.md, use-case-testing-rules.md, rest-layer-rules.md, controllers-testing-rules.md, database-layer-rules.md, provision-layer-rules.md, server-app-layer-rules.md (mesmo diretório); respectivos Antipatterns.
- **Risks/controls:** metadados incompletos não viram sucesso parcial; não misturar experiências; preservar get_skill_content e consumidores; não importar Curriculum diretamente em Learning.
- **Exit:** CI-F e CI-S da Spec; controller exercitado com banco descartável/adapter real, resposta e erros seguros, isolamento e ausência de mutações demonstrados. learning.rest deve conter uma requisição rotulada por rota do grupo (collection + detail), método/path/headers/parâmetros corretos e variáveis não secretas; registrar paridade, nunca tratá-la como substituta do HTTP real. Relatar diff/evidências ao Orchestrator.

## F3 — Página, Grafo, Lista e BFF

### F3-T1 — Implementar contrato Web e cobertura

- **Status/owner:** pending — Builder Web.
- **Depends/parallel:** F1; paralelo a F2; gate SHIFU-65 obrigatório antes da saída final de navegação/typecheck.
- **Paths:** lista exclusiva Builder Web. Solicitar ajustes de fixture/tokens/ícones ao Orchestrator, sem editar seus arquivos.
- **Traceability:** RP-01/03/04/05/15/25, JN-03; RF-01…10; CA-01…10.
- **Outcome:** página real, serviço/BFF seguro e visualizações equivalentes com cobertura; remoção dos placeholders preservando testes existentes de skill.
- **Rules:** documentation/rules/typescript-conventions-rules.md, ui-layer-rules.md, web-app-routing-rules.md, widget-testing-rules.md, rest-layer-rules.md, provision-layer-rules.md (mesmo diretório); respectivos Antipatterns.
- **Risks/controls:** não transportar JWT ao browser; não compartilhar dado entre sessões; descartar request/layout obsoleto; não hardcodear relações; controles futuros realmente disabled. Não contornar SHIFU-65 com cast, link quebrado ou placeholder.
- **Exit:** CI-W da Spec; suites de widget/hook/rota e handler real diferenciadas na evidência. Comparação inicial com cada frame e suplemento do manifest nos viewports exatos, teclado/foco/reduced-motion, loading/vazio/erro/recovery; requests/status/console inspecionados. Capturas frescas Playwright CLI por estado, não exportações Pencil como evidência runtime. F4 reroda tudo no candidato integrado.

## F4 — Integração, validação e conclusão

### F4-T1 — Aceitar evidência do candidato completo

- **Status/owner:** pending — Orchestrator.
- **Depends/parallel:** F2 e F3 concluídos, gates externos satisfeitos; sem Builders concorrentes editando o candidato durante review.
- **Paths:** revisar todos os caminhos da Spec; editar somente os caminhos exclusivos Orchestrator/SDD. Correções nos demais voltam ao Builder responsável.
- **Traceability:** todos RF-01…10/CA-01…10; VM-01…04; RP/JN conforme matriz da Spec.
- **Outcome:** diff integrado reconciliado, evidência atual e disposição por requisito na Evaluation.
- **Rules:** os 13 arquivos do Rule Pack da seção 5 da Spec, incluindo commit-rules.md e respectivos Antipatterns; implement-spec e conclude-spec governam o ciclo.
- **Risks/controls:** mock RPC não prova servidor; screenshot não prova autorização; ambiente indisponível mantém evidência pendente. Não iniciar serviços desnecessários; parar somente processos iniciados para esta validação, preservar Docker compartilhado.
- **Exit:** todos CI-W/CI-S/CI-D, VM e capturas da tabela abaixo; paridade REST e ausência de consumidores dos placeholders. Agendar **exatamente um Implementation Reviewer read-only** após integração e baseline de gates/evidências. Verificar achados, registrar ACH, retomar o Builder responsável, invalidar evidência afetada e rerodar; retomar o mesmo Reviewer. Sem aprovação fictícia ou diminuição de floors.

# 4. Validation and handoff

Toda evidência será registrada em evaluation.md durante a implementação. EV abaixo são destinos planejados, não resultados já obtidos. Referências visuais e decisões de adaptação: [manifest](design/manifest.md). Comandos CI-W, CI-S, CI-F, CI-D e CWD exatos estão na seção 4 da Spec; executá-los separadamente, sem inventar scripts.

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Use case e controller; regressões Curriculum/Competência | CA-01…04/07 | Spec CI-F/CI-S | EV-01: comandos e resultados | pending |
| Automated | Widget, hooks, rota e regressões Home/skill | CA-02…10 | Spec CI-W | EV-02: comandos e resultados | pending |
| Runtime | Sessão → server function → GET API → banco isolado | CA-01/07/08 | Suite goal-detail-handler; contrato técnico | EV-03: respostas, headers, auth e ausência de escrita | pending |
| Manual | VM-01 privacidade e rotas | CA-01/10 | Spec VM-01 | EV-04 | pending |
| Manual | VM-02 estados e recovery | CA-02/07 | Spec VM-02 | EV-05 | pending |
| Manual | VM-03 Grafo/Lista/teclado | CA-03…06/09 | Spec VM-03 | EV-06 | pending |
| Manual | VM-04 destinos reais | CA-08 | Spec VM-04; SHIFU-65 | EV-07 | pending |
| REST client | Learning collection + detail | CA-01/02; contrato HTTP | apps/server/rest-client/learning/learning.rest | EV-08: paridade por rota | pending |
| Visual | Grafo desktop, 1440×900 | CA-02…06/09 | Manifest: HZQyi | EV-09: screenshot runtime + comparação | pending |
| Visual | Lista desktop, 1440×900 | CA-03/04/05/09 | Manifest: Eu1jl | EV-10: screenshot runtime + comparação | pending |
| Visual | Grafo mobile, 390×844 | CA-03/04/06/09 | Manifest: dNtGs | EV-11: screenshot runtime + comparação | pending |
| Visual | Loading desktop, 1440×900 | CA-07 | Manifest: uNYG9 | EV-12: screenshot runtime + comparação | pending |
| Visual | Erro desktop, 1440×900 | CA-07 | Manifest: f9ra1 | EV-13: screenshot runtime + comparação | pending |
| Visual | Vazio desktop, 1440×900 | CA-02/08 | Manifest: KQvnQ | EV-14: screenshot runtime + comparação | pending |
| Visual | Foco Lista desktop, 1440×900 | CA-09 | Manifest: TmJTW | EV-15: screenshot runtime + comparação | pending |
| Visual | Lista mobile, 390×844 | CA-03/04/05/09 | Manifest: Eu1jl + dNtGs | EV-16: screenshot runtime + comparação | pending |
| Visual | Loading mobile, 390×844 | CA-07 | Manifest: uNYG9 + dNtGs | EV-17: screenshot runtime + comparação | pending |
| Visual | Erro mobile, 390×844 | CA-07 | Manifest: f9ra1 + dNtGs | EV-18: screenshot runtime + comparação | pending |
| Visual | Vazio mobile, 390×844 | CA-02/08 | Manifest: KQvnQ + dNtGs | EV-19: screenshot runtime + comparação | pending |
| Visual | Ausência privada desktop, 1440×900 | CA-01/07 | Manifest: f9ra1 | EV-20: screenshot runtime + comparação | pending |
| Visual | Ausência privada mobile, 390×844 | CA-01/07 | Manifest: f9ra1 + dNtGs | EV-21: screenshot runtime + comparação | pending |
| Visual | Quatro estados Lista, 1440×900 | CA-04 | Manifest: Eu1jl | EV-22: screenshot runtime + comparação | pending |
| Visual | Quatro estados Grafo, 1440×900 | CA-04 | Manifest: HZQyi | EV-23: screenshot runtime + comparação | pending |
| Visual | Foco Grafo, 1440×900 | CA-09 | Manifest: HZQyi + TmJTW | EV-24: screenshot runtime + comparação | pending |
| Visual | Foco mobile, 390×844 | CA-09 | Manifest: dNtGs + TmJTW | EV-25: screenshot runtime + comparação | pending |
| Visual | Ações disabled desktop, 1440×900 | CA-09 | Manifest: HZQyi/Eu1jl | EV-26: screenshot runtime + comparação | pending |
| Visual | Ações disabled mobile, 390×844 | CA-09 | Manifest: dNtGs | EV-27: screenshot runtime + comparação | pending |
| Visual | Skill desconectada e duas bases desktop, 1440×900 | CA-03/06 | Manifest: HZQyi | EV-28: screenshot runtime + comparação | pending |
| Visual | Skill desconectada e duas bases mobile, 390×844 | CA-03/06 | Manifest: dNtGs | EV-29: screenshot runtime + comparação | pending |
| Visual | Erro layout, 1440×900 | CA-07 | Manifest: f9ra1 | EV-30: screenshot runtime + comparação | pending |
| Visual | Título/descrição longos, 390×844 | CA-02/09 | Manifest: dNtGs | EV-31: screenshot runtime + comparação | pending |

Os 16 suplementos foram aceitos como capturas runtime derivadas, sem inventar mockups adicionais; detalhes de composição permanecem no manifest. Capturas temporárias não devem ser commitadas automaticamente. Os sete PNGs versionáveis são referências de design, não resultado de testes.

Handoff final exige todas as fases/tarefas completed, mesma revisão da Spec, diff e gerados/lockfile revisados, gates sem redução de exigências, evidência aceita para cada CA/VM/estado visual, paridade REST e Reviewer concluído com achados verificados resolvidos. Registrar serviços/contas/fixtures e limitações. Só então encaminhar para [conclude-spec](../../../prompts/conclude-spec-prompt.md); não declarar entrega completa enquanto SHIFU-65/CA-08 ou outro gate estiver pendente.

Não criar branches ou commits automaticamente nesta etapa documental. Na implementação, seguir a orientação de branch/commit e rastreamento do guia raiz, preservando a chave SHIFU-64 e sem mutar Jira/Confluence como efeito colateral.
