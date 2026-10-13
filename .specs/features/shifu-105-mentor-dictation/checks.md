# SHIFU-105 — Checks de ditado nativo

Profile: light
Plan: `.specs/features/shifu-105-mentor-dictation/plan.md`

34 critérios de aceitação ativos. C34 foi removido por solicitação explícita do usuário na revision9; IDs posteriores preservados para rastreabilidade histórica. Quatro gates de tipos/lint/arquitetura/build permanecem. Cada Proof é obrigação planejada, não resultado executado. Nenhum arquivo de áudio integra a entrega.

## Checks

### S1 — Ditar e enviar

**C1** - WHEN o aprendiz acionar Gravar ditado na página ou no FAB THEN o sistema — iniciar o reconhecimento nativo em pt-BR somente após esse gesto explícito. (AC 1)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'starts native recognition only on an explicit gesture'`

**C2** - WHILE estiver preparando o reconhecedor ou aguardando permissão o sistema — mostrar Preparando ditado… com Cancelar disponível. (AC 2)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'exposes preparation with cancellation'`

**C3** - WHEN o reconhecedor começar a capturar THEN o sistema — mostrar Gravando ditado… com duração mm:ss e controles Cancelar e Encerrar ditado. (AC 3)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'exposes recording duration and controls'`

**C4** - WHEN o aprendiz acionar Encerrar ditado THEN o sistema — chamar stop() e mostrar Transcrevendo ditado… enquanto aguarda a finalização nativa. (AC 4)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'stops recognition and awaits finalization'`

**C5** - WHEN a operação terminar com resultados finais válidos THEN o sistema — acrescentar exatamente transcricao.trim() ao rascunho original, separando por uma quebra de linha se o rascunho não for vazio. (AC 5)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'appends final text without changing the existing draft'`

**C6** - WHEN incorporar a transcrição THEN o sistema — mostrar Revise seu ditado, devolver foco ao campo editável e apresentar Edite o texto se precisar e toque em Enviar. (AC 6)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'focuses the editable reviewed draft'`

**C7** - WHILE uma operação de ditado estiver preparando, gravando ou finalizando o sistema — impedir submissão por Enviar ou Enter no compositor. (AC 7)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/use-composer.test.ts -t 'blocks sending and Enter during dictation'`

**C8** - WHEN o aprendiz enviar o rascunho revisado THEN o sistema — encaminhar exatamente seu texto pelo fluxo existente de primeira mensagem ou mensagem subsequente. (AC 8)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'sends only the explicitly reviewed text'`

**C9** - The sistema — criar zero conversas, mensagens ou respostas como efeito de iniciar, reconhecer ou cancelar um ditado. (AC 9)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'creates no message during dictation'`

**C10** - IF a conversa tiver envio em andamento, resposta em andamento, mensagem pendente ou acesso ainda não confirmado THEN o sistema — impedir iniciar o ditado nesse compositor. (AC 10)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'guards dictation while conversation access or response is pending'`

### S2 — Recuperação

**C11** - WHEN cancelar em preparação, gravação ou finalização THEN o sistema — chamar abort() na instância iniciada e preservar exatamente o rascunho atual. (AC 11)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'cancels every active stage without changing the draft'`

**C12** - IF ocorrer not-allowed ou service-not-allowed THEN o sistema — comunicar Permissão do microfone negada. Você pode continuar digitando. sem alterar o rascunho. (AC 12)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'preserves the draft on permission denial'`

**C13** - IF ocorrer audio-capture THEN o sistema — comunicar Não foi possível usar o microfone. Tente novamente ou continue digitando. sem alterar o rascunho. (AC 13)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'preserves the draft on microphone failure'`

**C14** - IF ocorrer no-speech, nomatch, erro de reconhecimento ou término sem texto final THEN o sistema — comunicar Não foi possível reconhecer o ditado. Tente novamente ou continue digitando. sem incorporar resultados parciais. (AC 14)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'rejects empty or failed recognition without partial text'`

**C15** - IF a preparação/permissão não concluir em 30s THEN o sistema — cancelar a operação com Não foi possível iniciar o ditado. Tente novamente ou continue digitando. (AC 15)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'times out preparation after thirty seconds'`

**C16** - IF a finalização não concluir em 10s após Encerrar THEN o sistema — cancelar a operação com Não foi possível concluir o ditado. Tente novamente ou continue digitando. (AC 16)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'times out finalization after ten seconds'`

**C17** - WHEN o navegador encerrar naturalmente uma sessão com texto final válido THEN o sistema — apresentar o texto para revisão sem reiniciar automaticamente o reconhecimento. (AC 17)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'reviews a natural end without automatically restarting'`

**C18** - WHERE existir uma coleção de anexos preparados o sistema — preservar seus itens e ordem durante sucesso, cancelamento e falha de ditado. (AC 18)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'keeps unavailable attachment controls untouched'`
Condição atual: nenhuma coleção de anexos existe nesta base; prova protege os controles existentes e o texto. A preservação de uma coleção futura não é declarada verificada.

### S3 — Ciclo de vida

**C19** - WHEN fechar o FAB, trocar conversa, iniciar Nova conversa, excluir a conversa selecionada, abandonar a superfície ou observar mudança de conta/acesso THEN o sistema — invalidar a operação e chamar abort() no reconhecedor iniciado. (AC 19)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'aborts dictation when its owning scope is abandoned'`

**C20** - IF um callback pertencer a uma conta, conversa ou geração anterior THEN o sistema — ignorá-lo sem modificar o estado atual. (AC 20)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'rejects stale callbacks from an earlier operation'`

**C21** - IF a revisão do rascunho mudar durante o ditado THEN o sistema — descartar seu resultado com Seu rascunho mudou. O ditado não foi aplicado., preservando exatamente o texto atualizado. (AC 21)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'rejects recognition after the draft revision changes'`

**C22** - WHEN o navegador repetir um evento de resultado ou término THEN o sistema — incorporar cada trecho final da operação no máximo uma vez e na ordem de seus índices. (AC 22)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'applies repeated final results only once in index order'`

**C23** - WHEN uma operação concluir ou for cancelada THEN o sistema — remover seus handlers/timers e descartar resultados finais ainda não aplicados. (AC 23)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'cleans native handlers and timers at termination'`

**C24** - The sistema — transmitir zero payloads de áudio ao backend do Shifu ou ao OpenRouter durante o ditado. (AC 24)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'makes no transcription or audio transport calls'`

**C25** - The sistema — criar zero arquivos, blobs ou registros de áudio para o fluxo de ditado. (AC 25)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'creates no audio files or blobs'`

### S4 — Suporte e privacidade

**C26** - WHEN criar o reconhecedor em ambiente elegível THEN o sistema — configurar reconhecimento gerenciado pelo navegador (processLocally false quando suportado) antes de chamar start(), sem exigir pacote local. (AC 26)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'starts browser-managed recognition without local processing support'`

**C27** - IF o navegador não suportar a API ou o serviço de reconhecimento disponível THEN o sistema — comunicar Ditado indisponível neste navegador. Continue digitando. mantendo o campo e o envio de texto utilizáveis. (AC 27)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'preserves typing when browser recognition is unavailable'`

**C28** - WHERE o hook for consumido em modo local explícito (não ativo no Mentor) WHEN o aprendiz acionar Instalar pacote de idioma, com pt-BR local instalável e método nativo disponível, THEN o sistema — solicitar a instalação pelo método nativo do navegador. (AC 28)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'installs Portuguese only on an explicit action'`

**C29** - WHERE o hook for consumido em modo local explícito (não ativo no Mentor) WHILE o pacote estiver sendo instalado o sistema — mostrar Instalando pacote de idioma… sem iniciar captura de microfone. (AC 29)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'announces installation without acquiring the microphone'`

**C30** - WHERE o hook for consumido em modo local explícito (não ativo no Mentor) IF a instalação falhar THEN o sistema — comunicar Não foi possível instalar o pacote de idioma. Tente novamente ou continue digitando. preservando o rascunho. (AC 30)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'preserves the draft when installation fails'`

**C31** - WHERE o hook for consumido em modo local explícito (não ativo no Mentor) WHEN a instalação concluir THEN o sistema — informar Pacote de idioma instalado. Você pode gravar seu ditado. sem iniciar reconhecimento automaticamente. (AC 31)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'announces installation success without starting recognition'`

**C32** - The controles de ditado — ter nomes acessíveis em pt-BR, foco identificável, estados anunciados por tecnologia assistiva e alvos de toque de pelo menos 44px no mobile. (AC 32)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'renders accessible keyboard dictation controls'`

**C33** - The bloco de ditado — seguir copy e arranjo dos estados s8UGf/qsYWq/QZB2M em 1440×1058 e nxL5i/e9FXb/VC7Ro em 390×900, adaptado ao FAB e aos tokens existentes. (AC 33)
Proof: `cd apps/web && pnpm test:integration tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts --grep 'renders native dictation states'`
Proof: `python3 .specs/features/shifu-105-mentor-dictation/verify-evidence.py --filter visual`

**C35** - The sistema — realizar zero instalações de pacote de idioma sem o gesto explícito Instalar pacote de idioma. (AC 34)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts -t 'never installs a language pack automatically|never installs in browser-managed mode'`

**C36** - Contratos TypeScript e consumidores afetados compilam sem erros.
Proof: `cd apps/web && pnpm check:types`

**C37** - Arquivos alterados passam Biome, incluindo regras de complexidade configuradas.
Proof: `cd apps/web && pnpm check:lint`

**C38** - Nenhuma dependência proibida ou circular nova é introduzida.
Proof: `cd apps/web && pnpm check:architecture`

**C39** - A aplicação web produz o build configurado.
Proof: `cd apps/web && pnpm build`

**C40** - Antes de iniciar ditado browser-managed, o Composer mostra “O navegador pode usar um serviço na nuvem para reconhecer sua fala.” (AC35)
Proof: `cd apps/web && pnpm test:unit src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx -t 'discloses browser-managed recognition before microphone use'`

## Coverage

| Set (size) | Member -> proof | Unproven |
| --- | --- | --- |
| Superfícies (2) | page C1/C33 · fab C1/C33 | - |
| Estados de ditado (6) | idle C1 · preparing C2 · recording C3 · transcribing C4 · review C6 · error C12/C13/C14 | - |
| Cancelamento (3) | preparing C11 · recording C11 · transcribing C11 | - |
| Guardas de conversa (4) | submission C10 · pending response C10 · pending message C10 · validating access C10 | - |
| Falhas nativas (6) | not-allowed C12 · service-not-allowed C12 · audio-capture C13 · no-speech C14 · nomatch C14 · empty end C14 | - |
| Abandono do escopo (7) | close FAB C19 · select conversation C19 · new conversation C19 · delete selected C19 · navigation C19 · unmount C19 · account/access change C19 | - |
| Callbacks tardios (3) | operation C20 · conversation C20 · account C20 | - |
| Disponibilidade nativa (5) | missing constructor C27 · missing local API C26 · unavailable service C27 · browser-managed available C26 · optional local downloadable C28 | - |
| Instalação (3) | installing C29 · failure C30 · success C31 | - |
| Referências visuais (6) | s8UGf C33 · qsYWq C33 · QZB2M C33 · nxL5i C33 · e9FXb C33 · VC7Ro C33 | - |

Não há nova rota, entidade persistida ou one-way door no plano. O campo Unproven acima indica falta de proof atribuída, não conclusão da execução. Não há set de acurácia/amostras: C34 foi removido explicitamente na revision9. A condição de anexos tem conjunto vazio nesta base; a integração real futura continua fora desta conclusão.

## Test policy

As regras existentes resolvem os níveis: componente com owning hook mockado; guards de useComposer em teste colocated; hook compartilhado real exercitado no consumidor/contexto com API nativa controlada; rota real com transporte controlado para composição. O fluxo nativo é coberto por comportamento e fallback; não existe obrigação de avaliar acurácia nem reunir amostras. Não criar teste de provision ou fingir que mocks provam speech recognition real. Perfil light: sem fault injection e sem recomputação independente de Coverage.

## Swept

- validation: C5, C14, C26, C27
- failure modes: C12, C13, C14, C15, C16, C30
- idempotency: C22, C35
- authorization: C10, C19, C20; existing - rota protegida e contexto por accountEmail
- concurrency: C7, C20, C21, C22
- data lifecycle: C11, C19, C23, C24, C25
- dependency failure: C26, C27, C30
- state transitions: C2, C3, C4, C6, C11, C17, C29, C31
- observability: n/a - nenhum log de áudio/transcrição ou analytics novo

## Handoff

Uma única fatia coerente de frontend, com todas as decisões de domínio e integração mantidas pelo autor principal. 117.510 bytes nos consumidores/testes existentes identificados, mais allowance de 60.000 bytes para hook, testes novos, suporte de browser e evidência = 177.510 / 4 = aproximadamente 44.378 tokens. Sob budget150k: one builder, sem corte de fatia ou mecanismo adicional. O explorer de capacidade é read-only e não é builder.

Feature base: `c2adb6ad85d35f7ddd5cb8eb35754791f10ef5df`. Plano aprovado pelo usuário em 2026-10-13. Nenhum push/deploy autorizado.

## Results

2026-10-13 — implementação local validada pelo autor; veredito independente pendente.

| Checks | Resultado do autor | Evidência |
| --- | --- | --- |
| C1–C32, C35 | PASS nos testes correspondentes | `apps/web/.playwright-cli/logs/shifu-105-unit.log`: 145 testes, 16 arquivos, nomes individuais em reporter verbose. C6 inclui prova adicional de foco no hook real e composição; C8 inclui primeira mensagem e conversa existente; C19/C20 incluem conta, seleção e rejeição de acesso. |
| C18 | PASS condicional nesta base | Nenhuma coleção de anexos preparada existe; apenas controles existentes/texto preservados. |
| C33 | PASS | Quatro cenários automatizados page/FAB em 1440×1058 e 390×900 passaram. Doze capturas via Playwright CLI inspecionadas e registradas em visual-evidence.json; autenticação real, eventos de fala controlados. Foco/Enter/cancelamento sem clipping. |
| C34 | BLOCKED | Chrome151 Linux suporta API local, mas `available({langs:['pt-BR'],processLocally:true,quality:'dictation'})` retorna unavailable. `quality-evidence.json` mantém seis amostras sem transcrição; zero qualidade inventada. |
| C36–C39 | PASS | types/lint/architecture/build reexecutados após correção final com exit0. Lint registra seis warnings e diagnóstico de diretório scripts ausente preexistente; architecture 438 módulos/1479 dependências. |

RED antes da implementação: testes de início falharam por ausência de dictationLanguageAvailability; testes do Composer falharam por ausência de estados/guards/foco. Correções posteriores foram guiadas pelos checks e testes, sem enfraquecer asserts. Red adicional de instalação detectou anúncio incorreto após install true com idioma ainda unavailable; corrigido.

Limites de nível: API nativa controlada comprova integração/estados, não processamento real nem acurácia. Autenticação dos testes de composição é controlada; jornada manual via CLI deve registrar separadamente a autenticação real. Perfil light: nenhuma mutação injetada.


Manual CLI: autenticação por formulário visível em localhost:7000, alinhado ao issuer configurado. Cookie state anterior expirou; renovado localmente. Fallback nativo observado com mic disabled, aviso correto, rascunho editável e Enviar enabled. Quatro jornadas controladas com autenticação real confirmaram iniciar/encerrar/cancelar por Enter, append/foco e edição; registro `apps/web/.playwright-cli/logs/shifu-105-cli-ui-result.txt`. Nenhuma mensagem/conversa foi criada nessas jornadas. Capturas não comprovam persistência nem reconhecimento real.

FAQ: recurso validado pelo carregador MentorResources; texto diferencia anexos indisponíveis e ditado por capacidade. O checksum do corpus muda: preparação dos índices pelo procedimento existente é necessária antes de ativar esse corpus em um ambiente. Índices compartilhados não foram reescritos nesta tarefa.

Commit format conflict: check_commit.py rejects the repository-required uppercase Jira prefix SHIFU-105 as a lowercase-description violation. Repository commit-rules.md/commitlint requires that exact prefix; use the repository-enforced message and retain the actual validator failure instead of changing the skill or claiming PASS.


Round1 independente em 08c5006: 35/39 PASS; C27/C31/C32 tiveram lacunas de assert, C34 BLOCKED. Finding adicional: instalação ainda observada após abandonar fluxo, contrariando Flow. Correção: invalidar observação no hook e vincular instalação à superfície no contexto, sem cancelar download nativo. Três regressões de close/navigation/surface falharam antes da correção e passaram após.

Round2 candidato do autor: 150 testes afetados/16 arquivos PASS; seis cenários de composição PASS (quatro page/FAB×viewport mais dois de instalação mobile). C27/C31 ganharam asserts literais de copy no componente; C32 mede width/height≥44, tabindex0, foco e outline computado em microfone/Cancelar/Encerrar/Instalar. Uma versão do setup de foco atravessava o chrome do navegador com Tab/Shift+Tab e disparava revalidação de acesso/cancelamento existente; setup limitado ao controle com tecla de navegação, mantendo todos os asserts de tamanho/foco/outline. A callback ResizeObserver está igual à base; repetição CLI de quatro jornadas registrou errors=[] em shifu-105-observer-probe.txt. Nenhuma correção de Identity ou do resize preexistente.


## Final disposition

Independent round2 em HEAD99be56d: **38/39 PASS; C34 BLOCKED**. Sem findings restantes de implementação ou prova local. 76 testes/3 targets de proofs e seis browser cases passaram independentemente; types/lint/architecture/build exit0. Autor também executou150 testes afetados/16 targets. `validate_verification.py shifu-105-mentor-dictation` exit1,1erro,0warnings porque a evidência nativa real de qualidade não existe.

Primeira execução independente de browser round2 teve3/6 timeouts. A repetição completa passou6/6 sem mudar timeout/assert/fonte; antiga aba CLI da tarefa gerava relay de erros e log Vite1.2GB. Isso é consistente com pressão transitória, sem provar causa exclusiva. Observação original ResizeObserver e falha inicial preservadas no report; sessão CLI e processos API/web da tarefa encerrados após validação. Logs runtime/capturas/state continuam locais e ignorados; relay log teve apenas o início/fim preservado para evitar deixar1.2GB de ruído.

Commits locais:08c5006 (feature) e99be56d (correção/provas suplementares). Nenhum push, PR ou alteração Atlassian. Código validado; conclusão integral aguardando C34 num ambiente elegível. Report/STATE/lessons pós-commit permanecem arquivos locais, sem alterar o candidato auditado.


Artifact placement amendment: per user instruction, STATE.md, lessons.json and LESSONS.md were moved into this feature directory. Root-level shared-memory files no longer exist. Acceptance criteria, implementation and verification evidence are unchanged.


## Browser-managed amendment — approved 2026-10-13

O usuário aprovou explicitamente a troca de modo. C26/27 passam a testar o modo browser-managed do Mentor: não depender de processLocally/available locais, usar available({processLocally:false}) quando existente e iniciar sem instalação local. C28–31 permanecem regressões do hook real em modo local explicitamente selecionado no harness; não representam a configuração ativa do Mentor. C35 continua proibindo instalação implícita. A qualidade C34 usa process_locally false; resultados anteriores de bloqueio local são históricos. Nova divulgação pt-BR: “O navegador pode usar um serviço na nuvem para reconhecer sua fala.”, comprovada por teste de Composer. Não declarar ZDR de Chrome nem conformidade com a política publicada.


Revision8 author results:80 focused tests/3 targets PASS,6 browser cases PASS, types/lint/architecture/build exit0. New checks first failed:4 recognition cases under the old local-only implementation and1 privacy-copy case. Actual authenticated Chrome151 at localhost:7000 had microphoneEnabled=true and entered Gravando ditado… (00:03), with no controlled recognition API. Cancellation removed recording and preserved exact draft. This proves native start/cancel, not six speech-to-text outcomes. Logs:shifu-105-browser-managed-{native-click,native-cancel,cli-ui}.txt and{unit,integration,types,lint,architecture,build}.log in apps/web/.playwright-cli/logs. All12 new captures inspected; cloud notice legible, no clipping. Browser console had only React DevTools INFO. Optional local-mode regressions explicitly select real shared-hook local mode in the consumer harness; production Mentor explicitly selects false.


## Amendment revision9 — 2026-10-13

A pedido explícito do usuário, C34 e a exigência de seis transcrições reais foram removidos. Os resultados históricos de reconhecimento indisponível permanecem em verification.md e quality-evidence.json apenas como registro das rodadas anteriores; não participam dos checks ativos. Os IDs C35/C40 e gates subsequentes permanecem estáveis. A Coverage não contém qualidade representativa.
