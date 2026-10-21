# SHIFU-105 — Feature state

## Artifact scope

User decision: handoff, decisions and lessons belong only to this feature. Keep STATE.md, lessons.json and LESSONS.md in this directory; do not create repository-wide memory files under .specs/. The skill’s default shared-memory layout is overridden for this task.

## Decisions

Rev9 removes the six-sample quality criterion at the user's explicit request. Current implementation decision: browser-managed native pt-BR through the shared hook; possible browser-cloud processing is disclosed in the Composer. No backend transcription, OpenRouter, or Shifu audio storage. Reviewed dictation appends to the existing draft; 30s/10s watchdogs and other checks remain.

## Handoff

**Feature**: shifu-105-mentor-dictation, plano revision10.
**Where**: plano revision10 reconciliado com Intelligence PRD v9; C34 e a avaliação de seis amostras seguem retirados por pedido explícito. O critério de aviso de processamento em nuvem permanece ativo. Implementação no hook compartilhado e contexto/compositor existentes.
**In progress**: nenhuma implementação pendente. Candidate feature code commit fece469; 39 checks ativos aprovados em fca6445 e relatório verificado em e842217.
**Next step**: criar commit documental escopado, publicar/atualizar um único PR e registrar CI/review do head atual.
**Blockers**: nenhum bloqueio de implementação. A elegibilidade ZDR do provedor de reconhecimento gerenciado pelo navegador está fora do escopo desta feature, conforme decisão do usuário e Intelligence PRD v9. RP-13 permanece aplicável à inferência de IA fornecida pelo Shifu.
**Uncommitted**: exclusão do `.specs/STATE.md` compartilhado será incluída para manter o estado desta feature apenas em `.specs/features/shifu-105-mentor-dictation/`; `design/shifu.pen` permanece preexistente e fora do commit. Nenhuma operação Pencil de escrita.
**Branch**: feat/shifu-105.
**Feature base**: c2adb6ad85d35f7ddd5cb8eb35754791f10ef5df.
**Sessions/ports**: API7777 (exec34832), web7000 (exec62328) e CLI shifu105 encerrados após verificação. Docker compartilhado preservado. Nenhum evento Inngest emitido; apenas registro automático do Dev Server durante execução da API. Auth state e capturas locais ignorados, nunca stageados. Log de relay da tarefa reduzido a início/fim após encerrar processo, com tamanho original registrado.

### Working evidence

- Repositório começou limpo; .codegraph/ existe. Não há .specs anterior nem store de lessons. Nenhum prompt de documentation/prompts foi lido/aplicado.
- Jira12615/SHIFU-105 e PRD83099649v9 completos lidos via Atlassian Shifu, cloudId b02dca9c-1d01-40c3-bef0-85720330145e. Política100106241v4 lida completa. PRD v9 mantém a divulgação do processamento gerenciado pelo navegador e remove a exigência de elegibilidade ZDR específica para esse modo.
- CodeGraph `Mentor page FAB composer send message draft attachments conversation lifecycle transcription audio speech provider` e `useComposer useMentorContextProvider MentorContextValue useMentorPage useMentorFab MentorChat Conversation`: Composer compartilhado, microfone/anexos desabilitados, rascunho sem anexos.
- CodeGraph sobre provider hook/sendFirstMessage/startNewConversation/selectSession/closePanel e caminhos de autenticação: seleção e callback têm detailGeneration; fechar FAB preserva rascunho; troca de conta remonta contexto; uma revisão de rascunho própria é necessária.
- CodeGraph `transcription audio speech recording MediaRecorder getUserMedia browser microphone provider approved privacy openrouter MentorModelPipe Settings` e query restrita de áudio: nenhuma captura, port, controller ou modelo STT existente; buscas locais posteriores limitadas confirmaram FAQ de indisponibilidade. Todas as consultas CodeGraph funcionaram.
- CodeGraph dos middlewares/API/access provider e leituras de fonte estreitas: rota nova fora do no-store e limite de corpo; limiter global10/IP+1token/s; timeout Axios15s; postFormData omite defaultHeaders; authorize/assert_current com mesmo grant detecta conta inativa/revisão alterada; não prova revogação atômica ou encerramento coordenado.
- SHIFU-99 local completed/revision8; SHIFU-100 implemented/revision18 com runtime local-only. Nenhuma Spec local de SHIFU-103 encontrada. Fonte atual não possui limite superior de caracteres para mensagem; o cap de transcrição proposto é novo e não herdado do título.
- Pencil inicialmente tinha HMS ativo: nós não encontrados e visitors falharam. Após retry, get_app_state confirmou `/Ubuntu-22.04/home/petros/projects/shifu/design/shifu.pen`; seis nós e três componentes foram lidos e screenshots inspecionadas. Layouts de ditado desktop/mobile íntegros nas capturas; não representam runtime implementado.
- Regras consultadas para desenho do plano: router documentation/rules.md, arquitetura, módulos, UI, REST, providers, AI, composição do servidor e design; manifests web/server. Repetir roteamento e leitura completa das regras de código/testes que forem ativadas antes de Build.
- Evidência de comandos existentes: apps/web usa pnpm test:unit/test:integration/check:types/check:lint/check:architecture; apps/server usa uv run pytest e uv run poe check:types/check:lint/check:architecture. Nenhum desses checks de implementação foi executado nesta fase.

- Revisão2, 2026-10-13: usuário esclareceu que deseja transcrição simples via recurso nativo do navegador e confirmou ausência de backend/OpenRouter. Plano anterior não aprovado substituído pelo plano browser-only. Removidos endpoints, uploads, modelo externo, caps de arquivo e infraestrutura de STT.
- MDN SpeechRecognition e processLocally: API nativa pode usar engine remoto; processLocally true exige processamento local e é experimental. available permite consultar idioma local; stop tenta concluir reconhecimento, abort cancela. Portanto nativo não equivale automaticamente a local/ZDR. Default local proposto explícito no plano, com decisão humana pendente sobre suporte limitado.
- Evidência anterior de middleware/transportes/fornecedores permanece registro da investigação, mas não define o escopo revision2. Integração agora é frontend, preservação de rascunho, callbacks/limpeza, acessibilidade e envio de texto existente; nenhum código novo foi escrito.
- Revisão3: usuário determinou wrapper da API nativa em hook compartilhado. Plano registra useSpeechRecognition em apps/web/src/ui/shared/hooks/use-speech-recognition.ts; hook possui API/instância/eventos/limpeza, Mentor possui conta/conversa/rascunho. Nenhum adapter novo em provision/speech. CodeGraph consultado para shared hooks/contexto e paths existentes inspecionados; documentação apenas, nenhum código criado.

- Revisão4: usuário respondeu ok às recomendações de reconhecimento local obrigatório/fallback para digitação e append após newline. Essas confirmações não aprovam os demais defaults ou o plano completo; próximas perguntas cobrem watchdogs e instalação de idioma.

- Revisão5: usuário respondeu ok aos watchdogs de início30s/finalização10s e à oferta de Instalar pacote de idioma por ação explícita. Substituída a proposta não aprovada de proibir install por uso nativo explícito, estados de instalação e nenhuma captura automática. MDN install_static lido para confirmar método/resultado/limitações; suporte e avaliação de qualidade permanecem perguntas abertas.

- Revisão6: protocolo grilling aplicado diretamente na conversa (uma pergunta por mensagem). Q5=A confirma suporte por capacidade; usuário confirmou que pacote nativo local pt-BR precisa estar instalado antes de ditar, via ação explícita quando disponível, sem gravação automática. Última pergunta Q6 cobre avaliação de qualidade; nenhum código ou checks criado.

- Revisão7: Q6=A confirma avaliação de seis exemplos pt-BR, registro de erros/limitações e nenhum limiar numérico de acurácia. Assumptions e Open questions fechados; plano consolidado para revisão humana final. Nenhum código, checks ou commit criado.


- Build 2026-10-13: 145 testes afetados em16 arquivos PASS, 4 testes de composição PASS, tipos/lint/arquitetura/build exit0. Logs em apps/web/.playwright-cli/logs/shifu-105-{unit,composition,lint,build}.log. Capturas CLI e avaliação em visual-evidence.json. Perfil light, sem fault injection.
- CodeGraph antes de cada nova exploração: composer/index.tsx/use-composer/tests; provider/accountEmail/clearPrivateState; fixtures Identity/BFF e browser suites; useSpeechRecognition/current consumers; FAQ MentorResources; auth provider/middleware para diagnosticar origem local. Consultas funcionaram, narrow reads complementaram funções anônimas/configs.
- Correção de launch: 127.0.0.1 divergira do origin/issuer localhost configurado; nenhum código Identity foi alterado. CLI em localhost com formulário visível obteve autenticação real e carregou intelligence sem redirect.
- Testes novos escritos pelos checks antes da implementação; falhas RED confirmadas. Correções: cancelamento por accountEmail, guarda independente de resposta ativa, foco de revisão, callbacks de escopos abandonados e idioma ainda unavailable após install true.
- FAQ muda checksum de corpus, requer preparação de índice no rollout pelo procedimento existente. Nenhum índice compartilhado reescrito, inferência remota permanece desativada.
- A seção Grilling do prompt create-spec foi utilizada somente porque o usuário pediu o protocolo; outros prompts/workflows SDD não foram aplicados. O registro histórico inicial de nenhum prompt lido refere-se à fase anterior ao pedido de Grilling.


- Round2 independente: 76 testes de proof/3 targets PASS; seis browser cases PASS na repetição completa, quatro static/build gates exit0; todos C1–C33/C35–C39 PASS, C34 BLOCKED. Report em verification.md auditou HEAD99be56d. Primeira rodada de browser teve3/6 timeouts; log relay da sessão antiga chegara a1.2GB; rerun inalterado6/6 PASS após encerramento da sessão task-owned. Causalidade exata não afirmada.
- validate_verification.py executado pelo Verifier e autor: exit1 por C34; nenhum outro finding de implementação/prova permanece. Lessons L001–L003 registradas por script para copy visível, medidas/foco no browser e invalidação de promessas no abandono. Nenhuma publication externa autorizada/feita.


- 2026-10-13, reported inactive microphone: user reports Chrome and no unavailable message after reload/Nova conversa. Read-only reproduction in regular headed Chrome151.0.7922.108 via Playwright CLI/Xvfb, using existing shared app/API, confirmed local pt-BR unavailable, microphone HTML-disabled, fallback visible, zero recording states after pointer click. Browser-managed availability returned available; this is capability evidence, not successful transcription. User-profile attachment failed because the Playwright extension was absent; the missing hint in the user's tab remains unreplicated. Logs: apps/web/.playwright-cli/logs/shifu-105-{headed-click,browser-modes,user-browser-connect}.txt; screenshot shifu-105-headed-click.png. All diagnosis-owned browser sessions closed; existing app/API and user changes preserved. No code/contract edits. Enabling browser-managed processing requires revising the user's approved local-only decision; no silent remote fallback.


- Revision8: usuário aprovou (“ok”) reconhecimento gerenciado pelo navegador, inclusive possível nuvem de Chrome. Mentor chama useSpeechRecognition('pt-BR',false); não exige pacote local nem instala idioma. Hook mantém opção local explícita e regressões condicionais. Copy informa serviço na nuvem. Conflito com ZDR do PRD83099649v7/política100106241v4 registrado; sem alteração externa ou alegação de conformidade. Append/watchdogs/privacidade do backend preservados.
- CodeGraph queries: Mentor/shared hook callers, Composer/status/test paths, browser installation helpers; JSON resource não é simbolizado e foi identificado pelo diff rastreado. Native Chrome click: mic enabled, recording real por3s, cancel→recording0/draftpreserved; zero mock nesta prova.6browsercases e78focusedtests PASS,4static/buildgates PASS.12freshCLIcaptures inspected. C34 ainda requer6outcomes reais. Nova sessão CLI shifu105managed pertence à tarefa e será fechada; app/API existentes pertencem ao usuário e permanecem ligados.

- Candidate revision8 committed locally as fece469adf74347fd5da7a228803548d397c0f84.80 focused tests/3targets and6 affected browser cases PASS; types/lint/architecture/build passed before commit. Shared corpus loader MentorResources PASS; indexes not rebuilt. Fresh independent Verifier browser_managed_dictation_verifier dispatched after commit over full feature base..HEAD, with all40checks; no source/test edits allowed.
- Precommit initially failed on formatting of the user-relocated untracked lessons.json. Biome format changed whitespace only; its data/placement preserved and file remained untracked. Actual repository commit hooks passed. Skill check_commit.py still rejects required uppercase Jira key; conflict previously documented. Main CLI shifu105managed closed. Existing shared app/API/Docker and unrelated hms-source-sync session untouched.

- C34 follow-up: existing browser speechSynthesis has no voices (voiceCount0,pt-BRvoices[]), OS has only English flite voices and no Portuguese synthesis executable/library. Probe apps/web/.playwright-cli/logs/shifu-105-portuguese-audio-source.txt. No controlled pt-BR source was synthesized, and no six outcomes claimed. This is an evidence-source limit, not a statement that browser-managed recognition is unavailable. Probe-only CLI shifu105audio closed.

- Independent round3 at fece469:39/40checks PASS; C34 BLOCKED only.80unit tests,6browser scenarios, types/lint/architecture/build and visual evidence PASS independently. No blocking implementation finding. Landing wording classified nonblocking because immediately following paragraphs explicitly represent cloud processing and unresolved ZDR; no material obligation missing. Main completion validator rerun exit1 solely C34. Shared app/API/Docker remain running; all main-owned CLI sessions closed; no new source changes after commit, no push/PR/Atlassian write. Remaining dirty paths are user root-memory relocation, unrelated design/shifu.pen, and feature-local post-commit handoff/report/lessons.

- Revision9, 2026-10-13: usuário pediu remover C34. Plano e checks ativos não exigem seis amostras, acurácia nem documento de qualidade. O `quality-evidence.json` com resultados não executados está marcado RETIRED e não é validado. Critérios restantes aguardam Verifier independente e completion gate.

- Revision9 verification handoff: commit fca6445 removes C34 per the user request and marks historical quality-evidence RETIRED. A fresh independent verifier is checking the 39 active checks and completion gate.
