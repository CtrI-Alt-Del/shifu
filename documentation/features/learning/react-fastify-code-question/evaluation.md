---
title: Questões integradas React + Fastify — avaliação
status: completed
spec: ./spec.md
last_updated_at: 2026-10-25
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete. Spec revisão3 completed, CA-01–13 Complete/Passed. |
| Automated checks | CI-01–09 e23checks remotos aplicáveis Passed. Pós-merge:186HTTP,32browser, Planning186unit, Submit100unit, jobs5+1em runs distintos, integridade406, retrieval real3. EV-36–46. |
| Type / lint / complexity | Gates configurados Server/Web Passed após merge. Tipos, lint, complexidade qualitativa, arquitetura e build em EV-37. Quantitativa dedicada Not applicable conforme CI-07. |
| Manual checks | VM-01 atualizado após main Passed em EV-40. VM-02 retido por identidade/restauração/sincronização inalteradas. Login novo comprovado em EV-40. |
| Visual checks | VM-03/04 Passed. Dez estados exigidos aprovados pelo Visual Reviewer. Capturas afetadas atualizadas para revisão 3, com adaptação mobile e resultado oficial após terminar a animação. |
| Independent review | Auditoria de código e visual pós-merge sem novo achado. Visual10/10 retido em EV-41. Parecer final Implementation Reviewer PASS em EV-43, sem achados abertos. |
| Blockers | Nenhum achado aberto. CI do candidato4bea0918Passed. Registro documental final será publicado e seu CI também conferido antes da resposta final. |
| Candidate | codex/shifu-90-spec, main0f1ee09a incorporado em5837ab8d, correção4bea0918. PR45 aberto sem conflitos e sem conversas de review pendentes. Atualização final restrita a Spec/Evaluation. |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01/02/04; EV-02/03/05/17 | Nenhuma obrigação específica pendente. |
| CA-02 | RF-02 | Complete | Passed | CI-01/02/03, VM-01; EV-02/03/04/18/20 | Nenhuma obrigação específica pendente. |
| CA-03 | RF-03 | Complete | Passed | CI-03/04, VM-01; EV-17/18/20 | Nenhuma obrigação específica pendente. |
| CA-04 | RF-04 | Complete | Passed | CI-03/04, VM-01; EV-17/18/20 | Nenhuma obrigação específica pendente. |
| CA-05 | RF-03/05 | Complete | Passed | CI-01/03/04; EV-02/04/05/17 | Nenhuma obrigação específica pendente. |
| CA-06 | RF-06 | Complete | Passed | CI-03/04, VM-02; EV-04/05/11/17 | Nenhuma obrigação específica pendente. |
| CA-07 | RF-07 | Complete | Passed | CI-03/04, VM-02; EV-04/05/11/17 | Nenhuma obrigação específica pendente. |
| CA-08 | RF-08 | Complete | Passed | CI-01/02/03, VM-01/03/04; EV-02/03/17/20/21 | Nenhuma obrigação específica pendente. |
| CA-09 | RF-08 | Complete | Passed | CI-01/02/03; EV-02/03/04 | Nenhuma obrigação específica pendente. |
| CA-10 | RF-09 | Complete | Passed | CI-01/02, VM-01; EV-02/03/20 | Nenhuma obrigação específica pendente. |
| CA-11 | RF-09/10 | Complete | Passed | CI-01/02, VM-01; EV-02/03/20 | Nenhuma obrigação específica pendente. |
| CA-12 | RF-10 | Complete | Passed | CI-01/02/04, VM-01/04; EV-02/03/17/20/21 | Nenhuma obrigação específica pendente. |
| CA-13 | RF-11 | Complete | Passed | CI-03/04, VM-01/02/03/04; EV-11/17/20/21 | Nenhuma obrigação específica pendente. |

# Check Results

EV-01–16 preservam o histórico da revisão 2 e do início da revisão 3. Seus resultados Failed/Blocked/Pending não são reescritos como aprovação. A prontidão atual usa as provas substitutas identificadas nas linhas posteriores e no Progress. Todos os logs e capturas citados ficam em apps/web/.playwright-cli, nas pastas logs, snapshots e screenshots.

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | Preflight / Automated | Passed | Base 8ee992a7, 2026-10-25 | git status --short na worktree separada | Somente duas Rules e artefatos aprovados preexistentes. Nenhum código alterado. CodeGraph ausente nesta worktree. Fontes completas atuais de Learning v26 e Curriculum v13 reutilizadas desta conversa. |
| EV-02 | CI-01 / Automated / CA-01/02/05/08/09/10/11/12 | Passed | Revisão 2, worktree atual, Python3.13.5, Redis descartável do Builder | Seis arquivos pytest de CI-01. Primeiro run 288, 281 Passed e 7 Failed por setup; correção rerun dos dois arquivos preview/submit | 150 Passed em14.02s. Outros138 Passed preservados do run67.35s, sem mudanças cobertas posteriores. 288 cenários atuais nesses runs. Quatro parâmetros novos de caminho/segmento nos limites240/241 e64/65 passaram2.54s em seleção própria, log shifu90-path-boundaries.log. Sem skips. |
| EV-03 | CI-02 / Automated / CA-01/02/08/09/10/11/12 | Passed | Revisão2, PostgreSQL/Redis descartáveis, app real com ambos registries | Quatro arquivos controller na Spec:51Passed225.51s retidos. Correção e nove parâmetros novos:10Passed34.85s | Total61cenários atuais, zero skips. Logs shifu90-ci02.log, correction.log (histórico falho), correction2.log. Assessor externo controlado, sem inferir execução registrada oficial dessa prova. |
| EV-04 | CI-03 / Automated | Passed | Revisão2, Node24.20.0, Vitest | pnpm --filter web test:unit, quatro arquivos CI-03 | Componente10Passed2.01s após correção mobile; revisão de bindings confirmada por10Passed3.48s em shifu90-component-review-correction.log. Hook21+histórico8:29Passed6.86s. Painéis HTTP4 e Terminal7 aprovados na seleção29Passed11.41s com hook então18. Evidência retida por ausência de alterações cobertas posteriores. |
| EV-05 | CI-04 / Automated | Passed | Revisão2, SDK controlado e browser fixtures | pnpm --filter web test:unit nas seleções CI-04; Playwright nos dois arquivos contratados | Rota atual79Passed13.64s após Base64 UTF-8, incluindo corpo multilinha, aspas, acentos e emoji. Log shifu90-web-route-latest.log. Primeira tentativa77Passed/2timeouts de startup preservada em shifu90-web-route-base64-first.log; rerun sem mudança de código ou limiares passou. Routing36Passed retidos da seleção73Passed56.71s. Três consumidores existentes53Passed agregados no run71cenários, cujas2falhas do hook novo foram corrigidas. Histórico8Passed. Browser17:14Passed retidos, correções2Passed20.5s e1Passed9.9s; mobile atualizado1Passed4.3s. Nenhum full-run verde inferido. |
| EV-06 | CI-05 / Automated | Passed | Revisão 2, Node24.20.0/TS6, Python3.13.5 | pnpm --filter web check:types (raiz); uv run poe check:types (apps/server) | Ambos exit0; Server0errors/0warnings/0notes. Logs shifu90-{web,server}-types.log. Atualização final Web após Base64/testes:exit0 em63.50s, shifu90-web-types-latest.log. Build de produção atual confirmado pelo Builder runtime após remoção dos diagnósticos. Server inalterado permanece válido. |
| EV-07 | CI-06 / Automated | Passed | Revisão2, Node24.20.0/Python3.13.5 | pnpm --filter web check:lint; uv run poe check:lint e Ruff focado | Web673arquivos, zero erros,11avisos herdados Intelligence,5.38s no run final após Base64. Server1521arquivos formatados, exit0. Logs shifu90-web-lint-latest.log e shifu90-server-lint.log. |
| EV-08 | CI-07 / Automated | Passed | Revisão2 | Mesmos comandos de CI-06, resultados de complexidade separados | Ruff C901 sem violações; Biome sem violações dos checkers qualitativos configurados. Métrica quantitativa dedicada Not applicable conforme contrato. |
| EV-09 | CI-08 / Automated | Failed | Revisão2, base8ee992a7 e atual | pnpm check:test-integrity; architecture/build das duas aplicações | Arquiteturas e builds passaram. Build Web final10.04s, shifu90-web-build-latest.log; avisos herdados descoberta de rotas/bundle. Integridade falha nos mesmos14 caminhos preexistentes, comprovados reconstruindo nomes de git ls-tree base e executando o checker inalterado. Logs shifu90-baseline-integrity.log e shifu90-test-integrity.log. Nenhum teste removido ou checker relaxado. |

| EV-10 | VM-01 / Manual / CA-02/03/04/08/10/11/12/13 | Blocked | Revisão2, desktop1440×900; banco/Redis/API próprios; Jev HTTP determinístico; runtime final com Inngest isolado | Playwright CLI shifu90 em apps/web, login real, Atividade093, edição e arquivo adicional, GET/PATCH, comandos, preliminar, envio e novo login | GET200 e PATCH200 done:true reais. Terminal executou npm run dev:api e dev:web e mostrou Vite pronto. Preliminar100%, quatro arquivos somente leitura; contagens oficiais0. Envio criou tentativa01M5TK3CZMYSSTGE20XVRQW174, avaliação100.00 e um workflow oficial COMPLETED. Uma admissão agentos:learning published com attempts1 e um evento de avaliação. Nova sessão SQL confirmou bytes exatos de três arquivos editáveis e HTML fixo no snapshot. Logout/login e GET da URL da tentativa preservaram nota, rubrica e quatro arquivos somente leitura, sem prévia de prática. Logs shifu90-{preliminary,official}-db-proof-corrected.json e shifu90-api.log; snapshots shifu90-{http-patch-fixed,preliminary-expanded,official-reopened}.yml. Prévia e React→API não comprovados: ACH-09. Edição não repetir HTTP tem prova automatizada; não inferir uma contagem de requisições manuais não instrumentada. |
| EV-11 | VM-02 / Manual / CA-06/07/13 | Passed | Revisão2, mobile390×844, Atividade094 no primeiro banco descartável | Login/logout por formulário/menu reais; reabrir mesma revisão; copiar conteúdo pelo editor; gravar em segunda aba e confirmar na primeira | Frontend959 e API556 caracteres restaurados exatamente como gravados. Marcador distinto da aba2 chegou à aba1. Editor, HTTP e Terminal acessíveis. scrollWidth390=innerWidth390. snapshots/shifu90-mobile-restored.yml. Prova comportamental retida: mudanças posteriores corrigem transporte HTTP, fixture de execução e altura CSS, sem alterar identidade/chaves/restauração/sincronização. Capturas antigas substituídas por V-04. |
| EV-12 | VM-03 / Visual / CA-02/08/13 | Blocked | Revisão2, desktop1440×900, candidato final | Comparação das capturas abaixo com handoff e referências salvas; revisão independente | V-03/V-06/V-07 Passed. V-01/V-02 Blocked: erro de serviço do fornecedor ocupa a prévia. Nenhum outro desvio material observado. |
| EV-13 | VM-04 / Visual / CA-08/12/13 | Passed | Revisão2, desktop1440×900 e mobile390×844, candidato final | Comparação de V-04/V-05a/b/c/d com adaptação/composição do handoff; revisão independente | Editor mobile400px, foco nítido em HTTP e ausência de overflow da página. Preliminar e oficial legíveis, arquivos sem affordance de edição. Código possui rolagem própria; demais arquivos seguem abaixo da dobra. Comentário inglês vem da fixture controlada, não comprova tradução de todo dado externo. |
| EV-14 | Revisão independente / Review | Blocked | Revisão2, diff integrado atual | Implementation Reviewer e Visual Reviewer em paralelo; nenhum teste verde repetido | Servidor, contratos entre camadas, snapshots e REST examples sem novo defeito bloqueante. Bindings do hook corrigidos. ACH-04/09 continuam abertos. Rechecagem focal concluída: ambos achados high de prova desatualizada encerrados. Sem novo defeito; apenas ACH-04/09 permanecem bloqueantes. |

| EV-15 | Reconciliação / Review | Passed | Revisão3, resposta anotada do usuário | Q5=A e Q6 na mesma worktree; Spec Reviewer focal | Emenda de origem própria HTTPS validada, allow-same-origin e manutenção preservadora autorizadas. Rules e checker reconciliados; reviewer PASS após correções documentais. Metadados Learningv26 e Curriculumv13 reconfirmados via MCP, versões inalteradas. |
| EV-16 | CI-09 / Automated | Pending | Revisão3, mesma worktree | Seleções de manutenção conforme CI-09 | Builders migrando cenários. Checker isolado:4limites autorizados aceitos e6limites vizinhos/provider/service recusados,10asserçõesPassed em shifu90-integrity-contract-boundaries.log. Não substitui execução dos testes reais. |

| EV-17 | Revisão3 / CI-03/04/05/06 / Automated | Passed | Revisão3, Node24.20.0 | Dois arquivos afetados ReactFastifyQuestion e route; tipos configurados Web; Biome4caminhos | 94Passed93.94s, incluindo execução da configuração CORS gerada: origem confirmada, ausente, null, Shifu e outro WebContainer; preflight e remoção de credenciais/cookies. Tipos e Biome passaram. Logs shifu90-rev3-{component-route,web-types,scoped-biome}.log. Nenhum browser inferido desses testes. |
| EV-18 | Revisão3 / VM-01 / Manual | Pending | Revisão3, runtime3 isolado | Playwright CLI shifu90, Atividade093 | Prévia real renderizou. Edição de frontend/API mostrou títulos distintos e arquivo adicional. React concluiu tarefa; painelGET200 confirmou done:true; PATCH200 alterou done:false. Contador no projeto tinha3PATCH e permaneceu3 após nova edição do frontend. Origem HTTPS validada, parent.document recusado com SecurityError, serviceWorker disponível. logs/shifu90-rev3-preview-proof.log e snapshots/shifu90-rev3-practice-complete.yml. Trecho de avaliação oficial e novo login concluído em EV-20. Esta linha preserva o checkpoint da prática. |
| EV-19 | CI-08 / Automated / integridade reconciliada | Passed | Revisão3 | pnpm check:test-integrity | 389arquivos verificados; zero violações. shifu90-test-integrity-reconciled.log. Aceitação do checker não substitui execução das afirmações migradas; os resultados atuais estão em EV-22–28. |


| EV-20 | Revisão 3 / VM-01 / Manual / CA-02/03/04/08/10/11/12/13 | Passed | Runtime3 descartável, desktop 1440×900; API17790, inferência18790 controlada, AgentOS Learning real | Playwright CLI shifu90 em apps/web: formulário real, edição, React→API, GET/PATCH, terminal, preliminar, envio oficial, logout/login e GET da URL da tentativa | Prévia HTTPS distinta permite service worker e recusa parent.document com SecurityError. PATCH contou 3 e permaneceu 3 após editar frontend. Preliminar 100%, quatro arquivos somente leitura e zero tentativas/avaliações/admissões oficiais. Envio gerou tentativa 01M5TNJESDMKE1P2977A2C5W0F, nota100.00, uma avaliação e admissão agentos:learning published com attempts1. Workflow nativo COMPLETED. Nova transação confirmou bytes exatos dos três arquivos editáveis e HTML fixo no snapshot. Novo login preservou nota, rubrica e quatro arquivos sem iframe de prática. Logs shifu90-rev3-{preview-proof.log,preliminary-proof.log,preliminary-db.json,official-db.json,reopened-proof.log}. Inferência determinística não prova qualidade remota; consumidor XP indisponível no endpoint isolado18791. |
| EV-21 | Revisão 3 / VM-03/04 / Visual | Passed | Mesmo candidato integrado, 1440×900 e 390×844 | Comparação independente de todas as dez linhas V com referências e handoff; inventário abaixo | 10/10 Passed. V-01/02 têm prévia real; HTTP, terminal e editor mobile aprovados. Preliminar e oficial recapturados. Primeiras capturas oficiais durante animação foram rejeitadas e substituídas após texto visível100, não apenas aria-label. V-03 anterior retido pois rubrica e componentes não mudaram. |
| EV-22 | CI-09 / Automated / unidades e contratos defensivos | Passed | Revisão 3, Python3.13 e Node24, mesma worktree | uv run pytest nos consumidores Planning/domínio; Vitest no arquivo REST/security; pytest nos guardas internos do handler | Seleção Planning156Passed84.02s; enum movido depois e consumidor6Passed6.18s. BFF3Passed e guardas internos6Passed. Logs shifu90-planning-migration-unit-final.log, shifu90-planning-enum-consumer-unit.log e logs focados de telemetria. Inventário de preservação abaixo. Guardas defensivos não são alegação de HTTP, qualidade NLP ou execução registrada. |
| EV-23 | CI-09 / Automated / HTTP e PostgreSQL | Passed | Revisão 3, app real, PostgreSQL/Redis descartáveis e NLP local | REDIS_URL=redis://127.0.0.1:1/0 uv run pytest, apps/server; doze seleções da seção de reprodução abaixo | Run inicial91Passed2Failed380.67s. Correção de expectativa curriculum_gap e autenticação BFF do sweep curricular: duas seleções exatas2Passed22.40s. São93cenários atuais comprovados por91+2, sem inferir run completo verde. Sem skips. Logs shifu90-ci09-server-integrated.log e shifu90-ci09-seed-http-correction.log. |
| EV-24 | CI-09 / Automated / REST no navegador | Passed | Revisão 3, BetterAuth/API reais, respostas Gamification controladas no upstream18792, Web17090, Node24 | pnpm test:integration --config=.playwright-cli/logs/shifu90-routed-rest.config.ts tests/gamification/gamification-layout.test.ts tests/learning/choice-result-page.test.ts --grep 'routed REST transport' --workers=1, apps/web | Primeiros10Failed por validação equivocada do ID da fixture no controle de testes. Corrigida essa validação;10Passed1.2m. Verifica cinco leituras por consumidores reais, sucesso/503, método, caminho, query, Bearer/BFF e ausência de Cookie. Sem interceptar _serverFn. Não prova concessão real de XP. Logs shifu90-ci09-routed-rest{,-correction}.log. |
| EV-25 | CI-09 / Automated / seletores permanentes | Passed | Revisão 3, arquivos reais de Poe e Server CI | Executar os find definidos nos seletores e comparar conjuntos; shifu90-ci09-selection-parity.log | Unidade112 arquivos; integração47 arquivos, conjunto Poe/CI idêntico. Inclui conformidade core/domain, shared/rest/handlers e dois limites Planning exatos. Nenhuma dependência/lockfile/proteção de branch alterada. Web CI já define a porta do upstream para os dez cenários novos. |
| EV-26 | Gates finais Web / Automated | Passed | Revisão 3, Node24.20.0, configuração de projeto | pnpm check:types, check:lint, check:architecture e build, apps/web | Todos exit0. Logs shifu90-rev3-web-{types,lint,architecture,build}-final.log. Lint673arquivos com11avisos herdados Intelligence. Build com avisos herdados de descoberta de rotas e chunks. Complexidade qualitativa configurada Passed; quantitativa dedicada Not applicable conforme CI-07. |

| EV-27 | Gates finais Server / Automated | Passed | Revisão3, Python3.13.5, configuração completa do projeto | uv run poe check:types, check:lint, check:architecture e build, apps/server | Todos exit0. Tipos0errors/0warnings/0notes. Ruff sem violações e1518arquivos formatados. Tach todos os módulos validados. Sdist e wheel construídos. Logs shifu90-rev3-server-{types,lint,architecture,build}-final.log. C901 configurado Passed; quantitativa dedicada Not applicable. Edições posteriores restritas aos testes reabrem somente seus estáticos focados. |


| EV-28 | CI-09 / Automated / jobs registrados | Passed | Revisão3, Inngest/PostgreSQL/Redis/Mailpit descartáveis, API17791 | Comando completo da seção Reprodução; dois arquivos, cinco cenários, SHIFU_RUN_REAL_INNGEST_TESTS=1 | 5Passed123.48s, zero skips. shifu90-ci09-real-jobs-final.log. Identity comprova publicação/execução registrada, sanitização e coletor indisponível. Communication comprova entrega única por evento duplicado e falha RuntimeError antes do step, repetição no mesmo run/event e recuperação com exatamente uma conclusão. Tentativa inicial/retry1, novo callback iniciado>=2, conclusão positiva por etapa. MiddlewareSync público evita incompatibilidade com send_sync. Não prova telemetria de BaseException interna do SDK. Tipos/Ruff/format dos dois últimos arquivos Passed; gates gerais anteriores retidos por ausência de mudança em produção. Sessão40649 exit0, recursos próprios limpos. |

| EV-29 | Revisão independente / Review | Passed | Revisão3, branch codex/shifu-90-spec, base8ee992a7 e diff integrado final | Implementation Reviewer e Visual Reviewer paralelos no candidato integrado, seguidos somente por rechecagens afetadas | Implementation Reviewer PASS final para CA-01–13 e CI-09, sem findings. Conferidos contratos, produção, afirmações preservadas, autenticação/persistência/eventos, CORS/credenciais, REST examples e atualidade de EV-02–28. Visual10/10PASS conforme EV-21. Orchestrator reconciliou inventário completo e diffs. Nenhum teste verde repetido para concluir. |

| EV-30 | Conclusão local / Review | Passed | Revisão3, mesmo diff integrado, 2026-10-25 | Skill conclude-spec; reconciliar sete seções, Progress, inventário, ACH e Delivery; git diff --check e integridade final | Todos os13critérios Complete/Passed, CI-01–09 e VM-01–04 atuais;21achados encerrados. Revisões independentes PASS. Integridade final389Passed e sintaxe do checker válida. Trabalho somente local, sem staging/commit/fetch/merge/publicação ou escrita Atlassian. Portas e sessões próprias encerradas; mudanças alheias preservadas. Spec e Evaluation completed. |

| EV-31 | Sincronização para publicação / Review | Passed | Revisão3, origin/main=8ee992a750bd526aafcf1b5db396677a3ebdc3c1 | gh auth status; gh repo view CtrI-Alt-Del/shifu; git fetch origin main; git merge --no-edit origin/main; pesquisa de PR por head/Jira | Remote/base verificados, Already up to date. Nenhum diff introduzido pela sincronização. Evidências EV-02–30 reutilizadas por contrato/código/fixtures/dependências/configuração inalterados. Metadados canônicos confirmam Learningv26 e Curriculumv13. CI remoto será verificado no SHA publicado, sem repetir suites locais verdes. |


| EV-32 | CI remoto head inicial / Automated | Failed | PR45, head2d2729f73d010c3edea77cc71c4c387d662f5956 | GitHub workflows Server/Web/Email; runs na tabela Delivery | Email completo Passed. Tipos/lint/arquitetura/build Server e Web Passed. Server unit1764Passed103.10s. Web158arquivos/1418testes Passed94.55s com4erros de scheduler após teardown, encerrando job com falha. Server real AI evals:9workflows Passed; retrieval2Passed1Failed. Integrações ainda executando no checkpoint. Não substitui Failed por aprovação dos testes individuais. |
| EV-33 | Correção ACH-22 / Automated + Review | Passed | Arquivo use-proposal-skill-graph.test.ts, mesma worktree | Node24.20.0, pnpm test:unit <arquivo>; pnpm check:types em apps/web; Biome focado; Implementation Reviewer | Quatro testes Passed1.92s e zero erros assíncronos. Apenas referências de arrays de teste estabilizadas e três asserções adicionais de uma chamada ao layout. Nenhuma produção/configuração alterada. Revisão focal PASS; visual anterior retido pois UI inalterada. CI remoto do novo head será acompanhado. |
| EV-34 | Diagnóstico ACH-23 / Review | Passed | Head2d2729f7 e comparação independente SHIFU-86/head1830515d | gh api para logs/artefatos12621008048 e12615424634; comparação de fontes e contrato Planner CA-13 | Ambos os relatórios têm Recall0.8974, MRR0.8013 e separação0.83887<0.8671. Baseline comprovado e não transitório. Teste deliberadamente cobre todo build_development_seed; hipótese de pressão pelas58skills adicionadas na base não foi provada por execução contrafactual. Não há correção honesta apenas de teste estabelecida. Métrica continua Failed; decisão de ampliar escopo solicitada, sem reduzir limiares/catálogo. |


| EV-35 | Segunda sincronização / Review | Passed | Merge em andamento: ours efa34742, origin/main0f1ee09a | git fetch origin main; git merge --no-edit origin/main; três Builders com caminhos disjuntos e integração do Orchestrator | Vinte conflitos conciliados. Planning: todos os métodos e asserções AST de ambos os lados preservados;186unitPassed10.61s e tipos/RuffPassed. Web: animações90frames de main, casos integrados e transporteXP preservados; tipos configurados/BiomePassed. Telemetria mantém11Goal,3Identity,3Communication,13Handler e7Health. Manifesto/CI contêm união de limites autorizados, sem handler duplicado. Integridade406arquivosPassed. Provas afetadas foram reabertas e atualizadas em EV-36–42. |

| EV-36 | Pós-merge / CI-01/02/09 / Automated | Passed | Merge5837ab8d, main0f1ee09a, Python3.13.5 | apps/server: REDIS_URL=redis://127.0.0.1:1/0 uv run pytest nas15seleções HTTP listadas abaixo e no log | HTTP186Passed513.62s, zero skips, shifu90-merged-http.log. Planning186unitPassed10.61s e Submit100Passed15.63s, logs shifu90-main-merge-planning-unit-correction.log e shifu90-merged-submit-unit.log. Asserções dos dois lados preservadas. |
| EV-37 | Pós-merge / CI-05/06/07/08 / Automated | Passed | Merge5837ab8d e correção focal de teste | apps/server: uv run poe check:types/check:lint/check:architecture/build; apps/web: pnpm check:types/check:lint/check:architecture/build; raiz: pnpm check:test-integrity | Todos exit0. Server tipos0/0/0,1536arquivos formatados, módulos válidos, wheel/sdist. Web tipos e build aprovados, avisos herdados. Complexidade qualitativa configurada Passed, quantitativa Not applicable. Integridade406arquivosPassed. Logs shifu90-merged-{server,web}-{types,lint,architecture,build}.log; tipos Web em shifu90-main-merge-learning-browser-types.log. |
| EV-38 | Pós-merge / retrieval real / Automated | Passed | Main0f1ee09a incorpora mínimo0.89 autorizado pelo usuário | apps/server: SHIFU_RUN_REAL_AI_EVALS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 REDIS_URL=redis://127.0.0.1:1/0 uv run python -m evals.run --workflow retrieve-planning-skills --output-dir ../web/.playwright-cli/logs/shifu90-merged-retrieval-real | 3Passed. Catálogo completo65skills, Recall0.8974>=0.89, MRR0.8013>=0.80, separação0.83887<0.8671. Nenhuma melhora de ranking alegada. Run anterior sem flag real teve3Passed com double e não foi usado como prova real. shifu90-merged-retrieval-real.log e relatório. |
| EV-39 | Pós-merge / CI-09 jobs reais / Automated | Passed | Inngest/PG/Redis/Mailpit descartáveis, API17791 | apps/server: mesmo comando de dois arquivos EV-28, seguido pelo cenário focal test_invalid_registered_event_reports_failure_without_runtime_retry_or_delivery | Primeiro run5Passed1Failed170.98s por consulta GraphQL antes da indexação. Espera por job.started corrigiu a consulta. Run focal intermediário falhou32.37s ao confundir marcador retrying com execução repetida. Prova final1Passed25.02s, shifu90-merged-job-terminal-correction.log, retém outros5Passed. FAILED terminal real, uma execução, todos eventos tentativa1, zero entrega e IDs iguais. Wrapper emite started/failed/retrying para NonRetriableError sem retry real. Tipos/Ruff/formatPassed. Nenhum full-run6verde inferido. |
| EV-40 | Pós-merge / VM-01 / Manual | Passed | Banco/API17790, inferência18790 controlada, Web17090 próprios; login visível real após mudanças Auth de main | Playwright CLI shifu90-merge: prática093, teclado Space em escolhas, edição frontend/API/adicional, React→PATCH, GET/PATCH200, Vite, preliminar, envio, logout/login e reabrir resultado | Origem HTTPS validada distinta, sandbox allow-scripts allow-same-origin e acesso DOM bloqueado. Frontend atualizado e GET /api/stats manteve patches2. Primeiro script leu rota resetada /api/tasks e gerou falso alerta, corrigido explicitando /api/stats. Preliminar100 com0tentativas oficiais. Oficial01M5TZ567NS4FXDD7EDR9ND0DA:1tentativa/1avaliação100, efeito aplicado e admissão agentos:learning published1. Comparação SQL confirma bytes exatos dos3editáveis e HTML fixo no snapshot. Novo login reabre100/4arquivos somente leitura/iframe0. Logs shifu90-merged-{runtime-proof-corrected,preliminary-proof,official-proof,result-proof-final}.log, preliminary-db.json, official-db.json e byte-comparison.json. Transientes GET500/JSONparse durante reinício da API recuperados com200; fornecedor emite avisos de preload/disposal. VM-02 retido: chaves e sincronização inalteradas, autenticação nova provada aqui. |
| EV-41 | Pós-merge / VM-03/04 / Visual | Passed | Merge5837ab8d, dez capturas exigidas de EV-21 | Visual Reviewer comparou impactos de main e referências existentes | Retidos10/10. Widget/resultados/layout/tokens/fontes inalterados. Mudança Input é foco, capturas relevantes sem foco; foco V04 está em HTTP inalterado. Menu de conta fechado nas capturas. Nova autenticação coberta em EV-40. Nenhuma captura adicional exigida. |

| EV-42 | Pós-merge / CI-04/09 / Automated browser | Passed | Merge5837ab8d, API/PG/Redis próprios, Node24.20.0 e configuração original importada | apps/web: pnpm test:integration --config=.playwright-cli/logs/shifu90-routed-rest.config.ts tests/learning/activity-page.test.ts tests/learning/choice-result-page.test.ts tests/gamification/gamification-layout.test.ts --workers=1 | 32Passed1.6min, zero failed/skips. Log shifu90-merged-browser.log. API17790 reutilizada apenas por ser do próprio trabalho; Playwright geriu Web17090, upstreams18792/18793. Inclui asserções Motion90frames de main, casos integrados e10cenários de transporte HTTP real. Ambiente privado carregado, CI=true. Não substitui CI remoto. |

| EV-43 | Revisão independente pós-merge / Review | Passed | Merge5837ab8d com correção final Communication, Spec revisão3 | Implementation Reviewer focal e Visual Reviewer em paralelo, sem terceiro reviewer ou repetição de testes | PASS sem achados. Confirma regras/seletores/asserções preservados, Identity/Auth/migration iguais ao main recebido, Recall autorizado, integração186HTTP/32browser/jobs5+1, prova manual e gates atuais. Visual10/10retido em EV-41. Orchestrator aceita ambas revisões. |

| EV-44 | CI remoto pós-merge / Automated | Failed | Head4bea0918, Server40257456886/job121362262846/artifact12623152704 | gh api autenticado: logs e relatório process-mentor-response | Retrieval real3Passed no CI. Outra falha: general_answer_says_the_context_was_not_checked, scorer_rejected,8/9Mentor. Nenhuma mudança em Mentor/eval/scorer/projeção/lock contra main ou head2d2729f. Caso idêntico passou no artefato real anterior1.876s, agora falhou2.910s. Modelo remoto sem seed/temperature fixados; resposta não está no relatório por privacidade, portanto sinônimo recusado versus falha semântica ainda não distinguíveis. Uma repetição diagnóstica somente do job no mesmo SHA, sem alterar scorer, autorizada por variação concreta entre runs. Falha original preservada, não considerada Passed. |

| EV-45 | Repetição diagnóstica de EV-44 / Automated | Passed | Mesmo head4bea0918, Server40257456886 tentativa2/job121364719994 | gh api POST actions/jobs/121362262846/rerun após conclusão do workflow | Job real AI evals Passed sem alterar código, prompt, scorer, modelo, limiares ou conjunto. Fonte idêntica já tinha caso Passed anterior; rejeição isolada da primeira execução preservada em EV-44. Log shifu90-merged-ci-evals-retry.log. Uma única repetição efetivamente iniciada. ACH-26 Resolved como variação observada da inferência remota, sem afirmar a formulação exata da resposta não registrada. |
| EV-46 | Conclusão publicada / Review | Passed | PR45/head4bea09183d90f6f750aaa9354735bf0be7559463, revisão3 | gh api por SHA, workflows e reviewThreads; reconciliar sete seções | Todos23checks aplicáveis Passed, zero pending/failure/cancelled. Server40257456886, Web40257456644, Email40257456602. ReviewThreads vazio, reviewDecision vazio, zero threads resolvidas. Falhas anteriores preservadas. Final factual em Spec/Evaluation não altera código/provas e acompanha commit documental com nova conferência de CI. |

## Inventário Manual e Visual

Rotas usam o caminho publicado em logs/shifu90-scenario.json. A Atividade final é 093; o resultado atual é a tentativa 01M5TNJESDMKE1P2977A2C5W0F. A tentativa terminada em 174 pertence à prova histórica da revisão 2. Todos os caminhos abaixo de screenshots/ e snapshots/ são relativos a apps/web/.playwright-cli/. Capturas atuais pertencem ao candidato após a correção da altura mobile e remoção de diagnósticos. Nenhum screenshot foi adicionado ao Git.

| ID / VM / CA | Surface / route | State / viewport | Reference | Candidate / artifact | Observed result / review disposition |
| --- | --- | --- | --- | --- | --- |
| M-01 / VM-01 / CA-02/03/04/08/10/11/12/13 | Atividade093 e tentativa5W0F | Prática, HTTP, terminal, preliminar e envio /1440×900 | Spec VM-01 | EV-18/20 | Passed. Prévia, React→API, HTTP, terminal, preliminar, envio, persistência exata e novo login reais. |
| M-02 / VM-02 / CA-06/07/13 | Atividade094 | Retomada e duas abas /390×844 | Spec VM-02 | EV-11; snapshots/shifu90-mobile-restored.yml | Manual Passed. |
| V-01 / VM-03 / CA-02/08/13 | Atividade093 | Arquivos/API/adicional e prévia /1440×900 | design/references/pcDeY.png | screenshots/shifu90-rev3-desktop-files-preview.png | Passed pelo Visual Reviewer. Prévia real, explorador/API/adicional visíveis; captura opaca anterior preservada como falha histórica. |
| V-02 / VM-03 / CA-02/08/13 | Atividade093 | Enunciado, rubrica e prévia /1440×900 | design/references/tDF6r.png | screenshots/shifu90-rev3-desktop-statement-preview.png | Passed pelo Visual Reviewer. Enunciado, rubrica e prévia real visíveis. |
| V-03 / VM-03 / CA-08/13 | Rubrica pública | Como será avaliado /recorte desktop | design/references/xeppf.png | screenshots/shifu90-desktop-public-rubric.png | Passed. Hierarquia, jade, explicação e peso legíveis. Correção100% é conteúdo curricular permitido. |
| V-06 / VM-03 / CA-02/08/13 | Atividade093 | Resposta HTTP /1440×900 | Composição handoff V-01/V-02 | screenshots/shifu90-rev3-desktop-http.png | Passed pelo Visual Reviewer na captura atual. Método, rota, corpo, status200 e JSONdone:true visíveis. |
| V-07 / VM-03 / CA-02/08/13 | Atividade093 | Terminal /1440×900 | Composição handoff V-01/V-02 | screenshots/shifu90-rev3-desktop-terminal.png | Passed pelo Visual Reviewer na captura atual. Saída monoespaçada, comandos permitidos, campo rotulado e envio legíveis. |
| V-04 / VM-04 / CA-06/07/13 | Atividade093 | Editor, abas e foco /390×844 | Adaptação mobile handoff | screenshots/shifu90-rev3-mobile-{editor-preview,panels}.png | Passed pelo Visual Reviewer na captura atual. Altura útil do editor, abas alcançáveis e foco nítido em HTTP. Sem correspondência exata com frame mobile inexistente. |
| V-05a / VM-04 / CA-08/12/13 | Preliminar093 | Arquivos somente leitura /1440×900 | Handoff V-05 | screenshots/shifu90-rev3-preliminary-desktop.png | Passed. Pontuação, critério e arquivos legíveis sem aparência de edição. |
| V-05b / VM-04 / CA-08/12/13 | Preliminar093 | Arquivos somente leitura /390×844 | Handoff V-05 | screenshots/shifu90-rev3-preliminary-mobile.png | Passed. Conteúdo adaptado; quatro arquivos confirmados no DOM, continuação por rolagem. |
| V-05c / VM-04 / CA-08/12/13 | Tentativa5W0F | Resultado oficial /1440×900 | Handoff V-05 | screenshots/shifu90-rev3-official-desktop.png | Passed. Detalhe integrado e indicação Somente leitura inequívocos. |
| V-05d / VM-04 / CA-08/12/13 | Tentativa5W0F | Resultado oficial /390×844 | Handoff V-05 | screenshots/shifu90-rev3-official-mobile.png | Passed. Hierarquia preservada; código tem rolagem própria. |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Inspeção do runner encontrou rejeição indevida do index.html curricular fixo. | high | CI-03/04, VM-01 | Resolved. Arquivo fixo aceito; instalação e Vite prontos no runtime real de EV-10. |
| ACH-02 | Import inicial pytest exige REDIS_URL antes do override; limpeza de rate limit não declarava dependência do Redis descartável. | medium | CI-01/02 | Resolved. Dependência explícita do Redis descartável; EV-02/03 posteriores aprovados. |
| ACH-03 | Inspeção encontrou import ausente do snapshot integrado no provider curricular. | high | CI-01/02 | Resolved. Import corrigido; tipos e EV-02/03 aprovados. |

| ACH-04 | CI-08 falha por14 testes herdados fora dos limites. Reprodução na base confirma mesmo conjunto. | blocking | CI-08/09 | Resolved. Q6 executada na mesma worktree. Autoridades reconciliadas; cenários preservados em consumidores reais/conformidade estreita; checker389Passed. Unidades,93HTTP/PG,10REST browser e5jobs reais aprovados em EV-22–28. Nenhuma dispensa de afirmação. |
| ACH-05 | check:lint Web referenciava apps/web/scripts inexistente inclusive na base. | medium | CI-06 | Resolved. Removido somente argumento de caminho inexistente em package.json. Mesmo lint dos arquivos reais, exit0 com11avisos herdados. |
| ACH-06 | Vite8.3 da fixture falhou no WebContainer por binding Rolldown/WASM e peers incompatíveis, API ficou pronta. | high | VM-01/03 | Resolved quanto à inicialização. Fixture compatível Vite6.3.5 exato. Aplicação Shifu mantém seu lock Vite8.3. Somente dois registros curriculares no banco descartável atualizados. Capturas anteriores não provam sucesso. |
| ACH-07 | Primeira seleção HTTP:51pass1fail por teste novo esperar kind inexistente na resposta preliminar atual. | medium | CI-02 | Corrigido teste para status/score existentes e question_kind no assessor. Primeira correção10falhas por expectativas inválidas400/404 e75/75.00, corrigidas e10Passed34.85s, sem mudança de produto. |
| ACH-08 | Browser17cenários:14pass3fail. Dois testes legados esperam seletor/animações antigos; novo mobile fica sem autoridadeonline. | high | CI-04 | Resolved. Fixture inclui accountId e teste de animação segue Motion/transitions reais; reload passa pela navegação client permitida. Reexecuções2Passed20.5s e1Passed9.9s.14anteriores preservados. Tipos/lint/build Web finais passaram após runtime corrigido. |

| ACH-09 | Prévia em sandbox allow-scripts tem origin null; navegador lança SecurityError ao acessar serviceWorker por ausência de allow-same-origin. Repetido após habilitar particionamento de storage no browser de teste. | blocking | VM-01/03, CA-03/04/13 | Resolved quanto ao conflito. Q5=A autorizou origem própria validada na revisão3, auditada pelo SpecReviewer. Testes94Passed e prévia/React→API reais comprovados. Revisão visual focal 10/10 Passed em EV-21. |
| ACH-10 | Espera ilimitada por exit do servidor antigo travava edição. | high | CI-03/04, VM-01 | Resolved no adapter: Vite HMR/Node watch, readiness limitada, encerramento limitado e descarte. Rota78Passed atual. |
| ACH-11 | Monaco mobile ficava com uma linha por altura indefinida. | high | VM-04, CA-13 | Resolved. Altura mobile local corrigida; componente10Passed, browser1Passed, recaptura atual e revisão V-04 Passed. Capturas antigas Stale preservadas como histórico. |
| ACH-12 | Corpo JSON com aspas causava SyntaxError antes do HTTP no argumento do subprocesso WebContainer. | high | CI-04, VM-01/03, CA-04 | Resolved. Base64 UTF-8 no argumento, decodificação no processo sem shell. PATCH real200done:true após remoção dos diagnósticos. Rota79Passed inclui aspas, acentos, emoji e quebra de linha. |
| ACH-13 | Inserção automatizada no Monaco produziu fechamento extra de código. | medium | VM-01 | Corrigido usando colagem por clipboard e cópia de confirmação. Não atribuído ao produto. |
| ACH-14 | Ambiente manual inicial herdava endpoint Inngest compartilhado. | medium | VM-01 | Corrigido antes de qualquer envio oficial: novo runtime privado com endpoint18791 deliberadamente indisponível. Login anterior pode ter emitido evento automático de página. Nenhum evento enviado manualmente. Não se afirma execução de consumidor Gamification. |

| ACH-15 | Widget consumia objeto inteiro do hook e intercalava valores e handlers, contrariando UI Rules. | medium | CI-03/05/06 | Resolved. Bindings nomeados e valores antes dos handlers. Componente10Passed3.48s; tipos/lint e revisão focal aprovados. |
| ACH-16 | Inspeções SQL iniciais esperavam zero runs nativos após preliminar e HTML fixo dentro dos arquivos editáveis enviados. | low | EV-10 | Corrigidas as consultas, sem mudança de produto. Preliminar executa seu workflow nativo; HTML fixo pertence ao snapshot. Artefatos corrected registram as asserções válidas. |


| ACH-17 | Sweep HTTP de todas as skills atingiu o rate limit público; graph-only esperava código genérico conflict em vez do contrato curriculum_gap. | medium | CI-09 | Resolved. Cliente de integração usa o mesmo segredo BFF configurado, preservando autenticação e cada chamada/persistência; expectativa segue o erro real. Nenhuma configuração de rate limit alterada. Duas seleções2Passed22.40s, EV-23. |
| ACH-18 | Dez cenários REST no navegador falharam porque o controle upstream rejeitava ID alfanumérico da própria fixture. | medium | CI-09 | Resolved. Correção somente no controle de teste; valida26caracteres maiúsculos/numéricos sem fingir ULID. Dez cenários10Passed1.2m, EV-24. |
| ACH-19 | Migração do wrapper isolado para Inngest real expôs múltiplos job.started por replay durável e ResponseInterrupt de BaseException dentro de step. | high | CI-09 | Resolved. Identity3Passed após permitir replay com mesma correlação e exatamente uma conclusão. Falha RuntimeError determinística passou a usar middleware público antes do step, sem capturar BaseException nem trocar execução/repositório. Run71631:3Passed2Failed195.24s. Communication: entrega inicial do outbox falhou no setup; recuperação observada, mas completionattempt1 invalidou expectativa herdada de contador global. Diagnóstico confirmado: middleware assíncrono de teste rejeitado por send_sync do SDK, antes da publicação. Corrigido para MiddlewareSync público. Rechecagem final5Passed123.48s em40649, sem skips, pois a fixture é compartilhada com Identity. EV-28 encerra o achado. Tipos focados0errors e Ruff/format Passed em shifu90-telemetry-communication-correction-types.log. Limite: falhas internas de step não são alegadas como prova de telemetria de Exception do wrapper. |
| ACH-20 | Capturas oficiais iniciais mostravam contador em95.18/99.98 enquanto aria-label já indicava100. | low | VM-04 | Resolved. Espera pelo texto efetivamente visível100 e novas capturas desktop/mobile. Ambas inspecionadas e aprovadas, EV-21. |
| ACH-21 | Seletores permanentes Poe/Server CI não executavam os novos limites de conformidade e integração. | high | CI-09 | Resolved. Seletores e Tooling reconciliados;112arquivos unitários e47de integração, conjuntos CI/Poe idênticos. Revisão independente aprovada, EV-25. |


| ACH-22 | PR45 Web unit:158arquivos/1418testes Passed, porém quatro ReferenceError window is not defined no scheduler React após o arquivo use-proposal-skill-graph.test.ts. | high | CI remoto Web unit | Resolved localmente. Três renderHook usavam arrays literais instáveis e realimentavam o layout após updates. Dados estabilizados; asserções preservadas e três novas verificam uma chamada ELK. Quatro testes Passed1.92s, zero erros assíncronos. Tipos de projeto, Biome e diff-check Passed. Implementation Reviewer focal PASS. Web CI do head efa34742 passou; confirmação do head integrado será registrada na Delivery. Logs shifu90-ci-web-unit-head1.log, shifu90-planner-graph-correction.log e shifu90-planner-graph-types.log. |
| ACH-23 | PR45 Server real AI evals: hybrid_recall_at_10=0.8974 <0.90; MRR0.8013 aprovado e consultas sem cobertura separadas corretamente. | high | CI remoto Server real AI evals | Open. Fonte de retrieval/eval/dataset/modelo inalterada contra origin/main. Baseline determinístico comprovado: SHIFU-86, head1830515d, run40238478557, artefato12615424634, mesmas métricas/revisões/falha. Ranker/seed/eval/modelo/lockfile inalterados nesta entrega. O contrato Planner CA-13 exige catálogo completo e Recall>=0.90, MRR>=0.80; filtrar skills ou reduzir limiar enfraqueceria a prova. Decisão posterior do usuário: main foi atualizada com mínimo0.89. Alteração incorporada de main0f1ee09a, proveniente de PR46/commitba45dc9c. Ranking, queries, rótulos, modelo, catálogo completo e MRR0.80 permanecem. Resolved quanto ao critério, sem alegar melhora do ranking. Reexecução real3Passed em EV-38. ACH-23 Resolved. Não é retry cego do critério anterior. Artefato server-evals12621008048, log/relatório shifu90-ci-server-evals-head1 e shifu90-ci-retrieve-planning-skills-head1.json. |

| ACH-24 | União de main0f1ee09a com entrega produziu20conflitos de testes/seletores. | high | Integração pós-merge | Resolved. Intenções e asserções de ambos preservadas, revisão focal e EV-35–41. |
| ACH-25 | Consulta GraphQL precoce e expectativa incorreta sobre marcador retrying no cenário Communication incorporado. | medium | CI-09 jobs | Resolved. Espera pelo início observado e prova terminal do engine distinguem marcador de retry de nova execução. EV-39. Nenhuma produção alterada. |

| ACH-26 | CI Mentor general_answer_says_the_context_was_not_checked recusado pelo scorer, enquanto retrieval atualizado passou. | high | CI remoto real AI evals | Resolved. Repetição única do mesmo job no mesmo SHA Passed, EV-45. Nenhuma alteração de prompt/scorer/modelo ou limiar. Pedido antecipado403 não iniciou execução. Falha histórica preservada. |

ACH-01–26 encerrados. Resultados históricos preservados com sua resolução. ACH-22/23 foram abertos na execução remota posterior. As falhas históricas e suas correções permanecem neste registro; nenhuma foi convertida em aprovação sem prova posterior.

## Resultados intermediários preservados

Os itens abaixo são checkpoints históricos. Declarações de pendência neles foram superadas pelos resultados atuais de EV-02–29. Nenhum run completo verde é inferido a partir de correções focadas.

- uv sync --frozen passou. pnpm install --frozen-lockfile passou. Lockfiles preservados. Scripts esbuild ignorados pelo pnpm, sem falha observada até aqui.
- Builder UI: primeira seleção 69 passou e 2 falharam por expectativa legada de entrypoint. Corrigidas as expectativas. Nova seleção de hooks/painéis 29/29 passou em 11.41s. Resultado final de todos os consumidores ainda pendente.
- Primeiro pytest interrompido no import por REDIS_URL ausente. Não executou testes. Nova seleção configurada pendente.
- Primeiro types Web iniciado antes de instalação usou TS global 4.9 e falhou. Invocação inválida para o projeto. Types configurado posterior apontou 1 diagnóstico runner e 2 no serviço, em correção.
- Ruff focado das fixtures/suporte/controladores passou após correção de sintaxe durante edição e dict comprehensions. Não substitui gate integrado.
- Runtime descartável aplicou Alembic head e seed no banco próprio. Health API 17790 retornou 200. Ambos workers AgentOS iniciaram. Sem prova comportamental manual ainda.

- CI04 ampliado:77cenários do arquivo de rota passaram22.47s, cobrindo SDK/controlado e matrizes HTTP/isolamento/lifecycle; nenhuma prova de rede real inferida.
- CI02 primeira seleção:51Passed/1Failed225.51s. Segunda tentativa10Failed44.98s por asserções de status/serialização do teste novo. Terceira seleção exata10Passed34.85s. Resultado validado contra transporte existente400validation_error e score75; não houve mudança de produto. Mudanças de teste não alteraram Server.
- CI04 browser:14Passed/3Failed1.3m; correção em andamento, sem declarar seleção inteira aprovada.
- VM01: loginformreal passou, escolhas avançadas por teclado, integrada carrega, rascunho confirma, dois arquivos editados e adicional criado. Rede real de prática ainda pendente por ACH06.
- Ambiente Web reiniciado com CI=true para desativar devtools de desenvolvimento que recursavam logs de console. API/seed preservados. Sessão79043 substitui12811 encerrada. Logs shifu90-web-ci.log. Erros de conexão do reinício não atribuídos à funcionalidade.

- VM02 comprovada no runtime real. A primeira leitura imediata de DOM após selecionar API foi falsa por renderização assíncrona/viewport do Monaco. Espera pelo grupo correto e cópia por teclado confirmaram o conteúdo completo, inclusive última gravação entre abas. Não foi falha de restauração.
- Runtime corrigido invalidou os casos de lifecycle/SDK. Builder atualizou e executou o arquivo de rota:78Passed14.90s, incluindo dois updates com exit do servidor pendente, sem processos duplicados nem reenvio HTTP.
- Webfinal types/lint/build passaram. Lint mantém11avisos herdados. Server types/architecture/build/1521arquivosformatados permanecem válidos nas declarações não alteradas.

## Diagnóstico de baseline de ACH-04

A reprodução na base preserva o checker e usa somente os nomes de arquivos de git ls-tree. O mesmo conjunto de14 violações aparece antes da feature. O diagnóstico somente leitura identificou contratos que impedem uma migração mecânica segura: UseCaseTesting permite conformidade de domínio sem usecase proprietário, mas Core/checker proíbem o caminho; NLP offline/índices não têm fronteira permanente acordada; AI/Jobs divergem para prova de registry dedicada. Telemetria exige controllers/jobs reais, sem renomear testes de aplicação mínima ou mocks como se fossem prova HTTP.

Caminhos preexistentes:

- apps/server/tests/curriculum/core/domain/test_react_question.py
- apps/server/tests/curriculum/server/test_roadmap_skills_seed.py
- apps/server/tests/intelligence/adapters/test_planning_embeddings_repository.py
- apps/server/tests/intelligence/ai/test_planning_nlp_evaluation.py
- apps/server/tests/intelligence/ai/test_planning_registry_ports.py
- apps/server/tests/intelligence/core/domain/test_planning_domain.py
- apps/server/tests/intelligence/core/domain/test_planning_session_domain.py
- apps/server/tests/shared/server/controllers/test_business_event_telemetry.py
- apps/server/tests/shared/server/handlers/test_app_error_telemetry.py
- apps/server/tests/shared/server/lifecycle/test_app_lifecycle_telemetry.py
- apps/server/tests/shared/server/messaging/test_job_lifecycle_telemetry.py
- apps/server/tests/shared/server/middlewares/test_telemetry_middleware.py
- apps/web/src/rest/axios/tests/server-request-client.test.ts
- apps/web/src/rest/services/tests/gamification-service.test.ts

A manutenção também alcança Identity, Communication e Gamification por seus controllers/jobs consumidores. Nenhum desses cenários foi removido e nenhuma autoridade ou regra do checker foi relaxada para obter aprovação. Q6 autorizou essa manutenção na própria worktree. As exceções estreitas foram reconciliadas entre Rules, Spec, checker e seletores de CI antes da execução, sem liberar testes genéricos de providers/services.

## Preservação dos 14 limites herdados

Caminhos nesta tabela são relativos a apps/server, exceto os dois Web. Os arquivos legados removidos foram substituídos pelos consumidores abaixo. O inventário local detalhado é logs/shifu90-curriculum-planning-boundary-inventory.md. A revisão independente conferiu nomes, matrizes e asserções originais junto aos consumidores.

| Origem | Destino e afirmações preservadas |
| --- | --- |
| curriculum/core/domain/test_react_question.py | Mesmo arquivo: dez cenários e matrizes de caminho, limites, imutabilidade, rubrica e snapshot. Round-trip persistido agora por learning/server/controllers/test_get_choice_activity_controller.py, leitura em transação nova. Sem import direto do codec. |
| curriculum/server/test_roadmap_skills_seed.py | learning/server/controllers/test_start_skill_controller.py: ao menos50skills, todas iniciadas por HTTP com experiência persistida, IDs/nomes únicos, referências conhecidas e rejeição graph-only. |
| intelligence/adapters/test_planning_embeddings_repository.py | intelligence/preparation/test_prepare_planning_indexes.py: três cenários de ciclo de vida por preparação pública e PostgreSQL real; scores, ordem, elegibilidade, imutabilidade e ativação observados em repositório novo. |
| intelligence/ai/test_planning_nlp_evaluation.py | intelligence/preparation/test_prepare_planning_indexes.py e intelligence/capabilities/test_planning_capabilities.py: 23nomes e parâmetros retidos, CLI pública, modelos locais reais, recuperação/classificação públicas, métricas, limiares, privacidade e recuperação. Três guardas de configuração rotulados não alegam qualidade ou execução. |
| intelligence/ai/test_planning_registry_ports.py | intelligence/server/controllers/test_get_planning_session_controller.py: contrato defensivo público de catálogo opcional ausente, sem worker ou adapter privado, close aguardado. Não alega execução registrada. |
| intelligence/core/domain/test_planning_domain.py | Mesmo arquivo:37casos de construtor inválido; enum declarativo movido ao consumidor test_classify_planning_intent_use_case.py. |
| intelligence/core/domain/test_planning_session_domain.py | 17invariantes de construtor retidas; 23nomes/matrizes de sessão distribuídos entre Start/Answer/Restart/Retry/Complete/Report/Get públicos, preservando fences, horários, mensagens e ausência de writes/eventos rejeitados. |
| shared/server/controllers/test_business_event_telemetry.py | RemoveGoal, SignIn e RegisterAccount controllers reais: ações, privacidade e coleta defeituosa, junto aos casos existentes. |
| shared/server/handlers/test_app_error_telemetry.py | shared/rest/handlers/test_app_error_handler.py: somente seis guardas internos diretos explicitamente rotulados. Respostas do handler registrado são comprovadas pelos consumidores HTTP RemoveGoal, SignIn, RegisterAccount e MainPageEntered. |
| shared/server/lifecycle/test_app_lifecycle_telemetry.py | shared/server/controllers/test_check_health_controller.py: ciclo de vida real, versões e falha do coletor. |
| shared/server/messaging/test_job_lifecycle_telemetry.py | Jobs Identity/Communication registrados em Inngest descartável: início, conclusão, IDs, tentativas, privacidade, falha, repetição e recuperação. Resultado final5Passed em EV-28. |
| shared/server/middlewares/test_telemetry_middleware.py | RemoveGoal e MainPageEntered HTTP reais: correlação, rotas, status, privacidade e falhas do coletor. |
| Web rest/axios/tests/server-request-client.test.ts | rest/security/tests/server-request-origin-contract.test.ts para opções defensivas internas; consumidores Gamification/ChoiceResult reais no navegador para transporte. |
| Web rest/services/tests/gamification-service.test.ts | tests/gamification/gamification-layout.test.ts e tests/learning/choice-result-page.test.ts: cinco leituras, sucesso/503, parâmetros e cabeçalhos reais no BFF, sem mock de server function. |

## Reprodução das seleções de manutenção

EV-23 executou a seguinte seleção em apps/server. O Redis inválido inicial apenas satisfaz a configuração de importação. As fixtures substituem por seu Redis descartável.

```sh
REDIS_URL=redis://127.0.0.1:1/0 uv run pytest \
 tests/intelligence/preparation/test_prepare_planning_indexes.py \
 tests/intelligence/capabilities/test_planning_capabilities.py \
 tests/intelligence/server/controllers/test_get_planning_session_controller.py \
 tests/learning/server/controllers/test_start_skill_controller.py \
 tests/learning/server/controllers/test_search_skill_catalog_controller.py \
 tests/learning/server/controllers/test_get_choice_activity_controller.py::TestGetChoiceActivityController::test_returns_persisted_react_project_and_curricular_file_policy \
 tests/shared/server/controllers/test_check_health_controller.py \
 tests/learning/server/controllers/test_remove_goal_controller.py \
 tests/identity/server/controllers/test_sign_in_controller.py \
 tests/identity/server/controllers/test_register_account_controller.py \
 tests/identity/server/controllers/test_main_page_entered_controller.py \
 tests/shared/rest/handlers/test_app_error_handler.py
```

Correção focada, com o mesmo prefixo de ambiente e cwd:

```sh
uv run pytest \
 tests/learning/server/controllers/test_start_skill_controller.py::TestStartSkillController::test_should_start_every_seeded_roadmap_skill_through_http \
 tests/learning/server/controllers/test_start_skill_controller.py::TestStartSkillController::test_should_reject_graph_only_skill_without_learning_content
```

Jobs reais executados em apps/server após integração. O último run repete os dois arquivos porque a correção alterou a fixture compartilhada:

```sh
SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=17791 \
 REDIS_URL=redis://127.0.0.1:1/0 uv run pytest -rs \
 tests/messaging/inngest/jobs/identity/test_log_main_page_entered_job.py \
 tests/messaging/inngest/jobs/communication/test_deliver_communication_job.py
```

A porta7777 já estava ocupada por outro trabalho. Foi preservada. Os testes usam a porta17791 livre e seus próprios Inngest/PostgreSQL/Redis/Mailpit descartáveis. Um run anterior nessa porta teve2Passed3Failed167.69s por expectativas de replay e falha dentro de step; shifu90-ci09-real-jobs-private-port.log. A correção intermediária teve3Passed2Failed195.24s; shifu90-ci09-real-jobs-correction.log. O resultado final fica separado em shifu90-ci09-real-jobs-final.log.

EV-24 usou a configuração temporária ignorada que importa playwright.config.ts e fixa caminhos absolutos. API descartável já iniciada foi reutilizada; Playwright iniciou/encerrou apenas seus processos Web e upstream. CI=true desativou devtools. Variáveis adicionais: SHIFU_SERVER_APP_PORT=17790, SHIFU_MENTOR_STREAM_TEST_PROXY_PORT=18792 e PLAYWRIGHT_BASE_URL=http://127.0.0.1:17090. Estado privado de autenticação e ambiente não foram impressos nem adicionados ao Git.


### Reprodução HTTP após incorporar main

EV-36 usou a seguinte seleção em apps/server. O teste de submissão unitário e os jobs possuem provas separadas. A configuração Redis apenas permite importar a app, pois as fixtures usam recursos descartáveis.

```sh
REDIS_URL=redis://127.0.0.1:1/0 uv run pytest \
 tests/intelligence/preparation/test_prepare_planning_indexes.py \
 tests/intelligence/capabilities/test_planning_capabilities.py \
 tests/intelligence/server/controllers/test_get_planning_session_controller.py \
 tests/learning/server/controllers/test_start_skill_controller.py \
 tests/learning/server/controllers/test_search_skill_catalog_controller.py \
 tests/learning/server/controllers/test_get_choice_activity_controller.py \
 tests/learning/server/controllers/test_get_choice_attempt_controller.py \
 tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py \
 tests/learning/server/controllers/test_submit_choice_activity_controller.py \
 tests/shared/server/controllers/test_check_health_controller.py \
 tests/learning/server/controllers/test_remove_goal_controller.py \
 tests/identity/server/controllers/test_sign_in_controller.py \
 tests/identity/server/controllers/test_register_account_controller.py \
 tests/identity/server/controllers/test_main_page_entered_controller.py \
 tests/shared/rest/handlers/test_app_error_handler.py
```

EV-42 carregou ambiente privado do suporte sem imprimi-lo, importou playwright.config.ts e definiu SHIFU_SERVER_APP_PORT=17790, SHIFU_MENTOR_STREAM_TEST_PROXY_PORT=18792, SHIFU_IDENTITY_ACCOUNT_TEST_PROXY_PORT=18793, PLAYWRIGHT_BASE_URL=http://127.0.0.1:17090 e CI=true. A porta17791 dos jobs permaneceu separada.

# Lessons Learned

- ACH-09/EV-10: inicialização do SDK e portas prontas não provam renderização. O browser recusou service worker em origem opaca. A compatibilidade de isolamento deve ser provada antes de congelar essa decisão. Decisão Q5=A registrada na revisão 3. A prova atual de origem distinta, isolamento e serviço disponível está em EV-18/20. Não exige política global nova.
- ACH-12/EV-05/10: argumentos com JSON aninhado precisam de transporte que preserve bytes no WebContainer. A correção usa Base64 UTF-8 e uma asserção de round-trip na fronteira existente. Não exige nova política global.
- ACH-04/EV-09/19/22–25: mover testes por nome não resolve divergências entre fronteiras e autoridades. Q6 autorizou reconciliar os limites e preservar suas afirmações em consumidores reais. Rules, checker e seletores permanentes foram atualizados juntos. A distinção entre teste defensivo e prova de HTTP/qualidade/execução permanece explícita.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | codex/shifu-90-spec. Main0f1ee09a incorporado pelo merge5837ab8d. Correção e provas em4bea0918. Spec revisão3 e Evaluation completed após CI e reviews. Registro final somente documental em publicação. |
| Completed | CA-01–13 Complete/Passed, CI-01–09 e VM-01–04 atuais. Revisões independentes PASS. CI23/23Passed no candidato4bea0918, nenhuma conversa bloqueante. EV-36–46. |
| Unfinished | Conferir CI do último commit exclusivamente documental antes da resposta final. Nenhuma implementação ou decisão de escopo pendente. |
| Uncommitted work | Somente Spec/Evaluation de conclusão, publicados no mesmo PR. Código integral e correções já publicados. Segredos, ambientes, estado de navegador, capturas e logs ignorados não entram no Git. Checkout original com alterações alheias preservado. |
| Active processes | Nenhum. Browser shifu90-merge, Web47309 e suporte56871 encerrados. API17790/inferência18790/PG/Redis próprios limpos pelo suporte, ambiente privado removido. Playwright40840 e jobs encerrados por suas fixtures. ss confirmou livres17090/17790/17791/18790/18792/18793. Nenhum serviço compartilhado parado. |
| Blockers | Nenhum bloqueio de implementação ou review. CI do commit documental final em acompanhamento. |
| Next action | Publicar registro factual final e conferir CI atual. Não fazer merge na main, deploy ou alteração Atlassian. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Learning RP-09/11/12/13/14/18/24/25/29, JN-07/08/11/13; Curriculum RP-03/JN-03 | RF-01–11 / CA-01–13 | EV-02–46, com limites por critério | implemented no recorte selecionado. CA-01–13 possuem provas atuais. CI-09 completo. Os requisitos completos dos módulos não são declarados entregues por esta fatia; checkboxes canônicos permanecem inalterados. |


| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/45 | 2d2729f73d010c3edea77cc71c4c387d662f5956 | Histórico Failed. Web teardown e Recall anterior, resoluções EV-33/38/45. | [Server](https://github.com/CtrI-Alt-Del/shifu/actions/runs/40252104827), [Web](https://github.com/CtrI-Alt-Del/shifu/actions/runs/40252104778), [Email](https://github.com/CtrI-Alt-Del/shifu/actions/runs/40252104790) |

| https://github.com/CtrI-Alt-Del/shifu/pull/45 | efa34742c92bf1cc0426ff1096438e924d43bd30 | Histórico:22Passed, apenas retrieval Failed pelo mínimo anterior. | Server40252621269/Web40252621163/Email40252621186 |
| https://github.com/CtrI-Alt-Del/shifu/pull/45 | 4bea09183d90f6f750aaa9354735bf0be7559463 | Passed23/23, zero conversas abertas e reviewDecision vazio. Primeira tentativa MentorFailed preservada EV-44, repetição únicaPassed EV-45. | [Server](https://github.com/CtrI-Alt-Del/shifu/actions/runs/40257456886), [Web](https://github.com/CtrI-Alt-Del/shifu/actions/runs/40257456644), [Email](https://github.com/CtrI-Alt-Del/shifu/actions/runs/40257456602) |

| Field | Result |
| --- | --- |
| Publication | PR45 publicado na mesma branch, base main. Candidato4bea0918Passed23/23. Conclusão factual de revisão3 em Spec/Evaluation será publicada no commit documental final, com conferência dos checks desse head antes da resposta final. Sem merge/deploy ou escrita Atlassian. |
| Source verification | Learning83066881v26 e Curriculum83034113v13, leituras completas atuais reutilizadas. Metadados reconfirmados via Atlassian Shifu MCP nesta publicação: Learning83066881v26 e Curriculum83034113v13, títulos/status atuais inalterados. Leituras completas anteriores da mesma conversa reutilizadas. |
| Documentation Alignment | Emendas AI/Jobs aprovadas preservadas. Manutenção Q6 reconcilia Core/UseCase/AI/Database/Provision/Controller/Widget Rules, checker e seletores Poe/CI. Tooling descreve os limites permanentes. REST examples atualizados e conferidos pelo reviewer. Nenhum PRD, Pencil, Jira ou Confluence alterado. |
| Revision History | Revisão3 incorpora Q5=A para origem própria validada e Q6 para preservar/migrar os14testes nesta worktree. Emenda auditada e implementada. |
| Limitations | Prévia renderiza com origem distinta validada. Modelo determinístico local não prova qualidade de inferência remota. Inngest18791 deliberadamente indisponível: um evento de avaliação existe, consumidor XP não executado e UI mostra confirmação pendente. Erros vendor Process aborted ocorreram no descarte do ambiente; console do resultado reaberto contém apenas dica ReactDevTools. Na revisão3, edição da API reiniciou Node watch e gerou dois GET500/JSONparse transitórios; depois houve nova prontidão e GET/PATCH200. Instalação inicial levou46s e ultrapassou a primeira espera de60s com bootstrap; a prévia depois renderizou. Process aborted no descarte/freeze é encerramento do fornecedor. Resultado reaberto sem erros ou avisos de console. Nenhum erro não explicado usado como prova de sucesso. |

Continuação autorizada em2026-10-25: Q5=A permite origem própria validada da prévia e nova prova de isolamento. Q6 determina resolver os14caminhos nesta mesma worktree. Spec revisão3 foi declarada ready após revisão independente e agora está completed após implementação, provas e conclusão local. EV-04/05/06/07 dependentes do sandbox/configuração foram reabertos somente no escopo afetado, com provas atuais em EV-17/26/27. V-01/V-02 foram recapturadas e aprovadas em EV-21. Manutenção é sem mudança de produto; seus caminhos, afirmações e resultados ficam em EV-16 e CI-09. Nenhuma escrita externa autorizada.

Continuação de publicação: invocação explícita conclude-spec em2026-10-25 autoriza fetch/merge do main remoto, commits e PR. Não autoriza merge na main, deploy ou escrita Atlassian. gh confirmou conta autenticada e repositório CtrI-Alt-Del/shifu, base padrão main. Fetch origin main e merge --no-edit origin/main retornaram Already up to date em8ee992a7. Nenhum código, fixture, dependência ou configuração mudou na sincronização; todas as provas locais e revisões permanecem válidas. Pesquisa por head não encontrou PR existente.

Publicação confirmada: PR45, título [SHIFU-90] Questões integradas React e Fastify, base main, head codex/shifu-90-spec, commit2d2729f73d010c3edea77cc71c4c387d662f5956. PR sem conversas de review na inspeção inicial, zero resolvidas, reviewDecision vazio. A versão instalada de gh não suporta headRefOid ou run list --commit; SHA e runs lidos via gh api autenticado. Primeiro commit foi recusado pelo hook apenas por linha de body maior que100caracteres; mensagem corrigida e commit aprovado com hooks, sem bypass. Hook de lint da raiz verificou767arquivos sem erros e com15avisos herdados.

Sincronização posterior autorizada: usuário informou main atualizada e mínimoRecall89%. Fetch origin/main encontrou0f1ee09a, merge de PR46/SHIFU-97. Além do limiar0.90→0.89, vieram perfil/segurança de conta, autenticação, migration própria de Identity, fixtures e outra migração dos14testes. Foram20conflitos de testes/seletores. Preservada a união das asserções/scenarios, sem escolher arquivos inteiros de um lado. As três conformidades de domínio aprovadas na revisão3 permanecem junto aos novos consumidores de main. ProductionIdentity/auth e migration de main preservadas.

Verificação pós-merge: EV-36–42 substituem somente provas afetadas por main. MínimoRecall0.89 veio de main por instrução do usuário e3checks reais passaram sem alterar ranking. Todos os13critérios continuam implementados. Head anterior efa34742 teve22checksPassed e apenas Server real AI evalsFailed pelo mínimo anterior. Seus runs Server40252621269/Web40252621163/Email40252621186 são históricos. Nenhuma conversa de review encontrada e reviewDecision vazio na nova inspeção.

Conclusão após incorporação de main: RF-01–11/CA-01–13 implementados e verificados, Spec revisão3 completed. Checks locais afetados e CI atual23/23Passed. ACH-01–26 encerrados. MínimoRecall89% veio de main por decisão explícita do usuário, sem alegar melhora de ranking. Fonte Learning83066881v26/Curriculum83034113v13 preservada. Registro final apenas documental, sem alteração de contrato/produto. Nenhum recurso próprio em execução e nenhuma mudança alheia incluída.
