# Project state

## Decisions

None - não há AD geral ativo neste fluxo. Decisões específicas confirmadas para SHIFU-105: reconhecimento nativo local obrigatório, hook compartilhado, ausência de backend/OpenRouter e transcrição acrescentada ao final do rascunho após uma quebra de linha, watchdogs de 30s/10s e instalação de pacote de idioma por gesto explícito quando o navegador permitir, e suporte por capacidade verificada com digitação nos demais ambientes (Q5=A), avaliação de seis amostras pt-BR com erros/limitações documentados, sem limiar numérico de acurácia (Q6=A).

## Handoff

**Feature**: shifu-105-mentor-dictation, plano revision7.
**Where**: plano revision7 aprovado; checks C1–C39 derivados antes de Build; implementação em hook compartilhado e contexto/compositor existentes.
**In progress**: commit08c5006 entregue localmente; round1 independente35/39 PASS, lacunas de prova e observação de instalação corrigidas, preparando commit e round2.
**Next step**: commit escopado e Verifier fresco sobre feature base..HEAD com todos os checks; executar validate_verification.py. Não declarar entrega completa com C34 bloqueado.
**Blockers**: C34: Chrome151 Linux retorna local pt-BR unavailable; seis resultados nativos reais ausentes. Digitação permanece utilizável. Nenhuma decisão de arquitetura/escopo pendente; usuário autorizou continuar implementação explicitamente.
**Uncommitted**: correção de observação de instalação e testes suplementares em apps/web; .specs/STATE.md/checks.md; verification.md do Verifier. design/shifu.pen preexistente preservado e excluído de staging. Nenhuma operação Pencil de escrita.
**Branch**: feat/shifu-105.
**Feature base**: c2adb6ad85d35f7ddd5cb8eb35754791f10ef5df.
**Sessions/ports**: API7777 via uv/main.py (exec34832), web7000 via pnpm/Vite (exec62328), CLI shifu105; encerrar apenas estes ao terminar validação. Docker compartilhado preservado, nenhum evento Inngest emitido.

### Working evidence

- Repositório começou limpo; .codegraph/ existe. Não há .specs anterior nem store de lessons. Nenhum prompt de documentation/prompts foi lido/aplicado.
- Jira12615/SHIFU-105 e PRD83099649v7 completos lidos via Atlassian Shifu, cloudId b02dca9c-1d01-40c3-bef0-85720330145e. Política100106241v4 lida completa. Nenhuma mutação externa.
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
