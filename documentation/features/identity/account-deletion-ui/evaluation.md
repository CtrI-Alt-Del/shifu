---
title: SHIFU-98 — interface de exclusão de conta evaluation
status: ready
spec: ./spec.md
last_updated_at: 2026-10-25
---

# Current State

| Campo | Estado |
| --- | --- |
| Implementação | CA-01–04 completos neste recorte de UI. |
| Automated | CI-01–06 e integridade aprovados. 41 testes unitários; 13 cenários da página aprovados pela seleção inicial12 + rerun afetado1. |
| Tipos / lint / complexidade | Passed separadamente em EV-10. Lint mantém11avisos fora da mudança e diagnóstico interno de diretório scripts ausente. Métricas quantitativas não configuradas/não exigidas. |
| Manual / Visual | VM-01 e VM-02 aprovados. Login real, desktop/mobile e quatro capturas verificadas. |
| Revisão independente | Implementação e visual aprovadas após correção ACH-01. |
| Bloqueios | Nenhum nesta fatia. Exclusão real permanece fora do escopo. Código da UI publicado com6/6checksCIaprovados em93a065fe; manutenção posterior do teste de infraestrutura de UI descrita emEV-12/13. |
| Candidato | codex/shifu-98-deletion-ui; base7db714aa, main incorporado em0f1ee09a sem mudança de árvore; código93a065fe; registro documental posterior no worktree /home/petros/.codex/worktrees/shifu-98-deletion-ui/shifu. |

# Progress

| CA | RF | Implementação | Verificação | Prova | Restante |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | EV-02,04–06,09–10 | Nenhum neste recorte |
| CA-02 | RF-02 | Complete | Passed | EV-02,04–07,09–10 | Nenhum neste recorte |
| CA-03 | RF-03 | Complete | Passed | EV-02,05,07,09–10 | Nenhum neste recorte |
| CA-04 | RF-04 | Complete | Passed | EV-02,05–07,09–10 | Nenhum neste recorte |

# Check Results

| EV | Check / tipo | Resultado | Ambiente / procedimento / limite |
| --- | --- | --- | --- |
| EV-01 | Autoridade / pesquisa | Passed | Identity Confluence 83001345 v2 lida integralmente; Jira SHIFU-98; Pencil MCP y2vJij/LbeWb e exportação escala1. .codegraph ausente no worktree, sem indexação criada. Context7 confirmou Dialog controlado e Trigger/Close. Spec Reviewer independente sem bloqueios, recomendou montagem condicional para descartar senha sem depender de efeitos em Activity. |
| EV-02 | CI-01 / Automated | Passed | Builder: pnpm test:unit src/ui/identity/widgets/pages/account-page, 8 arquivos/41 testes, 15.39s. Testes dos componentes, hooks e consumidores existentes. |
| EV-03 | CI-03–06 / Automated | Passed antes da correção | Tipos passaram após corrigir opção exact inválida de Testing Library; Biome focado passou. Projeto lint exit0,11avisos preexistentes e diagnóstico interno de diretório apps/web/scripts inexistente, já referenciado pelo script de lint. Não é falha de arquivos alterados. Arquitetura681módulos/2724dependências sem violações; build exit0. Complexidade configurada no Biome sem diagnóstico novo nos caminhos alterados, sem runner quantitativo. Logs apps/web/.playwright-cli/logs/shifu98-{lint,architecture,build}.log. |
| EV-04 | CI-02 / Automated | Failed histórico | 13 cenários selecionados em tests/identity/account-page.test.ts,12passaram/1falhou em1.5min. Falha do novo teste ao pressupor foco inicial no link de política; Radix focou senha. Corrigida a expectativa e a interação de checkbox para foco+Espaço. Log shifu98-integration.log preservado. |
| EV-05 | VM-01 / Manual | Passed antes da correção | Playwright CLI sessão shifu98; login visível real com conta ativa isolada criada pela fixture Identity, API7798/Web7098/PostgreSQL54998/Redis6398 próprios. Rota/account e aba por teclado; senha+confirmação não habilitam exclusão; cancelar/Escape devolvem foco e descartam campos. Política abre /privacy, retorno à conta funciona e campos vazios. Console0erros, requests observados sem envio de exclusão. Desktop1440×900 e mobile390×844 sem overflow. Login inicial aguardava incorretamente /home; corrigido para rota real / e navegação /account, sem defeito de produção. |
| EV-06 | VM-02 / Visual | Passed antes da correção | Quatro capturas shifu98-{delete,modal}-{desktop,mobile}.png em apps/web/.playwright-cli/screenshots/, inspecionadas pelo Orchestrator e Visual Reviewer independente. Primeira captura mobile ocorreu durante animação; substituída após opacidade1. Sem desvios materiais fora do handoff. Rever somente os dois modais após ACH-01. |
| EV-07 | CI-02 / Automated | Passed antes da correção | Rerun somente novo cenário de exclusão após ajuste do teste, log shifu98-integration-deletion-rerun.log. Os12cenários anteriores permanecem válidos. |
| EV-08 | Integridade / Automated | Passed | pnpm check:test-integrity,399arquivos. git diff --check passou. Detector Impeccable focado retornou [] sem achados. |
| EV-09 | Correção ACH-01 / Automated, Manual, Visual | Passed | Builder repetiu41testes/8arquivos em5.44s. Novo cenário de navegador passou1/1em30.2s após cabeçalho, checkbox por teclado e foco correto. Log shifu98-integration-final.log. Os12demais cenários anteriores permanecem válidos porque o ajuste é exclusivo ao modal. Playwright CLI confirmou novo Fechar: limpa senha/consentimento e devolve foco ao gatilho; final continua bloqueado. Consulta na conta isolada confirmou statusactive/deleted_atnull. Dois modais recapturados nos mesmos caminhos e inspecionados pelo Orchestrator/Visual Reviewer; os dois cartões anteriores válidos. Implementation Reviewer resolveu ACH-01 e aprovou. |
| EV-10 | CI-03–06 / Automated final | Passed | pnpm check:types exit0; pnpm check:lint exit0; pnpm check:architecture exit0,681módulos/2724dependências; pnpm build exit0. Logs shifu98-{types,lint,architecture,build}-final.log. Após encerrar Vite, repetido lint para diagnosticar a leitura incompleta: exit0,685arquivos,11avisos preexistentes e diagnóstico interno persistente porque apps/web/scripts não existe, embora package.json o inclua no comando. Sem diagnósticos nos arquivos alterados; lint focado aprovado. Log shifu98-lint-stopped-runtime.log. Biome configurado prova complexidade lint, sem métrica quantitativa. |
| EV-11 | CI remoto / Automated | Passed | PR47, candidato de código93a065fe357522645c272fe97398b0171e48a703. Web6/6checks aprovados: tipos, lint, arquitetura, unitários165arquivos e integração260/260em6.2min, build. Run https://github.com/CtrI-Alt-Del/shifu/actions/runs/40257540991. Log local shifu98-ci-93a065fe.log. Main0f1ee09a incorporado sem mudanças de árvore, resultados locais preservados. Revisão GitHub:0threads,reviewDecisionnull; revisões independentes locais EV-09 aprovadas. Este registro documental não muda código, contratos, configuração ou fixtures. |
| EV-12 | CI remoto posterior / Automated | Failed histórico | Head31061e1b, que só acrescentou documentação. Unitários165arquivos/1373testes passaram, mas Vitest encerrou com1exceção não tratada window is not defined de React após teardown, atribuída a use-proposal-skill-graph.test.ts. Run40258308760, job121364865000. Log shifu98-ci-31061e1b-unit.log. Investigação identificou arrays criados a cada renderHook que reativavam layout assíncrono e ausência de cleanup explícito. |
| EV-13 | Correção de limpeza do teste / Automated | Passed local | Manutenção restrita a apps/web/src/ui/intelligence/widgets/pages/planner-page/planning-proposal-review/tests/use-proposal-skill-graph.test.ts. Arrays locais estáveis e afterEach(cleanup); todas as asserções preservadas. Suite focada4/4aprovada em3execuções separadas, sem erros não tratados; Biome focado e tipos Web aprovados. Revisão independente sem achados. Sem mudança de produção, contrato, dependências ou configuração. CI do head final é acompanhado no PR47. |

# Findings

| ACH | Problema | Gravidade | Estado / correção |
| --- | --- | --- | --- |
| ACH-01 | Implementação independente identificou ausência de ícone lateral, ação de fechar superior e separador no cabeçalho exigido pelas regras UI. | P2 | Resolved: ícone à esquerda, título/descrição agrupados, botão Fechar superior e separador. Handoff alinhado. EV-09/10 aprovados e revisões independentes resolvidas. |
| ACH-02 | Teste de navegador pressupunha foco no link e tentava clicar o input visualmente oculto do checkbox. | Teste | Corrigido para foco real na senha e teclado Espaço. EV-07 passa; EV-09 revalidou foco e fechamento após mudança de cabeçalho. |
| ACH-03 | Teste antigo do grafo do Planejador mantinha hooks montados e dependências novas a cada render, repetindo layout assíncrono até o ambiente ser descartado. CI posterior falhou mesmo com todas as asserções aprovadas. | CI / teste | Correção implementada e verificada emEV-13; sem alteração de produção. Falha históricaEV-12preservada. Resultado do head final acompanhado no PR. |

# Lessons Learned

Montagem condicional do painel evita guardar a senha ao trocar de aba sem depender de efeitos suspensos pelo React Activity. Regras existentes suficientes. Checkbox compartilhado é utilizável pelo rótulo visível e teclado; testes devem representar esse uso.

# Handoff

| Campo | Detalhe |
| --- | --- |
| Candidato | codex/shifu-98-deletion-ui, códigoUI93a065fe357522645c272fe97398b0171e48a703, main0f1ee09a incorporado sem mudança de árvore; registro documental31061e1b e manutenção pontual de teste em commit posterior na mesma branch. |
| Concluído | CA-01–04, CI-01–06, VM-01/02, integridade e revisões independentes. |
| Pendente | Nenhum nesta entrega parcial. Integração de exclusão real pertence ao restante da SHIFU-98. |
| Arquivos locais | account-page/index.tsx,use-account-page.ts,tests/account-page.test.tsx,tests/use-account-page.test.ts; deletion-panel/**; apps/web/tests/identity/account-page.test.ts; documentation/features/identity/account-deletion-ui/**. Somente trabalho desta entrega e manutenção pontual de use-proposal-skill-graph.test.ts necessária para corrigir a falha de CI. Incluídos nos commits autorizados; sem alterações alheias. |
| Processos | Nenhum ativo. Encerradas API7798, Web7098, navegador shifu98 e processos de integração7108/proxy7799. Conta isolada limpa. Containers próprios shifu98-ui-postgres54998 e shifu98-ui-redis6398 encerrados/removidos. Arquivos temporários de ambiente e storage removidos. Serviços compartilhados7000/7777 e Docker preservados. |
| Próxima ação | Revisão humana do PR47. Após o registro documental, acompanhar os checks do head no próprio PR, sem repetir validação local não afetada. Integração do servidor permanece fora deste recorte. |

# Delivery

| RP/JN | Escopo | Evidência | Disposição |
| --- | --- | --- | --- |
| RP-09/JN-09 | RF-01–03 | EV-01–10 | partially_implemented: UI pronta. Encerramento/eliminação/validação de senha remota adiados. |
| RP-10 | RF-04 | EV-02,05–10 | implemented no recorte de UI, desktop/mobile/teclado. |

| Campo | Resultado |
| --- | --- |
| Publicação | Publicado https://github.com/CtrI-Alt-Del/shifu/pull/47, main←codex/shifu-98-deletion-ui. Código93a065fe, CI6/6aprovado no run40257540991. Registro documental31061e1b revelou falha no teardown de teste preexistente (EV-12), corrigida por manutenção pontual (EV-13). Estado dos checks do head final disponível no PR. Sem merge/deploy ou escrita Jira/Confluence. |
| Fonte | Identity Confluence83001345v2. Sem mudança de requisitos ou escrita externa. SHIFU-98 permanece pendente em seu escopo integral. |
| Documentação | Spec revisão1 implemented; Evaluation ready. Handoff documenta cabeçalho vigente, ação desabilitada e adaptações mobile. SHIFU-97 e seus registros no worktree anterior preservados. |
| Limites | Não existe execução de exclusão nem verificação remota da senha. Avisos de desenvolvimento do Vite/TanStack e11avisos preexistentes de lint não foram alterados. O comando global de lint também referencia apps/web/scripts inexistente e emite diagnóstico interno com exit0; validação focada dos arquivos alterados não tem esse diagnóstico. Capturas não provam exclusão; conta continua ativa, conforme esperado. |
