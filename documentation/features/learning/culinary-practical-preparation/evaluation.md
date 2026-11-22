---
title: Preparação prática culinária evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-22
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Completa para RF-01 a RF-15 no código. Contrato avaliado: Spec revisão 3. |
| Automated checks | Servidor e web passaram nas seleções afetadas (EV-03 a EV-08). Os testes Playwright novos da web estão Bloqueados localmente no Windows (EV-09) e ficam para o CI Linux. |
| Type / lint / complexity | Passados no servidor e na web (EV-03, EV-06). Complexidade pelas regras configuradas de lint, sem medidor quantitativo (Não aplicável). |
| Manual checks | VM-01 passou na validação do orquestrador-validador (EV-10). VM-02 passou em parte. VM-03 só alcançou "sem nota" e falha recuperável. **O usuário assumiu a validação final no navegador.** |
| Visual checks | VM-04 parcial: boards desktop alcançados comparados (EV-12). Mobile por captura, dispensa aprovada pelo usuário. |
| Independent review | Código: revisado, correções aplicadas (ACH-05, ACH-06 a ACH-08). Visual: revisado sobre capturas existentes (ACH-09). |
| Blockers | Nenhum bloqueio externo. Pendências no Handoff. |
| Candidate | Branch `claude/shifu-130-preparacao-pratica-culinaria`, commits da task ainda a criar. |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 / EV-04 | Nenhuma |
| CA-02 | RF-02 | Complete | Passed | CI-01, CI-04 / EV-04, VM-01 EV-10 | Nenhuma |
| CA-03 | RF-03 | Complete | Passed | CI-02 / EV-05, VM-02 EV-10 | Nenhuma |
| CA-04 | RF-04 | Complete | Passed | CI-03, CI-07 / EV-05, EV-07 | Nenhuma |
| CA-05 | RF-05 | Complete | Passed | CI-03, CI-06 / EV-05, EV-06 | Nenhuma |
| CA-06 | RF-06 | Complete | Passed | CI-04 / EV-04 | Nenhuma |
| CA-07 | RF-07 | Complete | Passed | CI-04 / EV-04, VM-01 EV-10 | Nenhuma |
| CA-08 | RF-08 | Complete | Passed | CI-05 / EV-04 (workflow em processo) | Qualidade do agente: eval em `apps/server/evals` em modo duplo; execução com o modelo real feita só em script isolado (EV-11) |
| CA-09 | RF-09 | Complete | Partial | CI-05 / EV-04; EV-11 (nota 65 com o modelo real) | Resultado "concluído" não visto no navegador |
| CA-10 | RF-10 | Complete | Passed | CI-05 / EV-04; VM-03 EV-10 (sem nota no navegador) | Nenhuma |
| CA-11 | RF-11 | Complete | Passed | CI-05 / EV-04; VM-03 EV-10 (falha recuperável e retry na mesma tentativa) | Nenhuma |
| CA-12 | RF-12 | Complete | Partial | CI-04, CI-07 / EV-04, EV-07; VM-03 EV-10 | Estados "em andamento" e "concluído" sem captura examinada |
| CA-13 | RF-13 | Complete | Passed | CI-03, CI-06 / EV-05, EV-06 | Nenhuma |
| CA-14 | RF-14, RF-15 | Complete | Partial | CI-07, CI-08 / EV-07, VM-01/02 EV-10 | Foco visível, botão de enviar a 390 px com FAB/navegação, Playwright no CI |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | Penpot MCP e boards / preparação | Passed | 2026-11-21 e 2026-11-22, arquivo Shifu | `execute_code`, `export_shape` | Desktop com 11 boards; Mobile com 0 (dispensa aprovada). |
| EV-02 | PRD Learning v35 / fonte | Passed | 2026-11-21 | `getConfluenceContent` | Versão 35 confirmada. |
| EV-03 | CI-08 / Automated / servidor tipos, lint, arquitetura, formato | Passed | Candidato com todas as fatias, 2026-11-22 | `uv run poe check:types`, `check:lint`, `check:architecture`, `ruff format --check` em `apps/server` | 0 erros, 0 avisos, 0 notes de tipos; lint e formato limpos (1897 arquivos); tach validado. |
| EV-04 | CI-01, CI-04, CI-05 / Automated | Passed | Postgres Testcontainers, 2026-11-22 | `uv run pytest tests/curriculum tests/learning -k ...` | Curriculum 209 passados; práticos de Learning 89 passados; seleção final 894 passados e 11 pulados antes do ajuste de 2 testes de controller. |
| EV-05 | CI-02, CI-03 / Automated | Passed | Postgres e storage em memória | Controllers e casos de uso de rascunho/foto | 44 controllers e 71 casos de uso práticos passaram após o ajuste (EV-04 teve 2 falhas por reencode de WebP, corrigidas nos testes). |
| EV-06 | CI-06 / Automated | Passed | `SHIFU_RUN_REAL_INNGEST_TESTS=1` | `uv run pytest tests/messaging/inngest/jobs/learning` e `tests/learning/messaging` | 8 testes passados sem pular; migração `e48385bfd6fe` subiu, desceu e subiu em Postgres descartável. |
| EV-07 | CI-07 / Automated / unit | Passed | 2026-11-22 | `pnpm --filter web test:unit` na raiz | 201 arquivos, 1949 testes passados. Uma rodada anterior terminou com código 1 e a seguinte passou (suíte instável sob carga). |
| EV-08 | CI-08 / Automated / web | Passed | 2026-11-22 | `pnpm --filter web check:types`, `check:lint`, `check:architecture`, `build` | Sem erros nem avisos; 841 arquivos checados pelo lint. |
| EV-09 | CI-07 / Playwright | Blocked | Windows | `pnpm exec playwright test tests/learning/...` em `apps/web` | `playwright.config.ts` usa `exec ./node_modules/.bin/vite`, que não roda no Windows. Cobertura fica para o CI Linux. |
| EV-10 | VM-01, VM-02, VM-03 / Manual | Partial | API e web locais, conta seed, 2026-11-22 | `playwright-cli` pela UI | VM-01 passou. Rascunho restaurou após recarregar e em outro contexto a 390 px. "Sem nota" passou. Falha com Tentar novamente passou. "Concluído" não visto; o modelo real marcou o registro `during` como insuficiente e a rubrica do banco local tinha uma regra só (explicado em ACH-04). O usuário fará a validação final. |
| EV-11 | CI-05 / modelo real | Passed (script isolado) | `openai/gpt-6-luna` via OpenRouter, ZDR | Script e workflow em processo, Testcontainers | Fotos de comida: nota 65; fotos de ruído: sem nota. Sem rodar na API do usuário. |
| EV-12 | VM-04 / Visual | Partial | Boards desktop e capturas existentes | Penpot MCP e capturas `shifu130-r2-*` | Inicial, reflexão, falha na avaliação e sem evidência: aprovados com desvios aceitos. Falha na foto: captura antiga. Sem captura: envio, concluído, falha ao salvar, foto em envio, em andamento. Varredura de 4 páginas do Penpot: 0 avisos nos boards de Culinária. |
| EV-13 | `pnpm check:test-integrity` | Failed (pré-existente) | Raiz, 2026-11-22 | `pnpm check:test-integrity` | Falha só nos 2 arquivos da SHIFU-129: `tests/curriculum/providers/test_curriculum_content_provider.py` e `tests/learning/server/controllers/test_ordering_response_models.py`. Não fazem parte do CI nem do hook. Os arquivos novos da SHIFU-130 passam. |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Página Mobile do Penpot sem boards de Preparação prática. Afeta CA-14. | Média | VM-04 | Resolvido por dispensa aprovada pelo usuário em 21/11/2026 (Design Contract). |
| ACH-02 | O limite de 512 KiB só cobre POST, não o PUT da foto. | Baixa | CI-03 | Resolvido: middleware próprio de PUT. |
| ACH-03 | Fixture de jobs sem variáveis de storage. | Baixa | CI-06 | Resolvido: stub de S3 no fixture. |
| ACH-04 | A rubrica de demonstração tinha uma regra de insuficiência só; com o modelo real, o registro `during` insuficiente gerava falha recuperável em vez de "sem nota". | Média | CI-05, VM-03 | Resolvido no código (regra por registro nos fakers e no seed). O banco local semeado antes não muda sem novo seed, que o usuário não autorizou. |
| ACH-05 | Spec Reviewer: 6 bloqueios e 5 de severidade alta ou média sobre caminhos de teste, remoções, middleware, nomes. | Alta | CI-01 a CI-08 | Resolvido na Spec rev. 1; segunda passada sem bloqueios. |
| ACH-06 | Revisão de código: corrida de upload com a mesma chave podia apagar o objeto de foto `ready`. | Alta | CI-03 | Resolvido; testes de concorrência e conclusão tardia adicionados. |
| ACH-07 | Revisão de código: decodificação de 10 MB antes da autorização; metadados EXIF/GPS armazenados. | Média | CI-03 | Resolvido: autorização antes, metadados removidos (Spec rev. 3). |
| ACH-08 | Revisão de código: mensagens da web para 409/422 sem usar o código. | Baixa | CI-07 | Resolvido. |
| ACH-09 | Revisão visual: estados sem captura (envio, concluído, falha ao salvar, foto em envio, em andamento); foco visível não demonstrado; botão de enviar a 390 px pode ser coberto pelo FAB/navegação. | Média | VM-04 | Aberto: validação manual final do usuário. |
| ACH-10 | Aceitas sem correção: sem revisão esperada nas gravações do rascunho (regra aprovada: última gravação prevalece), foto presa em "enviando" sem expiração, linha `FAILED` remanescente, corpo do upload em memória (limitado a 10 MB). | Baixa | CA-03, CA-05 | Limitações registradas. |
| ACH-11 | Fora do escopo: formulário de login sem `method`; um clique antes da hidratação envia a senha na URL. `apps/web/src/ui/identity/widgets/pages/sign-in-page/index.tsx`. | Média | Nenhum | Registrado para tarefa separada. |
| ACH-12 | Lacuna do seed: a conta seed não alcança a Atividade de demonstração (competência 033 da Habilidade 032). | Baixa | VM-01 | Documentado: criar um Objetivo, adicionar a Habilidade 032 e iniciá-la pela interface, depois abrir a Atividade `01SHF000000000000000000994`. Seed não alterado, a pedido do usuário. |

| ACH-13 | Merge com a `main` em 2026-11-22 (SHIFU-125): 6 conflitos mecânicos de importações, rotas e testes; a migração `14fadc960949` da `main` criou uma segunda ponta do Alembic. | Média | CI-06, CI-08 | Resolvido: a migração `e48385bfd6fe` agora tem as duas pontas como `down_revision`; uma só ponta (`alembic heads`). Pós-merge: tipos 0 erros, lint e formato limpos, arquitetura ok, 507 testes de servidor e 853 de Learning na web passaram. |
| ACH-14 | Validação do autor em ambiente real: a avaliação com fotos reais (2,3 a 2,6 MB) falhava de forma intermitente. Com o modelo real, 2 de 6 execuções devolviam critério inconclusivo para um registro marcado suficiente, que Learning rejeita (RF-11). O `FrameworkError` do log era a própria linha de falha com o texto apagado pela telemetria. | Alta | CI-05, VM-03 | Resolvido: fotos reduzidas só na cópia enviada ao modelo (lado maior 1568 px, JPEG 85), prompt exige `sufficient=false` para critério nulo, falhas do workflow registram uma linha sanitizada (estágio, classe, código) pelo logger do Agno e a avaliação nunca fica pendente. 8 execuções reais seguintes válidas. |
| ACH-15 | O resultado não aparecia depois de "Tentar novamente": o polling só rodava com estado pendente. | Média | CI-07, VM-03 | Resolvido: janela de polling de 60 s depois do retry; nota da questão exibida quando o estado da tentativa não traz nota. |
| ACH-16 | Tentativas de revisão (Habilidade concluída) deixam a faixa de XP em "Confirmando…": o caso de uso retorna antes de emitir `ActivityEvaluatedEvent` para o tipo REVIEW. Comportamento anterior à SHIFU-130, vale para todos os formatos. | Média | Nenhum | Aberto, fora do escopo; decisão do usuário. |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Rubricas de demonstração precisam de uma regra de insuficiência por registro, senão o modelo real gera falha recuperável. | ACH-04, EV-11 | Aplicado aos fakers. Sem mudança em autoridade. |
| O `check:test-integrity` não roda na pipeline nem no hook e acumulou violações. | EV-13 | Proposta: incluir o script no CI em tarefa separada. |
| A configuração do Playwright é só Linux. | EV-09 | Proposta: tarefa separada para suporte a Windows. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | Branch `claude/shifu-130-preparacao-pratica-culinaria`, commits da task em preparação. |
| Completed | Spec rev. 3, as quatro fatias, revisões de código e visual, correções, checks do servidor e da web. |
| Unfinished | Validação final no navegador (usuário); estados "concluído" e "em andamento"; foco e botão a 390 px; Playwright no CI; revisão pós-PR. |
| Uncommitted work | Todo o código e os documentos da task. `SHIFU-130-plano-de-implementacao.md` é do usuário e não entra nos commits. |
| Active processes | Docker, API (7777) e web (7000) do usuário. Nenhum processo iniciado por esta task. |
| Blockers | Nenhum. |
| Next action | Commits, push, PR, acompanhar web-app-ci e server-app-ci. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Learning RP-32, RP-09/12/13/14/18/24/25/27/29, RP-21/22; Curriculum RP-03; JN-26 | RF-01 a RF-15 / CA-01 a CA-14 | EV-03 a EV-08, EV-10 a EV-12 | partially_implemented: código e automação completos; validação manual do resultado concluído e comparação visual de alguns estados pendentes; Playwright novo só no CI. |

| PR | Current head SHA | Review state |
| --- | --- | --- |
| A criar | A registrar | A registrar |

| Field | Result |
| --- | --- |
| Publication | Em andamento: PR único para a `main` |
| Source verification | Learning v35, Curriculum v19, Política v4 em 2026-11-21 |
| Documentation Alignment | Sem escrita em Confluence ou Jira. Design Contract e Spec atualizados (rev. 3). |
| Revision History | Revisões 1 a 3 na Spec |
| Limitations | Mobile sem boards (dispensa aprovada); `check:test-integrity` com 2 falhas da SHIFU-129; seed local não reaplicado. |
