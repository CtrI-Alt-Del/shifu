# SHIFU-105 — Ditado nativo do navegador para o Mentor

Status: approved — plano original confirmado em 2026-10-13; C34 removido a pedido explícito do usuário na revision9; fonte reconciliada com o PRD v9 na revision10. Data: 2026-10-13. Revision: 10.

Profile: light. Budget: 150k. Mantido o padrão da skill; o usuário não solicitou mudança de perfil.

## Problem

O aprendiz precisa digitar integralmente suas dúvidas no Mentor, inclusive no celular. A página e o FAB exibem um microfone desabilitado. O ticket não fornece métricas quantitativas do problema.

O resultado é simples: ditar, revisar e editar o texto, depois enviá-lo explicitamente. O usuário confirmou nesta conversa reconhecimento nativo do navegador, sem backend de transcrição nem OpenRouter. O Shifu não cria arquivo de áudio, upload ou armazenamento para esse fluxo.

O plano usa tlc-spec-lean e não usa os prompts atuais de SDD. O envio continua usando a gestão de conversas e o processamento atualmente entregues por SHIFU-99/100.

## Flow

Reutiliza o Composer e o rascunho compartilhados da página/FAB, a proteção de acesso existente e o envio de texto existente. Por decisão do usuário, a API nativa é envolvida pelo hook compartilhado `useSpeechRecognition`, em `apps/web/src/ui/shared/hooks/use-speech-recognition.ts`.

1. O gesto Gravar ditado entra em `Intelligence web` (exists): verifica suporte ao reconhecimento nativo, cria uma operação vinculada à conta/conversa/revisão do rascunho e solicita o reconhecimento em pt-BR.
2. `Intelligence web` (exists) consome o hook compartilhado de `Shared UI` (exists), que envolve SpeechRecognition e retorna estado, texto reconhecido, falha e ações de iniciar/encerrar/cancelar. O Mentor mostra Gravando ditado… sem mudar o rascunho durante a fala.
3. Encerrar entra em `Intelligence web` (exists): chama stop(), mostra Transcrevendo ditado… enquanto o reconhecedor finaliza e aguarda end. Cancelar chama abort() e invalida os callbacks.
4. `Intelligence web` (exists) aplica uma única vez o texto final à mesma revisão do rascunho, mostra Revise seu ditado e devolve o foco ao campo editável.
5. out: apenas o envio explícito do rascunho chama o fluxo existente de `Intelligence` (exists), que aceita a mensagem e processa a resposta vigente.

O reconhecedor nativo é responsável pela captura. Em 2026-10-13, após diagnosticar Chrome151 com pt-BR local unavailable e browser-managed available, o usuário aprovou explicitamente reconhecimento gerenciado pelo navegador, que pode enviar áudio ao serviço de nuvem do próprio navegador. O Mentor usa processLocally false e não exige nem oferece instalação de pacote local. A digitação permanece disponível se a API ou o serviço não estiver disponível. O hook mantém modo local opcional explícito, inclusive instalação e suas regressões, sem ativá-lo no Mentor. Não há obrigação de suportar uma lista fixa de navegadores.

O Shifu não usa MediaRecorder, não solicita um segundo stream com getUserMedia e não manipula chunks, Blob, base64 ou formatos de arquivo. O estado Transcrevendo representa a finalização do reconhecimento nativo, não uma requisição ao servidor.

A instância nativa, eventos, resultados por índice e limpeza pertencem ao hook compartilhado. Ele é independente de contas, conversas, anexos e rascunhos do Mentor. O contexto do Mentor consome uma única instância desse hook para ambas as superfícies e mantém as guardas de conta/conversa/revisão do rascunho. Cancelar, trocar o contexto ou abandonar a superfície invalida a operação antes de cancelar o reconhecimento; eventos posteriores não aplicam texto. O rascunho só muda no término válido da operação.

## Impact

| Front | What changes |
| --- | --- |
| domain | Ditado é uma forma temporária de compor texto em Intelligence. Mensagem, conversa e resposta mantêm seus significados. |
| compositor | O Composer comum à página e ao FAB ganha estados de preparação/permissão, gravação, finalização, revisão e erro. |
| shared hook | useSpeechRecognition envolve a API nativa e possui sua instância, eventos, estados e limpeza; é consumido pelo contexto do Mentor. A proposta anterior de arquivo native-speech-recognition.ts em provision/speech é substituída por essa decisão do usuário. |
| rascunho | O texto anterior é preservado; uma revisão de rascunho impede aplicação tardia sobre texto alterado. Novo ditado acrescenta texto ao final. |
| conversas | Fechar FAB, trocar conversa, iniciar Nova conversa ou abandonar o compositor encerra o ditado. O texto já revisado segue a continuidade atual do contexto compartilhado. |
| API/transporte | Nenhuma rota, payload, limite de upload, autenticação de STT ou timeout HTTP novo. Somente o envio de texto existente é consumido depois de Enviar. |
| stored data | Nada a migrar ou armazenar para ditado. Somente a mensagem explicitamente enviada usa a persistência existente. |
| anexos | Não existe estado de anexos preparados na base atual. Ditado não habilita SHIFU-103 e deve manter intocada qualquer coleção preparada quando essa capacidade existir. Sua ausência não introduz um projeto de armazenamento nesta feature. |
| acesso | Reutiliza o escopo autenticado atual. Mudanças de conta/acesso observadas pelo contexto cancelam o ditado; não entrega encerramento coordenado de contas ou novas garantias de revogação do servidor. |
| conteúdo local | A FAQ curada que anuncia ditado indisponível deve refletir os ambientes em que a capacidade estiver habilitada; não anunciar anexos como entregues. Se afetar o corpus indexado, usar seu procedimento existente de preparação. |
| design | Os seis estados Pencil inspecionados orientam arranjo e copy de ditado. Cota e anexos representados ao redor são capacidades independentes. |
| autoridade | documentation/design.md cita Intelligence v6/Política v3; PRD atual v7 e Política v4 prevalecem para comportamento. A diferença permanece explícita, sem alterar fontes externas. |

## Relations

None - no stored-data shape change. O reconhecedor e seus resultados ainda não aplicados são temporários no navegador. Nenhuma entidade de áudio ou de transcrição é persistida.

## Surface

None - nenhuma rota é adicionada ou tem assinatura alterada. O texto revisado usa o envio de mensagem existente.

## Landing

None - não há esquema persistido, dependência de pacote, contrato externo novo ou infraestrutura de inferência. A integração do serviço nativo e a máquina de estados são reversíveis no frontend.

Forma técnica confirmada pelo usuário: API nativa do navegador, sem backend/OpenRouter, envolvida por hook compartilhado em Shared UI. Forma proposta para implementação: SpeechRecognition, com compatibilidade webkitSpeechRecognition quando ela oferecer as capacidades requeridas; lang pt-BR, continuous true, interimResults false e maxAlternatives 1; start por gesto, stop para concluir e abort para cancelar. Um único reconhecedor ativo, possuído pelo hook compartilhado e consumido no contexto da conta.

Decisão de privacidade atual, aprovada pelo usuário: browser-managed, com processLocally false quando essa propriedade existir. Sem available() estático, a existência de SpeechRecognition/webkitSpeechRecognition permite tentar iniciar por gesto; falhas nativas continuam visíveis e preservam o rascunho. available() quando existente consulta processLocally false. A disponibilidade local não é requisito. O Composer informa que o navegador pode usar serviço na nuvem.

A decisão anterior (revision7) exigia modo local e instalação explícita. Esta aprovação substitui somente esse requisito no Mentor. O modo local permanece opção explícita do hook compartilhado com verificações reais; seus testes de instalação são regressões condicionais, não evidência de um fluxo habilitado no Mentor. Append com quebra de linha, watchdogs30s/10s e envio explícito permanecem.

Reconciliação: Intelligence83099649v9 exige aviso prévio quando o reconhecimento gerenciado pelo navegador puder enviar áudio ao provedor do navegador e confirma que o Shifu não recebe nem armazena o áudio. O usuário confirmou que a elegibilidade ZDR desse provedor está fora do escopo da feature. O fluxo usa a API nativa do navegador; não integra endpoint de IA controlado pelo Shifu nem declara conformidade ZDR do provedor. As proteções RP-13 para inferência de IA fornecida pelo Shifu permanecem inalteradas.

## Criteria

### S1: Ditar, revisar e enviar (P1)

A página e o FAB oferecem a mesma composição por voz.

**Acceptance Criteria**

1. WHEN o aprendiz acionar Gravar ditado na página ou no FAB THEN o sistema SHALL iniciar o reconhecimento nativo em pt-BR somente após esse gesto explícito.
2. WHILE estiver preparando o reconhecedor ou aguardando permissão o sistema SHALL mostrar Preparando ditado… com Cancelar disponível.
3. WHEN o reconhecedor começar a capturar THEN o sistema SHALL mostrar Gravando ditado… com duração mm:ss e controles Cancelar e Encerrar ditado.
4. WHEN o aprendiz acionar Encerrar ditado THEN o sistema SHALL chamar stop() e mostrar Transcrevendo ditado… enquanto aguarda a finalização nativa.
5. WHEN a operação terminar com resultados finais válidos THEN o sistema SHALL acrescentar exatamente transcricao.trim() ao rascunho original, separando por uma quebra de linha se o rascunho não for vazio.
6. WHEN incorporar a transcrição THEN o sistema SHALL mostrar Revise seu ditado, devolver foco ao campo editável e apresentar Edite o texto se precisar e toque em Enviar.
7. WHILE uma operação de ditado estiver preparando, gravando ou finalizando o sistema SHALL impedir submissão por Enviar ou Enter no compositor.
8. WHEN o aprendiz enviar o rascunho revisado THEN o sistema SHALL encaminhar exatamente seu texto pelo fluxo existente de primeira mensagem ou mensagem subsequente.
9. The sistema SHALL criar zero conversas, mensagens ou respostas como efeito de iniciar, reconhecer ou cancelar um ditado.
10. IF a conversa tiver envio em andamento, resposta em andamento, mensagem pendente ou acesso ainda não confirmado THEN o sistema SHALL impedir iniciar o ditado nesse compositor.

**Independent test:** na página e no FAB, ditar numa Nova conversa, encerrar, editar e enviar; observar que o histórico só muda no envio. Repetir numa conversa existente com as guardas atuais de resposta.

### S2: Cancelar e recuperar preservando o rascunho (P1)

O aprendiz pode voltar à digitação sem perder o texto preparado.

**Acceptance Criteria**

11. WHEN cancelar em preparação, gravação ou finalização THEN o sistema SHALL chamar abort() na instância iniciada e preservar exatamente o rascunho atual.
12. IF ocorrer not-allowed ou service-not-allowed THEN o sistema SHALL comunicar Permissão do microfone negada. Você pode continuar digitando. sem alterar o rascunho.
13. IF ocorrer audio-capture THEN o sistema SHALL comunicar Não foi possível usar o microfone. Tente novamente ou continue digitando. sem alterar o rascunho.
14. IF ocorrer no-speech, nomatch, erro de reconhecimento ou término sem texto final THEN o sistema SHALL comunicar Não foi possível reconhecer o ditado. Tente novamente ou continue digitando. sem incorporar resultados parciais.
15. IF a preparação/permissão não concluir em 30s THEN o sistema SHALL cancelar a operação com Não foi possível iniciar o ditado. Tente novamente ou continue digitando.
16. IF a finalização não concluir em 10s após Encerrar THEN o sistema SHALL cancelar a operação com Não foi possível concluir o ditado. Tente novamente ou continue digitando.
17. WHEN o navegador encerrar naturalmente uma sessão com texto final válido THEN o sistema SHALL apresentar o texto para revisão sem reiniciar automaticamente o reconhecimento.
18. WHERE existir uma coleção de anexos preparados o sistema SHALL preservar seus itens e ordem durante sucesso, cancelamento e falha de ditado.

**Independent test:** partir de texto existente, provocar eventos e exceções pelo consumidor da API nativa e verificar preservação exata. As falhas permitem nova tentativa por gesto; não reiniciam reconhecimento automaticamente. AC18 é compatibilidade com uma coleção quando existente, não declaração de entrega da SHIFU-103.

### S3: Encerrar o reconhecimento e rejeitar callbacks tardios (P1)

Uma operação pertence somente ao rascunho no qual começou.

**Acceptance Criteria**

19. WHEN fechar o FAB, trocar conversa, iniciar Nova conversa, excluir a conversa selecionada, abandonar a superfície ou observar mudança de conta/acesso THEN o sistema SHALL invalidar a operação e chamar abort() no reconhecedor iniciado.
20. IF um callback pertencer a uma conta, conversa ou geração anterior THEN o sistema SHALL ignorá-lo sem modificar o estado atual.
21. IF a revisão do rascunho mudar durante o ditado THEN o sistema SHALL descartar seu resultado com Seu rascunho mudou. O ditado não foi aplicado., preservando exatamente o texto atualizado.
22. WHEN o navegador repetir um evento de resultado ou término THEN o sistema SHALL incorporar cada trecho final da operação no máximo uma vez e na ordem de seus índices.
23. WHEN uma operação concluir ou for cancelada THEN o sistema SHALL remover seus handlers/timers e descartar resultados finais ainda não aplicados.
24. The sistema SHALL transmitir zero payloads de áudio ao backend do Shifu ou ao OpenRouter durante o ditado.
25. The sistema SHALL criar zero arquivos, blobs ou registros de áudio para o fluxo de ditado.

**Independent test:** entregar eventos atrasados após trocar contexto, cancelar, editar ou desmontar; observar abort/limpeza e nenhuma alteração tardia. Na jornada real observar o encerramento da captura nativa pelo estado do navegador. Não testar readyState de tracks que o Shifu não adquiriu.

### S4: Oferecer suporte acessível e privacidade compatível (P1)

O recurso respeita as capacidades reais do navegador; digitação permanece disponível.

**Acceptance Criteria**

26. WHEN criar o reconhecedor em ambiente elegível THEN o sistema SHALL configurar reconhecimento gerenciado pelo navegador (processLocally false quando suportado) antes de chamar start(), sem exigir pacote local.
27. IF o navegador não suportar a API ou o serviço de reconhecimento disponível THEN o sistema SHALL comunicar Ditado indisponível neste navegador. Continue digitando. mantendo o campo e o envio de texto utilizáveis.
28. WHERE o hook for consumido em modo local explícito (não ativo no Mentor) WHEN o aprendiz acionar Instalar pacote de idioma, com pt-BR local instalável e método nativo disponível, THEN o sistema SHALL solicitar a instalação pelo método nativo do navegador.
29. WHERE o hook for consumido em modo local explícito (não ativo no Mentor) WHILE o pacote estiver sendo instalado o sistema SHALL mostrar Instalando pacote de idioma… sem iniciar captura de microfone.
30. WHERE o hook for consumido em modo local explícito (não ativo no Mentor) IF a instalação falhar THEN o sistema SHALL comunicar Não foi possível instalar o pacote de idioma. Tente novamente ou continue digitando. preservando o rascunho.
31. WHERE o hook for consumido em modo local explícito (não ativo no Mentor) WHEN a instalação concluir THEN o sistema SHALL informar Pacote de idioma instalado. Você pode gravar seu ditado. sem iniciar reconhecimento automaticamente.
32. The controles de ditado SHALL ter nomes acessíveis em pt-BR, foco identificável, estados anunciados por tecnologia assistiva e alvos de toque de pelo menos 44px no mobile.
33. The bloco de ditado SHALL seguir copy e arranjo dos estados s8UGf/qsYWq/QZB2M em 1440×1058 e nxL5i/e9FXb/VC7Ro em 390×900, adaptado ao FAB e aos tokens existentes.
34. The sistema SHALL realizar zero instalações de pacote de idioma sem o gesto explícito Instalar pacote de idioma.
35. WHERE o Mentor oferecer reconhecimento browser-managed o sistema SHALL mostrar “O navegador pode usar um serviço na nuvem para reconhecer sua fala.” antes de iniciar captura.

**Independent test:** validar reconhecimento nativo em navegador/dispositivo identificado, revisar e enviar na página/FAB, inclusive por teclado. Usar Playwright CLI para jornada e capturas; um mock da API ou apenas viewport mobile não prova suporte de microfone/idioma num aparelho real. Uma indisponibilidade nativa deve resultar no fallback de digitação definido no critério34.

## Out of scope

| Excluded | Why |
| --- | --- |
| Backend de transcrição, OpenRouter ou fornecedor integrado pelo Shifu | Usuário confirmou reconhecimento nativo do navegador. |
| Upload, armazenamento, reprodução ou anexo de áudio | O usuário precisa somente do texto do ditado. |
| Bibliotecas de transcrição e modelos gerenciados pelo Shifu | A captura e o reconhecimento pertencem ao navegador, sem biblioteca/modelo ou pacote gerenciado pelo Shifu. |
| Síntese de voz e Ouvir resposta | Não compõem a entrada por ditado. |
| Envio automático e comandos de voz que executem ações | O texto exige revisão e envio explícito. |
| Implementar anexos, cota mensal ou encerramento coordenado da conta | Capacidades independentes; suas interfaces existentes não são ampliadas para realizar ditado. |
| Retomada de ditado após recarregar ou fechar | A operação é temporária. |

## Assumptions

None - todas as decisões materiais perguntadas foram resolvidas. Escolhas reversíveis de implementação seguem as convenções do repositório.

**Open questions:** none - todas resolvidas.

Decisões confirmadas nesta conversa: reconhecimento nativo browser-managed em pt-BR (substitui a decisão local anterior), hook compartilhado, texto acrescentado após quebra de linha, watchdogs de 30s/10s, instalação de idioma por gesto explícito, suporte por capacidade com digitação nos demais ambientes (Q5=A) e a posterior remoção explícita da avaliação de qualidade com amostras (revision9). Instalar não inicia gravação automaticamente.

O usuário confirmou o mecanismo nativo, não o plano anterior de OpenRouter ou seus limites. Este plano não impõe limite adicional de duração do ditado; os watchdogs cobrem início e finalização. Não há avaliação de acurácia ou exigência de amostras reconhecidas nesta feature. Os testes verificam fluxo, preservação do rascunho, limpeza e tratamento de falhas nativas.

Os checkers, Coverage e Test policy serão derivados deste documento após a revisão final aprovada; execução e evidências passam a checks.md e verification.md.

## Observable

| Surface | Decision | Landing |
| --- | --- | --- |
| Página e FAB do Mentor | Estado inicial/vazio | AC1/9; existing - Nova conversa ainda não é persistida |
| Página e FAB do Mentor | Preparação/permissão | AC2/15 |
| Página e FAB do Mentor | Gravação e controles | AC3 |
| Página e FAB do Mentor | Finalização e revisão | AC4/5/6/16 |
| Página e FAB do Mentor | Erros recuperáveis | AC12/13/14 |
| Página e FAB do Mentor | Acesso não confirmado ou alterado | AC10/19/20; existing - proteção e limpeza do contexto autenticado |
| Página e FAB do Mentor | Densidade e ordenação | AC33; cancelar à esquerda e encerrar à direita no bloco de gravação |
| Página e FAB do Mentor | Confirmação de cancelamento | n/a - descarta somente a operação temporária, preservando o rascunho |
| Página e FAB do Mentor | Navegador indisponível | AC27 |
| Página e FAB do Mentor | Instalação de idioma: gesto, carregamento, falha e sucesso | AC28/29/30/31/34 |
| Página e FAB do Mentor | Teclado, foco e anúncio de estado | AC6/32 |
| Página e FAB do Mentor | Aviso de possível processamento em nuvem | AC35 |
| Documento de qualidade | n/a - o usuário removeu explicitamente essa obrigação na revision9; nenhum documento de qualidade integra a feature |
| Coleção de anexos preparada | Agrupamento/nome/ordem/duplicados/exceções | AC18; existing - ditado não organiza ou altera a coleção |
| API/webhook | Respostas, erros, acesso, versão e rate limit | n/a - nenhuma API de ditado; envio de texto continua usando o contrato existente |
| Comando/tarefa agendada | Saída, flags, defaults, exit codes e falha parcial | n/a - nenhum comando ou job criado |

## Sources

- [SHIFU-105](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-105): id12615, Implementar ditado por áudio, parent SHIFU-29, updated 2026-10-05T18:09:38.116-03:00. Composição, revisão explícita, cancelamento e preservação; mecanismo nativo confirmado pelo usuário nesta conversa em 2026-10-13.
- [PRD Intelligence](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83099649): content83099649 v9, updated 2026-10-13T16:12:19.811Z; RP-06 principal e RP-01/03/11/12/13 relacionados, JN-01. Lido completo. A [Política de privacidade](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/100106241), content100106241 v4, updated 2026-10-08T01:07:15.769Z, permanece aplicável ao processamento de IA fornecido pelo Shifu; elegibilidade ZDR do serviço de fala gerenciado pelo navegador está fora do escopo desta feature.
- Design vinculante: design/shifu.pen, nós s8UGf/qsYWq/QZB2M e nxL5i/e9FXb/VC7Ro; componentes ihZ8z/PXcJb/puC0u. Árvore e screenshots inspecionadas pelo Pencil em 2026-10-13; arranjo/copy de ditado vinculam a feature, sem ampliar o escopo pelas capacidades representadas ao redor.

Referências técnicas: [SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition), [modo local](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally), [disponibilidade do idioma](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/available_static) , [instalação de idioma](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/install_static) e [Web Speech API](https://webaudio.github.io/web-speech-api/). São documentação da API, não prova de suporte real num navegador alvo nem de privacidade do modo remoto.


## Artifact scope

User amendment: STATE.md, lessons.json and LESSONS.md are scoped exclusively to `.specs/features/shifu-105-mentor-dictation/`, alongside this plan, checks and verification. No shared memory files under `.specs/`. This overrides the skill’s default memory placement and leaves product behavior and acceptance criteria unchanged.


Amendment revision8: aprovação humana “ok” à troca por browser-managed em 2026-10-13. AC26/27 e C26/27 revisados; AC28–31/C28–31 passam a regressões condicionais do modo local opcional do hook. Nenhuma assertion é retirada para esconder falha.


Amendment revision9 (2026-10-13): a pedido explícito do usuário, removida a avaliação das seis amostras pt-BR e o respectivo gate C34. Os resultados BLOCKED registrados nas revisions7/8 permanecem somente no histórico e não são uma obrigação ativa. Nenhum objetivo de acurácia foi acrescentado.

Amendment revision10 (2026-10-13): reconciliação com o PRD Intelligence v9 após o usuário confirmar que a elegibilidade ZDR do provedor browser-managed está fora do escopo desta feature. O PRD exige aviso prévio e informa que o Shifu não recebe nem armazena o áudio; esse modo não é mais condicionado à elegibilidade ZDR do provedor. AC35/C40 de divulgação permanece inalterado; nenhuma implementação ou prova foi alterada.
