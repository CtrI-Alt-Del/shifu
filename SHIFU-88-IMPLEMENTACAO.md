# SHIFU-88 — Plano e instruções para o agente implementador

Preparado em 14/10/2026, com fontes reconferidas às 20h23 (America/Sao_Paulo), e atualizado conforme as instruções posteriores do usuário. Esta é a versão de referência do handoff, salva na raiz do projeto; substitui a cópia inicial externa. Não é uma Spec aprovada. A publicação inicial da branch e a atualização de status da SHIFU-88 pertencem à primeira etapa; commits das modificações e abertura de PR continuam dependendo do aceite manual. Nenhum teste foi executado nesta pesquisa.

Repositório: `C:\Users\Luciano\Desktop\Joao\Faculdade\projeto\shifu`. Estado inspecionado: branch `main`, HEAD `e7b2097258f64b4669b0185aa31328555c736d03`, worktree limpa. Remote configurado: `origin`, `https://github.com/CtrI-Alt-Del/shifu.git`. Não foi verificado se esse HEAD já contém o estado remoto mais recente. `.codegraph/` não existe neste checkout.

## 1. Fontes, escopo e comparação com o código

### Autoridades atuais

| Fonte | Identidade e versão verificadas | Aplicação nesta entrega |
| --- | --- | --- |
| [SHIFU-88](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-88) | Issue `12598`, “Implementar questões React em Atividades de aprendizagem”, atualizada em 05/10/2026; parent SHIFU-10 | Define o recorte de entrega e os frames ZWAmr/ZQZkP. Bloqueia SHIFU-111 e SHIFU-23; isso não significa que esta task implementa integralmente essas histórias. |
| [Learning](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning) | Conteúdo `83066881`, **v26**, parent `82804737`, atualização 05/10/2026 02:11:45 UTC | RP-09, RP-11, RP-12, RP-14, RP-18, RP-25; JN-07/JN-08. Preservar também os contratos consumidores RP-13/RP-27 e o ciclo dos novos rascunhos em RP-29. |
| [Curriculum](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113/Shifu+PRD+Curriculum) | Conteúdo `83034113`, **v13**, parent `82804737`, atualização 04/10/2026 23:01:19 UTC | RP-03/JN-03: projeto inicial, arquivos editáveis, dependências, comandos, política de arquivos adicionais e rubrica. |
| Repositório | AGENTS.md; documentation/{sdd,rules,architecture,modules,tooling,design}.md; prompts e configurações atuais | Governa implementação, evidências, testes e entrega. |

Os dois PRDs foram lidos integralmente. O Jira ainda referencia Learning v24 e Curriculum v12; as versões acima são o retrato da consulta, não versões fixadas para a implementação. Registrar a reconciliação na nova Spec, sem alterar requisitos do Jira nem conteúdo do Confluence. A atualização do status da SHIFU-88 é tratada separadamente na etapa 1. As versões consultadas também explicitam eliminação de rascunhos e impedimento de recriar dados removidos. A última alteração de Learning integra ações do Mentor; não amplia esta task para implementar o Mentor.

### Regra permanente — sempre seguir o Confluence mais recente

O agente deve sempre consultar e seguir a versão mais atual das páginas canônicas aplicáveis no Confluence, mesmo quando ela for posterior às versões deste documento, do Jira ou de uma Spec existente. No início, em cada retomada da implementação e antes da conclusão/publicação do PR, verificar identidade, versão e atualização das páginas; ler integralmente a versão vigente antes de usá-la como autoridade. Repetir a consulta quando houver indício de alteração ou expansão de escopo. Não usar somente trechos de busca, cache ou números de versão registrados neste plano.

Registrar na Spec URL, content ID, versão e horário efetivamente consultados. Se o Confluence mudar durante o trabalho, marcar o contrato como `stale`, ler e reconciliar as alterações com RF/CA, código e testes antes de prosseguir no trecho afetado; mudanças materiais retornam a Spec a `draft` para revisão conforme SDD. Uma versão nova não autoriza ampliar silenciosamente a task nem alterar o PRD: reportar conflitos com o escopo da SHIFU-88 e resolver a decisão com o usuário, preservando trabalho independente. Atualizar as referências do PR para as versões efetivamente reconciliadas.

### Escopo funcional fechado pelo Jira e PRDs

- Questão React dentro de Atividade de aprendizagem com três a cinco questões; manter compatibilidade com questões de escolha e JavaScript stdin e o avanço sequencial já existente.
- Projeto inicial curricular, arquivos editáveis, dependências fixas e comandos permitidos. O aluno não altera configurações nem instala pacotes.
- Prática opcional em WebContainers: iniciar automaticamente, atualizar ao editar, mostrar prévia e terminal, sem botão Executar. Navegador incompatível continua permitindo edição e envio.
- “Novo arquivo”, pelo ícone de arquivo com `+`, somente quando a questão autoriza; informar diretórios, extensões e limite. Arquivos autorizados participam da prática, resposta e avaliação.
- Autosave dos arquivos editáveis e adicionais autorizados no navegador, por conta e experiência; persiste após logout/login no mesmo navegador. Em duas abas prevalece a última versão salva. Não cria tentativa ou progresso e não sincroniza dispositivos.
- “Salvo neste navegador”, estados de salvamento e aviso de perda quando salvar não for possível.
- “Como será avaliado” com nomes e pesos públicos vindos da rubrica; nunca fixar no produto os exemplos 30/40/30 ou o limite ilustrativo de arquivos do desenho.
- Avaliação preliminar com nota provisória, rubrica e arquivos congelados em somente leitura. Inconclusão obrigatória bloqueia avanço e permite reavaliar exatamente a mesma resposta.
- Somente o envio final completo cria tentativa imutável e dispara avaliação oficial. Falhas recuperam a mesma tentativa, sem zero artificial, nota parcial definitiva ou efeitos duplicados.
- Resultado e arquivos históricos acessíveis após sair e voltar; desktop, mobile, teclado e pt-BR.

Fora do escopo: Fastify, painel HTTP, React + Fastify, questão HTML/CSS/JS independente, React no diagnóstico, instalação livre, configuração editável, sincronização de rascunhos no servidor, IDE genérica, reescrita de progressão/gamificação e infraestrutura de SonarCloud. Regressão do diagnóstico continua necessária quando contratos compartilhados forem alterados.

### O que já existe e o que precisa mudar

| Área | Evidência atual | Direção de implementação |
| --- | --- | --- |
| Contratos Web | `apps/web/src/core/learning/choice-activity.ts`: CodeQuestion, CodeAnswer e CodeResultQuestion usam literalmente `javascript_stdin` | Acrescentar discriminador React e política curricular; atualizar todos os consumidores e o mapeamento REST. |
| Currículo/Shared | `javascript_stdin_question.py` e snapshots aceitam apenas stdin; arquivos editáveis limitados a `.js/.mjs/.cjs/.txt` | Introduzir contrato React e snapshot compatíveis, sem liberar extensões/arquivos indiscriminadamente no tipo stdin. |
| Avaliação e recuperação | Casos de uso, outbox, job Inngest, chave idempotente, snapshots e histórico já existem | Generalizar o fluxo existente. Não criar segundo pipeline de avaliação exclusivo de React. |
| Validação de arquivos | Preliminar e envio final exigem exatamente os caminhos iniciais editáveis | Validar iniciais editáveis + adicionais autorizados nas duas entradas, com decisão autoritativa no servidor. |
| Persistência | Tentativa e snapshot já persistem arquivos/questões em JSON; mapper distingue stdin de escolha | Acrescentar desserialização React, preservar leitura de dados antigos. Nova tabela/migration somente se houver necessidade demonstrada. |
| Avaliador IA | CodeRubricAssessmentInput tem `question_kind: str`; Jev provider é independente do tipo | Reutilizar a porta e o avaliador. Learning continua calculando notas e efeitos; não adicionar Agno nem avaliador React duplicado. |
| Editor/interface | Há Monaco, árvore de arquivos, xterm, rubrica, resposta congelada e resultados somente leitura | Reutilizar os componentes adequados; criar composição React com prévia e criação autorizada de arquivos. Monaco precisa reconhecer JSX e as linguagens autorizadas. |
| Runtime | Runner atual aceita `node <entrypoint>`, gera CommonJS e encerra processo após 10 segundos | Runtime React precisa de projeto confiável, processo de desenvolvimento contínuo, URL de prévia, atualização e descarte. Não reutilizar cegamente o timeout de execução stdin. |
| Rascunho | Estado atual fica apenas na memória dos widgets | Implementar armazenamento persistente por conta/experiência/atividade/questão/revisão, concorrência entre abas e recuperação segura. |

As dependências Monaco, WebContainers, xterm, React e Vite já estão instaladas. Não planejar sua reinstalação como se estivessem ausentes. `documentation/features/learning/js-code-question/{spec,evaluation}.md` é histórico concluído, revisão 15: seus parágrafos de baseline descrevem o estado anterior à implementação. Usar o código atual como prova do presente; não reabrir nem reescrever o histórico para hospedar React.

## 2. Sequência obrigatória de execução

**Abrir e publicar a branch da task → verificar vínculo e atualizar status da SHIFU-88 no Jira → implementar mudanças → rodar testes → pedir avaliação manual ao usuário e aguardar aprovação explícita → commitar as mudanças, atualizar a branch remota e abrir PR.**

A publicação inicial deve apontar para o commit-base já existente, sem commit vazio nem commit das modificações. Ela disponibiliza a branch remota antes da implementação. Não criar commits intermediários das mudanças, enviar essas mudanças ou abrir PR antes da avaliação manual solicitada. A atualização inicial de status se limita à SHIFU-88, conforme etapa 1; não concluir a task ou alterar outras issues. Estas são instruções para o agente implementador; a edição deste plano não executa ações no GitHub/Jira.

### Etapa 1 — Abrir e publicar a branch; verificar o Jira

Reinspecionar status, diff e fontes; preservar qualquer trabalho que tenha surgido depois desta pesquisa. Verificar remote e autenticação `gh auth status`. Buscar a `main` remota antes de criar a branch. Com worktree segura, criar a partir de `origin/main`, não de uma branch de outra task:

```text
git fetch origin main --prune
git switch -c feat/server/SHIFU-88-react-questions origin/main
git push --set-upstream origin feat/server/SHIFU-88-react-questions
git ls-remote --heads origin refs/heads/feat/server/SHIFU-88-react-questions
```

O nome proposto segue `<tipo>/<escopo>/<descricao-curta>` de `documentation/development/branch-strategy.md`, inclui a chave Jira exigida pelo fluxo SDD e usa `server`, um escopo explicitamente permitido. A única branch contém a entrega integrada Web/Server. O documento ainda tem exemplos legados ANI/mobile; não copiá-los. Se a branch já existir, inspecionar e reutilizar somente se for desta entrega, sem recriá-la ou sobrescrever trabalho.

Publicar imediatamente após criar/reutilizar a branch, antes de implementar código ou criar commits de mudanças. Confirmar upstream, existência do ref remoto e SHA igual ao commit-base escolhido; registrar nome, SHA e resultado no handoff/Evaluation quando disponível. Não usar force push ou criar commit vazio para tornar a branch visível. Preservar este documento local na raiz ao trocar de branch; sua existência não exige commit antecipado.

Em seguida, verificar pelo Atlassian MCP se a integração GitHub–Jira associou a branch à **SHIFU-88** e se a automação de branch criada mudou a task para o estado de trabalho em andamento. A chave no nome ajuda a associação, mas o push sozinho não comprova vínculo nem transição de status. Não presumir que a automação está configurada.

Se o status não for atualizado automaticamente, consultar as transições disponíveis da SHIFU-88 e executar a transição válida para o estado de trabalho em andamento definido no projeto, usando o ID real retornado, sem inventar nome/ID. Esta atualização específica integra a sequência solicitada pelo usuário; não transicionar outras issues, alterar requisitos ou marcar conclusão. Ler a issue novamente e registrar status observado e link. Se a integração, a transição ou a permissão estiver indisponível, diagnosticar e informar a pendência sem alegar sucesso; não iniciar as mudanças até resolver a etapa inicial ou obter orientação explícita do usuário sobre a pendência. Não criar automações ou vínculos artificiais como efeito colateral.

### Etapa 2 — Especificar e implementar

Seguir `documentation/prompts/create-spec-prompt.md` e `implement-spec-prompt.md`. Criar uma feature nova, proposta `documentation/features/learning/react-code-question/`, com `spec.md`, `evaluation.md` e `design/handoff.md`/referências. Não criar `plan.md` no repositório. A Spec deve fixar contratos, RF/CA e checkers; Evaluation registra resultados reais, não uma lista de tarefas históricas.

Este roteiro não substitui o requisito de revisão da Spec: o prompt vigente exige revisão independente e aceite explícito do contrato escrito antes de marcar `ready`. Essa revisão preparatória é distinta da avaliação manual do produto, obrigatória depois dos testes e antes de commits/PR. Reaproveitar decisões já tomadas; perguntar somente sobre lacunas materiais, diretamente na conversa conforme AGENTS.md.

Ler integralmente o Rule Pack selecionado pelo router: TypeScript, Python, UI, widget testing, Core, use-case testing, REST, controller testing, Database, Provision e Commit. Acrescentar Routing se houver alteração de rotas; Server App, Messaging/Jobs e AI conforme os caminhos efetivamente alterados. Repetir descoberta se o escopo expandir. Se `.codegraph/` passar a existir, consultar comportamento e consumidores antes de novas buscas; não criar/reindexar por iniciativa própria.

Confirmar APIs incertas na documentação atual via Context7 quando disponível, depois de verificar versões instaladas. WebContainers `^1.6.4`, React `^19.2.0`, Vite `^8.0.0`, Vitest `4.1.6` e Playwright `1.63.0` já constam dos manifests; resolver a versão efetiva pelo lockfile.

**2A. Contratos e validação autoritativa.** Criar o contrato curricular React, política opcional de arquivos adicionais e snapshot Shared. Atualizar uniões/exportações, cálculo de revisão curricular e projeção de conceitos. Paths de partida:

- `apps/server/src/shifu/curriculum/core/domain/{structures/activity_question.py,entities/activity.py}` e novos tipos React no mesmo módulo.
- `apps/server/src/shifu/shared/core/domain/structures/curriculum_learning_activity_snapshot.py` e snapshot React planejado.
- `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`.
- `apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py`.

Fixar no contrato quais arquivos são iniciais editáveis, fixos e adicionais. Validar nomes, caminhos relativos canônicos, diretório por segmento, extensão e contagem; rejeitar absolutos, traversal, barras invertidas/NUL, duplicatas, colisões, arquivos de configuração/dependências e payloads que tentem alterar comandos. Manter limites de tamanho coerentes entre Web/Server. Não confiar na validação da interface. Não introduzir renomeação/exclusão ou permissões que o escopo não solicita.

**2B. Integrar Learning, HTTP e persistência.** Atualizar os casos de uso existentes em `apps/server/src/shifu/learning/core/use_cases/`:

```text
get_choice_activity_use_case.py
preview_activity_question_feedback_use_case.py
submit_choice_activity_use_case.py
evaluate_choice_activity_use_case.py
get_choice_attempt_use_case.py
retry_choice_evaluation_use_case.py
```

Centralizar a política de resposta para preliminar e final. Atualizar os controllers equivalentes em `learning/rest/controllers/`, schemas, mappers e exemplos `.rest` correspondentes. Reutilizar `CodeAnswer`/`CodeSubmittedFile`. Atualizar `learning/database/sqlalchemy/mappers/activity_attempt_mapper.py`, hoje com fallback de todo tipo diferente de stdin para escolha.

Salvar e usar o snapshot da submissão, incluindo política/projeto/rubrica relevantes; resultados históricos não podem depender do currículo atual. Preservar transação tentativa+avaliação+outbox, chave idempotente, mesmos arquivos no retry e aplicação única de efeitos. Reutilizar `learning/messaging/inngest/jobs/evaluate_choice_activity_job.py`; manter proteção contra eventos antigos, experiência removida e resultados repetidos. Não executar código do aluno no processo da API. Não usar preview/terminal como prova de correção nem testes determinísticos para definir a nota.

**2C. Runtime React.** Estender a porta `apps/web/src/core/learning/code-practice-runner.ts` ou criar porta irmã, conforme a Spec, e compor o adapter em `apps/web/src/provision/learning/`. Separar o ciclo de vida do servidor React da execução curta stdin. A plataforma pode preparar somente dependências fixas e configuração confiável curricular; isso não autoriza o aluno a instalar pacotes. Expor inicialização, atualização, pronto, URL de prévia e erro; rejeitar comandos fora da allowlist, proteger autenticação/estado Shifu e descartar processos/listeners/URLs antigos. Manter edição/envio disponíveis se a prática falhar. Preservar COOP/COEP existentes e conferir o requisito de isolamento na execução real.

**2D. Web e rascunhos.** Atualizar:

- `apps/web/src/core/learning/choice-activity.ts` e `src/rest/services/learning-service.ts`.
- `src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts}`.
- Composição React planejada sob `activity-page/`, reutilizando `code-question/`, `components/code-editor/` e `components/code-file-tree/` nas responsabilidades comuns.
- `activity-page/question-feedback/` e `choice-result-page/choice-result-detail/`.

Manter rotas existentes se suficientes; não criar página/endpoint paralelo por conveniência. Substituir checks stdin-only com tipagem explícita, sem transformar todo tipo desconhecido em código. Preservar escolha, stdin e diagnóstico.

Para autosave, usar identidade confiável da conta e da experiência, não email ou apenas skillId. Validar schema/revisão e permissões antes de restaurar. Não misturar Habilidade igual em Objetivos diferentes, experiências recriadas ou contas. Implementar leitura de alterações entre abas e ordenação de salvamentos para impedir gravação antiga atrasada sobre a última versão. Tratar armazenamento indisponível, quota e dados corrompidos com mensagem e proteção ao sair. Logout preserva o rascunho da conta; remoção da experiência/Objetivo e encerramento da conta devem invalidar/apagar os respectivos novos rascunhos e impedir recriação por aba antiga. Integrar pontos existentes; se faltar contrato de lifecycle necessário, registrar a dependência e resolver o recorte, sem declarar o requisito comprovado nem implementar silenciosamente toda SHIFU-98.

Autosave não autoriza voltar/editar questões já avançadas. A preliminar congela os arquivos; reavaliar usa a mesma resposta, mesmo com alterações vindas de outra aba. Histórico oficial permanece somente leitura e não inicia runtime de prática.

**2E. Design e divisão de trabalho.** Os frames `ZWAmr` e `ZQZkP` foram inspecionados no Pencil: desktop 1440×900, enunciado/arquivos à esquerda, editor ao centro, prévia/terminal à direita, estado do rascunho e rubrica pública. O segundo mostra o ícone `file-plus` e informações de permissão. Exports da pesquisa para consulta: [ZWAmr](C:/Users/Luciano/.codex/visualizations/2026/10/14/01a13cb6-9f76-7213-a8f5-3d62b97f3792/SHIFU-88-referencias/ZWAmr.png) e [ZQZkP](C:/Users/Luciano/.codex/visualizations/2026/10/14/01a13cb6-9f76-7213-a8f5-3d62b97f3792/SHIFU-88-referencias/ZQZkP.png). São referências históricas locais; se indisponíveis, reexportar pelo Pencil MCP a partir do design atual.

Obter estado/schema do Pencil antes de operar e revalidar os frames atuais pelo MCP. Não ler bytes do `.pen` pelo filesystem. Mapear tokens e primitives existentes; salvar referências oficiais no bundle da nova Spec. Não ativar HTTP por aparecer na estrutura reutilizável do painel. Os dois frames são desktop: definir adaptação mobile conforme padrões existentes e registrar o que é referência direta e o que é adaptação, sem alegar que existe frame mobile aprovado não verificado. Registrar também as referências adequadas para preliminar e resultado.

Após estabilizar contratos, delegar streams independentes com paths exclusivos: Curriculum/Shared; Learning Server; runtime React; UI/rascunhos. O orquestrador mantém Spec/Evaluation, contratos compartilhados, integração e validação final. Evitar que runtime/UI editem simultaneamente a mesma porta ou widget; atribuir ownership exato. Revisar todos os diffs retornados.

### Etapa 3 — Testar e revisar antes de chamar o usuário

Durante a construção, usar verificações focadas. Depois da integração, executar **a regressão completa** abaixo, autorizada pelo pedido explícito de verificar todos os testes. Não confundir cobertura completa da seleção com garantia absoluta de ausência de bugs.

**Testes da feature e regressões obrigatórias.** Estender casos de uso e controllers existentes de get/preview/submit/evaluate/get attempt/retry e `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`. Estender widgets/hooks de ActivityPage/CodeQuestion/editor/árvore/resultado e `apps/web/tests/learning/{activity-page,choice-result-page}.test.ts`. Novos testes devem seguir os limites atuais: comportamento por casos de uso/controllers/jobs/widgets/rotas; não criar suítes próprias de provider, adapter REST, banco ou query/action hook.

Cobrir: com/sem permissão adicional; limites 0/máximo/excedido; paths e colisões inválidos; tentativa direta de adulterar config/deps/comandos; nomes/extensões autorizados; combinação de questões; render React real e atualização automática; saída/erros e comandos; falha/incompatibilidade de runtime; isolamento conta/experiência/revisão; logout/login; duas abas e gravações fora de ordem; falha de storage; limpeza sem ressurreição; preliminar sem tentativa/efeito; inconclusão obrigatória e retry congelado; envio incompleto; replay/chave divergente; nota ponderada; falhas/retry oficial; evento antigo; efeito único; histórico recuperado após mudança curricular; diagnóstico e progressão/Gamification consumidores sem regressão.

**Preparação do ambiente.** Verificar Node/Python dos arquivos de runtime, pnpm/uv/lockfiles, Docker e serviços. CI usa Node 24.20.0, Python 3.13.5, pnpm 10 e uv 0.11.26. Quando instalação for necessária, usar lockfiles (`pnpm install --frozen-lockfile`, `uv sync --frozen`), sem upgrade incidental. Usar env explícito compatível com CI, sem imprimir segredos. Tests Server criam PostgreSQL/Redis descartáveis; jobs também usam Inngest/Mailpit e exigem porta callback disponível, por padrão 7777. Serializar checks que disputam essa porta. Fixtures verificam registro de funções, não apenas container em execução. Preparar os recursos locais de NLP exigidos pela configuração atual, como faz o CI.

Este checkout Windows tem comandos de startup Playwright e tarefas Poe que usam POSIX (`exec`, `.venv/bin`, `find/grep/xargs`). Confirmar ambiente compatível ou servidores previamente iniciados conforme configuração; não pressupor execução nativa bem-sucedida, não alterar tooling transversal por conveniência e não transformar skip em aprovação. Diagnosticar e registrar bloqueios.

**Web — executar na raiz:**

```text
pnpm --filter web check:types
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web test:coverage
pnpm --filter web test:integration
pnpm --filter web build
```

`test:coverage` já executa toda a suíte Vitest, portanto não duplicar `test:unit`. O script unit usa `--passWithNoTests`: conferir contagens, não só exit code. Não há threshold de cobertura Web configurado.

**Server — executar em `apps/server`:**

```text
uv run poe check:types
uv run poe check:lint
uv run poe check:architecture
uv run poe test
uv run poe build
```

Antes de `poe test`, definir `SHIFU_RUN_REAL_INNGEST_TESTS=1` no ambiente do processo. Em PowerShell: `$env:SHIFU_RUN_REAL_INNGEST_TESTS = '1'`; preservar/restaurar o valor anterior ao terminar. Assim o full pytest inclui os jobs reais. Alternativamente, executar a suíte completa e depois `uv run poe test:jobs`, registrando que apenas a segunda execução forneceu a prova dos jobs. Porta ocupada/Docker indisponível ainda podem causar skip, que não vale como sucesso.

`poe test` é `pytest -s -x -vv`: corrigir falhas e repetir até a seleção completa terminar. `test:unit` e `test:integration` isolados deixam testes de outras pastas de fora. Não há pytest-cov/coverage Server configurado atualmente; não inventar percentual. Conferir wheel e sdist gerados em `apps/server/dist/`, conforme CI.

**Email — executar na raiz:**

```text
pnpm --dir packages/email check:code
pnpm --dir packages/email check:types
pnpm --dir packages/email build
```

O pacote não possui suítes unit/integration próprias; seus gates reais e o contrato de distribuição Server são a verificação disponível. Revisar qualquer saída gerada e não versionar artefatos de runtime indevidamente.

**Migrations, mutação e complexidade.** Em alvo descartável, migrar até head e executar `uv run alembic check` como no CI. Atenção: `poe db:upgrade` pode carregar `.env.local`; não usá-lo sem garantir o alvo descartável. Nunca resetar banco/volumes compartilhados. Se o JSON existente for suficiente, documentar ausência de migration com prova da compatibilidade histórica.

Avaliar mutação para regras críticas alteradas. Se contratada, executar `uv run poe test:mutation --core --files <paths-exatos>` somente nos arquivos Server `core/use_cases/**` novos/alterados e testes relacionados; registrar mutantes sobreviventes/equivalentes e duração. Não rodar `--all` local por interpretar “todos os testes” como autorização de toda análise de mutação. CI já executa core completo em 12 shards e gate/summary próprios (config atual: mínimo de 70% para código novo e tolerância de regressão de 5 pontos percentuais por módulo). Web/Email: mutação N/A. Biome e Ruff C90 fornecem os checks configurados de complexidade; não existe runner quantitativo separado para alegar aprovação.

**Percurso real e visual.** Usar Playwright CLI em `apps/web`, verificar `docker compose ps`, health Web/API e estado autenticado local `.playwright-cli/states/shifu-auth-state.json`. Se necessário, autenticar pelo formulário visível. Preparar dados isolados com uma Atividade React válida e três a cinco questões; não executar seed/reset compartilhado. Confirmar edição, novo arquivo permitido, atualização real da prévia, terminal, autosave e retorno após login, preliminar, envio completo e leitura do resultado persistido após retornar. Verificar URL, requests, teclado/foco, console e persistência. Mocks de BFF não provam autenticação/persistência real; se um avaliador determinístico isolado for usado, registrar essa limitação separadamente da integração real com provedor.

Capturar desktop 1440×900 e mobile definido na Spec, comparar visualmente com referências e registrar adaptações. Guardar runtime artifacts em `apps/web/.playwright-cli/{logs,screenshots,snapshots,states}/`; não commitar storage state, logs ou screenshots de execução. Parar somente sessões/processos iniciados pela task ao concluir a validação; manter serviços compartilhados. Preparar comandos seguros para reabrir o ambiente durante o aceite humano.

Lançar `implementation-reviewer-agent` e `visual-reviewer-agent` em paralelo sobre o mesmo candidato integrado, usando evidências já capturadas; visual segue `documentation/agents/visual-reviewer-agent.md`. Corrigir achados bloqueantes e repetir apenas verificações invalidadas. Não declarar aprovação visual apenas por salvar imagens.

Evaluation deve registrar RF/CA→CI/VM→EV, candidato, comandos, contagens, duração, falhas/skips, ambiente, referências/capturas, limitações, paths sujos e processos/portas. Não usar testes antigos de outra entrega como evidência automática desta feature. Se corrigir após falha, não apresentar execução focada como se fosse uma nova suíte completa verde; fechar honestamente o requisito de regressão completa.

### Etapa 4 — Pedir avaliação manual e parar

Somente com testes/reviews obrigatórios aprovados, apresentar ao usuário: resumo implementado, evidências, resultados/limitações, URL local e setup reproduzível. Entregar checklist curto: editar React e ver prévia; criar arquivo permitido; confirmar rascunho após retorno; conferir rubrica e preliminar; enviar Atividade completa e consultar resultado histórico; verificar mobile/teclado.

Pedir explicitamente a avaliação manual e a autorização para **commitar as mudanças e abrir PR**. Aguardar resposta afirmativa. Silêncio, testes verdes ou um comentário sobre a interface não são aprovação. Até lá, manter somente a branch-base já publicada na etapa 1; deixar as modificações locais sem commit/push/PR e registrar o handoff. Se o usuário pedir correção, implementar, rodar checks afetados e reapresentar o candidato para novo aceite.

### Etapa 5 — Após aprovação, commits e PR

Inspecionar diff completo e stage somente paths desta task, incluindo Spec/Evaluation/handoff/referências necessários. Excluir env, credenciais, estados de navegador, bancos, caches, cobertura, logs e runtime artifacts. Não alterar trabalho alheio. Se um `.pen` realmente mudar nesta entrega, incluí-lo como arquivo opaco pelo path exato; não publicar modificação alheia.

Usar Conventional Commits com chave **SHIFU-88**, descrição imperativa em inglês, minúscula e sem ponto. Manter header até 72 caracteres, que satisfaz os dois documentos. Exemplos de agrupamentos coerentes, ajustados ao diff real:

```text
feat(server): SHIFU-88 support React activity assessments
feat(web): SHIFU-88 add React practice and local drafts
test: SHIFU-88 cover React activity recovery
docs: SHIFU-88 record React delivery evidence
```

Não é necessário separar testes da feature artificialmente. O config real é `commitlint.config.cjs`; o guia cita `.mjs` inexistente e tipos diferentes. Usar tipos compatíveis `feat/fix/docs/test/refactor/chore/ci/style`; não adotar `perf/build/revert` apenas pelo guia antigo. Não alterar esse tooling incidentalmente. Hooks devem rodar: pre-commit chama lint global, commit-msg valida mensagem. Se revelarem falha preexistente, diagnosticar e informar, sem ignorar hook nem fazer limpeza global.

Verificar novamente as versões mais atuais do Confluence e reconciliá-las conforme a regra permanente. Verificar o remote, buscar a `main` mais recente e incorporar por **merge**, conforme `create-pr-prompt.md`/`conclude-spec-prompt.md`; não usar rebase nem force push. Uma atualização já incorporada pode ser reutilizada. Se a main ou o contrato Confluence mudarem após o aceite e a integração/reconciliação afetar comportamento, contrato, fixtures ou dependências, refazer checks afetados e obter novo aceite do candidato relevante antes de publicar as modificações/PR. Uma mudança apenas de SHA não invalida prova de código idêntico. Imediatamente antes do push das mudanças, verificar que a main remota atual é ancestral de HEAD; se não for, reconciliar novamente. Nenhum commit de merge deve anteceder a autorização da etapa 4.

Conferir autenticação `gh`, procurar PR existente da mesma branch/Jira e atualizar em vez de duplicar. Fazer push normal dos commits aprovados para a mesma branch remota publicada na etapa 1 e abrir PR com base `main`; não fazer merge/deploy. Título sugerido: **[SHIFU-88] Questões React nas Atividades de aprendizagem**.

Título/body em pt-BR, conforme `documentation/prompts/create-pr-prompt.md`: Objetivo; PRD; Requisitos afetados; Jira; Implementação técnica; Alterações de regras de negócio quando aplicável; Testes manuais; Validações automatizadas; Migrations e artifacts gerados; Limitações conhecidas. Usar URLs canônicas, IDs/versões atuais, evidências observadas e disposição real. Ao usar `gh`, passar body multilinha por arquivo, sem escapes literais acidentais. Não afirmar que SHIFU-111/SHIFU-23 foram concluídas automaticamente.

Ler o PR publicado de volta, informar link/base/head/SHA e anexá-lo à conversa quando a ferramenta estiver disponível. Acompanhar checks aplicáveis do **head atual**: `Verify web application`, `Verify server application` e, conforme filtros, `Verify email package and server contract`. Corrigir falhas e tratar conversas bloqueantes com evidência; não marcar Spec/Evaluation como entrega publicada concluída com CI pendente/falho ou review bloqueante. A criação do PR não autoriza seu merge. O fluxo documentado de main requer ao menos uma aprovação de PR, distinta do aceite manual local.

## 3. Condição de entrega

O agente deverá devolver: branch publicada no início, evidência do vínculo/status observado da SHIFU-88 no Jira, versões mais atuais do Confluence reconciliadas, commits aprovados, PR e SHA, Spec/Evaluation, lista de critérios atendidos, resultados completos dos testes, evidência do percurso real/visual e registro do aceite manual. Qualquer checker não executado, skip obrigatório, limitação de Windows/Docker/IA ou dependência de lifecycle fica explicitamente pendente; nunca transformar ausência de prova em “não quebrou nada”.

Esta revisão salvou somente o plano `SHIFU-88-IMPLEMENTACAO.md` na raiz do projeto. A pesquisa inicial exportou os dois frames aprovados para consulta. Nenhuma branch, commit, publicação ou atualização de Jira/Confluence foi executada ao preparar estas instruções, e o arquivo Pencil não foi alterado. O estado limpo registrado no início descreve o baseline anterior à adição deste documento.

## 4. Retomada e pendências atualizadas — 14/10/2026

Esta seção registra o estado observado durante a tentativa de validação local. Ela complementa o roteiro acima e não aprova a entrega nem altera os requisitos da Spec.

### Evidências novas

- O helper em `apps/server/devtools/react_browser_fixture/prepare.py` foi corrigido para atualizar a sequência da competência criada pela seed, em vez de inserir outra linha para a mesma competência. Ruff, formatação, compilação Python e `git diff --check` passaram para o helper. A preparação chegou ao fim com sucesso no PostgreSQL descartável `127.0.0.1:15448/shifu` e criou a atividade “Prática React: estado e contador”.
- O login real da conta seed funcionou no Web dedicado após alinhar o segredo BFF do processo Web com o da API isolada. Não ler nem copiar o segredo já configurado no `.env.local`; no ambiente isolado, definir o valor local correspondente nos dois processos.
- API dedicada `http://localhost:17779/health` e rota Web `http://localhost:17000/login` responderam HTTP 200. O Web e a API usaram o banco descartável, Redis `16379`, Inngest dedicado `18298` e avaliador determinístico local `18779`. A API respondeu HTTP 200 às requisições de registro `PUT /api/inngest`; a lista de funções do Inngest dedicado ainda precisa ser confirmada antes de submeter avaliação final. Nenhum evento foi enviado ao Inngest compartilhado e nenhum dado foi gravado no banco compartilhado.
- A navegação autenticada encontrou a atividade na competência e abriu sua rota, mas a página exibiu “Não foi possível carregar esta Atividade”. A Server Function de carregamento respondeu `{kind: "invalid-request"}`; a API não recebeu uma requisição de leitura da atividade. A causa ainda não foi confirmada. Ao retomar, verificar a validação dos identificadores da rota (`isIdentifier`) e os IDs gerados no fixture antes de alterar código de produção.
- O erro anterior `duplicate key value violates unique constraint curriculum_sequences_pkey` está resolvido no helper e não deve ser repetido. Para recriar o cenário, subir novamente os serviços descartáveis e executar o `prepare.py` com URL explícita e `SHIFU_REACT_FIXTURE_DISPOSABLE=1`. A seed limpa as tabelas, portanto jamais a apontar para o banco compartilhado.
- A instância Playwright autenticada foi aberta e chegou à atividade; não foi salvo estado autenticado reutilizável. Os snapshots, logs e capturas gerados estão sob `apps/web/.playwright-cli/` e são artefatos locais; não os incluir no stage.

### Próximos passos ao retomar

1. Recriar somente PostgreSQL, Redis e Inngest descartáveis; repetir a preparação do cenário garantindo que a chave de criptografia temporária usada na seed também seja definida na API isolada. Iniciar o stub determinístico local e a API/Web em `17779`/`17000`. No Web isolado, alinhar explicitamente o segredo BFF com o da API para evitar 401 no login.
2. Diagnosticar e corrigir o `invalid-request` da atividade. Validar a solução com o teste focado da rota/identificador e confirmar no navegador que a API recebeu a leitura e a atividade foi carregada.
3. Confirmar no Inngest descartável que `learning-evaluate-choice-activity` está registrada. Completar VM-01/VM-02 no Playwright CLI: questão mista de escolha e React, edição, criação de arquivo autorizado, terminal e prévia WebContainer com atualização; segurança de sandbox/origem; rascunho após logout/login no mesmo navegador; rubrica e avaliação preliminar congeladas; reavaliação de falha inconclusiva; envio final e recuperação; resultado persistido e histórico após retorno. O avaliador determinístico é somente evidência do fluxo local, não da qualidade do provedor real.
4. Verificar teclado/foco e capturar desktop 1440×900 e mobile 390×844 nos diretórios `.playwright-cli` prescritos. Atualizar `evaluation.md` com observações, requests, limitações, arquivos de evidência e o estado real de cada VM/EV; concluir também os gates Server ainda pendentes segundo a seção 2C.
5. Após integrar a correção, executar em paralelo a revisão independente de implementação e a revisão visual exigidas por `AGENTS.md`, usando o mesmo candidato e as capturas novas. Corrigir achados bloqueantes e repetir os checks afetados. Reler as versões vigentes dos PRDs antes da conclusão e registrar a reconciliação.
6. Apresentar o candidato e o checklist manual da etapa 4 ao usuário. Aguardar aprovação explícita antes de commitar mudanças, atualizar a branch remota ou abrir PR. Não atualizar Jira/Confluence manualmente.

### Estado dos serviços e preservação

Foram encerrados os serviços iniciados para esta validação: Vite na porta `17000`, API na `17779`, stub na `18779`, browser Playwright da task e containers `shifu88-vm01-*` nas portas `15448`, `16379`, `18298`/`18299`. A verificação confirmou essas portas fechadas e os processos locais do usuário ainda escutando em `7000`/`7777`. Os containers eram descartáveis; seus dados não devem ser considerados persistentes. Os serviços compartilhados do Docker Compose foram mantidos. Preservar as mudanças locais de SHIFU-88, o plano não rastreado e a alteração autorizada de `pnpm-workspace.yaml`.

## 5. Retomada e bloqueio de ambiente — 17/10/2026

Esta seção substitui as pendências já resolvidas da seção 4 como ponto de partida da próxima sessão. A implementação foi pausada ao encontrar o bloqueio de regressão completa descrito abaixo, conforme a instrução do usuário de parar e explicar problemas.

### Concluído nesta sessão

- O `invalid-request` era causado pelo ID de atividade do fixture com 25 caracteres. O ID em `apps/server/devtools/react_browser_fixture/activity.py` foi corrigido para 26 caracteres. Em seguida, a API retornou 404 porque as duas questões de escolha do fixture não tinham `correct_explanation` e `incorrect_explanation`, exigidas pelo provider. O fixture foi corrigido; o registro do PostgreSQL descartável foi ajustado somente para continuar o percurso já aberto. Ao retomar, recriar o cenário pelo helper atualizado para provar sua preparação de ponta a ponta, sem apontá-lo ao banco compartilhado.
- Login real no ambiente isolado e percurso das duas questões de escolha passaram, incluindo feedback individual de 100% e avanço até a terceira questão React. O editor, a árvore, a rubrica pública e o estado de rascunho apareceram. Um arquivo permitido `src/components/Badge.jsx` apareceu na árvore. A prévia WebContainer instalou dependências e iniciou Vite, mas mostrou uma divergência: o SDK retorna HTTPS em `*.local-corp.webcontainer-api.io`, enquanto o código aceitava apenas `*.webcontainer.io`. O runner e o hook agora aceitam os dois sufixos, sempre exigindo HTTPS e origem diferente da aplicação. Em nova sessão, a prévia apareceu “Em execução”, com `sandbox="allow-scripts"`, origem distinta de `http://localhost:17000` e sem erros de console naquele momento.
- A tentativa inicial de criar o arquivo adicional causou `ENOENT` no WebContainer porque `src/components` não existia. O runner agora cria o diretório pai recursivamente antes de gravar. **Ainda falta repetir a criação na prévia após essa correção** e verificar a atualização real do arquivo e do iframe. A criação visual do arquivo no rascunho, sozinha, não prova a gravação no runtime.
- Os checks focados após essas correções passaram: Web `tsc --noEmit`, Biome nos três arquivos afetados e 6 testes Vitest do widget React; Ruff check/format no fixture e `git diff --check`. Uma tentativa Vitest dentro do sandbox falhou antes de coletar testes por `EPERM` no diretório temporário; a repetição elevada passou. A regressão completa Web anterior (524 testes) e o build Web anterior são de 15/10 e devem ser renovados após as mudanças atuais.
- Os checks Server de tipos, lint e arquitetura passaram nesta sessão. A suíte completa com `SHIFU_RUN_REAL_INNGEST_TESTS=1` e porta de callback `7779` executou **721 testes aprovados, 17 warnings e 1 erro de setup**, em cerca de 760 s. Os jobs reais anteriores de Communication, Gamification e Identity passaram. O primeiro erro foi em `tests/messaging/inngest/jobs/intelligence/test_mentor_catalog_abstention_job.py::TestMentorCatalogAbstentionJob::test_missing_answer_vectors_abstain_without_model_calls_or_runtime_reindex`: a API de teste não iniciou em `127.0.0.1:7779/health` porque o modelo `intfloat/multilingual-e5-small` na revisão fixa `614241f622f53c4eeff9890bdc4f31cfecc418b3` não estava em cache e o download do Hugging Face falhou. O CI prepara esse recurso com `SentenceTransformersEmbeddingsProvider(local_files_only=False)` antes dos jobs. Isso é bloqueio de recurso de NLP no ambiente; não é resultado verde da suíte nem diagnóstico de defeito da feature. Log local: `%TEMP%\shifu88-server-full-test-20261017.log`. O build Server não foi iniciado após esse erro.

### Pendências para a próxima retomada

1. Preparar o modelo fixo `intfloat/multilingual-e5-small` (revisão acima) no cache local acessível aos subprocessos dos testes, seguindo o passo **Prepare pinned local Mentor model** em `.github/workflows/server-app-ci.yaml`; não modificar código de produção nem mascarar o teste. Reexecutar o caso que falhou e então **a suíte Server completa com Inngest real** até o fim; registrar contagens, warnings, skips e duração. Prosseguir com build Server e `alembic check` no banco descartável.
2. Recriar o fixture pelo `prepare.py` atualizado apenas em PostgreSQL descartável `127.0.0.1:15448/shifu`, com reconhecimento explícito `SHIFU_REACT_FIXTURE_DISPOSABLE=1`, chave temporária compartilhada com a API isolada e BFF secret alinhado no Web isolado. Repetir VM-01/VM-02 no Playwright CLI: criação e edição de arquivo na pasta permitida; prévia realmente atualizada e terminal; validação de path inválido; rascunho após logout/login; rubrica, preliminar, congelamento e recuperação; envio final pelo Inngest descartável e resultado histórico persistido. O stub de avaliação apenas valida o fluxo local, não a qualidade do provedor externo.
3. Capturar e inspecionar desktop 1440×900 e mobile 390×844, teclado/foco, URLs, requests e console. Atualizar Evaluation com evidência real; revisar o candidato integrado em paralelo com `implementation-reviewer-agent` e `visual-reviewer-agent` após as capturas, corrigindo achados e repetindo os checks afetados. Renovar gates Web completos e Email conforme a etapa 3. Reler os PRDs vigentes antes da conclusão.
4. Apresentar o candidato para avaliação manual da etapa 4. Não commitar, atualizar a branch remota ou abrir PR antes da aprovação explícita do usuário; não transicionar Jira manualmente.

### Estado ao pausar

A sessão Playwright `shifu88`, Vite `17000`, API `17779`, stub `18779` e os containers descartáveis `shifu88-vm01-*` foram encerrados. As portas correspondentes ficaram fechadas; os processos locais do usuário em `7000`/`7777` e os serviços compartilhados do Docker Compose permaneceram ativos. O banco do fixture era descartável e seus dados foram removidos junto com o container. As mudanças de código, Spec/Evaluation, plano não rastreado e `pnpm-workspace.yaml` autorizado permanecem locais, sem commit/push/PR.

### Atualização de retomada — 17/10/2026

- O modelo fixo `intfloat/multilingual-e5-small` foi baixado e carregado pelo comando de preparação equivalente ao CI. O teste de abstinência que antes falhava passou isoladamente. O fixture React atualizado foi recriado com sucesso em PostgreSQL descartável `shifu88-vm02-postgres` na porta `15448`.
- Os gates Web atuais passaram: tipos, arquitetura (445 módulos/1.504 dependências), cobertura (91 arquivos/524 testes) e build. Os gates Email `check:code`, `check:types` e `build` passaram. O Biome Web terminou com código 0 e sete avisos preexistentes de Intelligence.
- A suíte Server completa com Inngest real avançou até **729 testes aprovados**, 17 warnings e 1 falha em cerca de 22min52s. Falhou em `test_mentor_langfuse_sdk_job.py::test_registered_native_job_exports_anonymous_operational_spans_with_actual_sdk`, que espera encerramento gracioso da aplicação de teste. Repetido isoladamente, o mesmo caso falhou em 79,80 s. O fixture chama `subprocess.Popen.terminate()` e só aceita exit code `0` ou `-SIGTERM`; no Python para Windows, `terminate()` chama `_winapi.TerminateProcess(handle, 1)`, de modo que o código `1` observado é resultado do próprio fixture. Isso não estabelece defeito na SHIFU-88, mas impede registrar a regressão completa como aprovada no Windows sem corrigir/adequar o fixture ou rodar esse gate em Linux.
- A pedido do usuário de parar diante de problemas, a implementação foi novamente interrompida nesse diagnóstico. Ainda faltam Server build e `alembic check` descartável; a repetição VM-01/VM-02 para escrita de arquivo, rascunho, avaliação, resultado e capturas; revisões paralelas; e reconciliação documental. O PostgreSQL descartável `shifu88-vm02-postgres` foi encerrado e a chave temporária VM02 removida. Os demais serviços isolados Web/API/Inngest/Redis/stub já estavam parados; os serviços compartilhados do usuário permanecem intocados. Nenhum código foi commitado ou publicado.

### Aceite manual e disposição final — 17/10/2026

- O usuário autorizou prosseguir sem corrigir o teste de fixture Langfuse específico do Windows, desde que a exceção seja registrada. A suíte Server completa permanece sem resultado verde; o resultado conhecido foi 729 testes aprovados e uma falha desse fixture.
- No ambiente isolado `shifu88-vm03`, o navegador autenticado concluiu as duas questões de escolha, editou o projeto React, criou `src/components/Badge.jsx`, recebeu avaliação preliminar 75 e concluiu a tentativa com resultado persistido 87,5 e arquivos históricos. As capturas de resultado desktop/mobile foram inspecionadas. A prévia iniciou Vite no WebContainer, mas o iframe no navegador de automação exigiu Storage Partitioning para o Service Worker; a renderização da prévia não foi comprovada.
- A validação de arquivo adicional no hook foi corrigida para não colidir com o próprio arquivo; a árvore passou a refletir arquivos criados sem recarregar; o detalhe da tentativa passou a preservar `kind=react`. Depois das correções, 20 testes Web focados, TypeScript, Biome nos arquivos afetados, 5 testes Server focados, tipos Server e Ruff passaram. Os gates Server de lint, arquitetura, build e Alembic em banco descartável também passaram antes da última correção do detalhe.
- O usuário declarou que acompanhou visualmente os testes, aprovou o resultado e autorizou explicitamente commitar e abrir o PR. Publicar com as limitações acima registradas, sem transição manual do Jira.
