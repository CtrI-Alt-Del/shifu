---
title: Diagnóstico inicial completo da Habilidade
status: ready
revision: 9
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-77
scope:
  - apps/server/.env.example
  - apps/server/src/shifu/app.py
  - apps/server/src/shifu/shared/core
  - apps/server/src/shifu/shared/settings.py
  - apps/server/src/shifu/learning
  - apps/server/src/shifu/curriculum
  - apps/server/migrations
  - apps/server/src/shifu/shared/database/seed_data.py
  - apps/server/tests/curriculum
  - apps/server/tests/learning
  - apps/server/tests/messaging/inngest/jobs/learning
  - apps/server/rest-client/learning
  - apps/web/src/core/learning
  - apps/web/src/constants/routes.ts
  - apps/web/src/rest/services/learning-service.ts
  - apps/web/src/ui/learning
  - apps/web/src/routes/learning
  - apps/web/tests/learning
last_updated_at: 2026-09-27
---

# 1. Context and scope

**Objetivo.** Entregar, no módulo **Learning**, o diagnóstico integral da
experiência de uma Habilidade, seu ponto de partida consolidado, a transição
para aprendizagem ou conclusão direta e um resultado consultável depois.
Origem: [SHIFU-77](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-77).
Autoridade: [PRD Learning](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB),
content ID `83066881`, versão **24** (`2026-09-27T23:21:50.838Z`), lida
integralmente após a emenda autorizada pelo usuário. O PRD Curriculum, content
ID `83034113`, versão **12**, também rege a cobertura de conteúdo diagnóstico.
Modo: **complete**.

**Situação atual e lacuna.** Há início explícito, sequência curricular,
submissão idempotente, avaliação assíncrona, observações por Conceito e
algoritmo adaptativo. Entretanto, tentativas pertencem somente à experiência:
reabrir a página retoma o próximo item. A avaliação da última resposta
consolida e publica o resultado mesmo após a saída. A página da Habilidade
oferece “Continuar diagnóstico”, não há rota própria de resultado, e o
resumo atual pode transformar ausência de evidência em zero. O caminho de
avaliação preliminar precisa impedir retorno de nota e critérios de uma
questão diagnóstica. A versão 24 do PRD determina uma política única global sem
identidade ou conjunto de parâmetros por experiência. A cobertura exigida pelo
diagnóstico pertence à autoridade de Curriculum e continua protegida pelo gate
de prontidão. Na seed de desenvolvimento, Skills incompatíveis e Goals que as
referenciam serão omitidos da estrutura construída, sem executar a seed nem
apagar conteúdo ou registros persistidos nesta entrega.

| Área | Em escopo | Fora de escopo |
| --- | --- | --- |
| Execução | Início, sequência completa em memória, um envio final atômico, reinício após interrupção, isolamento entre abas, abandono e confirmação final | Rascunho persistido; retomada de execução interrompida |
| Avaliação | Escolha única, múltipla seleção e código definidos pelo Currículo; falha, retentativa da mesma resposta e sigilo | Criar questões, rubricas, linguagem ou avaliador novos |
| Resultado | Base por Conceito e Competência, cobertura, foco, recomendação, conclusão direta e rota posterior | Nota do Objetivo; reutilização de progresso entre experiências |
| Experiência | Quadros do Pencil, pt-BR, teclado, 390 × 844 e 1440 × 900 | Redesenho do shell ou Mentor |
| Seed | Omitir da estrutura `DevelopmentSeed` Skills sem prontidão diagnóstica e Goals seed que as referenciam, junto dos registros dependentes | Executar `db:seed` no banco compartilhado, alterar catálogo já persistido ou completar Skills incompatíveis |
| Integrações | Eventos confirmados de Learning para consumidores existentes | Recompensa, regra de Gamification ou painel de análise |

| Fonte | Entrega | Delimitação |
| --- | --- | --- |
| RP-05, RP-06; JN-04 | full | Uma execução contínua por entrada; sair antes da confirmação reinicia na primeira Atividade. “Continuação” de RP-05 vale dentro da execução atual. |
| RP-07, RP-15, RP-16; JN-05, JN-18 | full | Base conceitual completa, parcial ou desconhecida; estados, domínio e foco após o diagnóstico inteiro. |
| RP-10, RP-11, RP-12, RP-13, RP-14, RP-26, RP-27; JN-21 | full para o diagnóstico | Reusar avaliação oficial e recuperação existentes; ocultar retorno individual; preservar observação inconclusiva como lacuna. |
| RP-17, RP-19, RP-28 | full para política global | Usar parâmetros globais em experiências existentes e novas; não persistir nem expor identidade/versão da política por experiência; resultados oficiais concluídos permanecem imutáveis. |
| PRD Curriculum: diagnóstico e cobertura por Conceito | confirmed | Mantém a autoridade de Curriculum e seu gate de prontidão; esta alteração filtra apenas a seed de desenvolvimento. |
| Pedido direto do usuário, 2026-09-28 | full para seed de desenvolvimento | Omitir Skills incompatíveis e Goals seed relacionados; não alterar dados persistidos. |
| RP-25 | full para estas telas | Estados e ações acessíveis em pt-BR, desktop e mobile. |

**Decisões confirmadas.** Navegar para fora, recarregar e fechar a aba
interrompem a execução; falha breve de rede com página aberta permite recuperar.
Uma nova aba inicia outra execução para a mesma experiência e invalida a
anterior, que informa a invalidação na próxima ação. O servidor só observa
abandono confirmado por chamada ou nova entrada; fechar a aba não garante
comunicação imediata. Nenhum trabalho tardio da execução abandonada pode
produzir efeito. O resultado aparece logo após confirmação, continua acessível
pela rota própria e a página habitual da Habilidade permanece a entrada normal.
A data original de início da experiência permanece única durante reinícios.
Por pedido direto posterior, o usuário percorre todas as questões e Atividades
sem envio intermediário e envia o diagnóstico inteiro uma única vez no fim.
Learning conserva uma tentativa e uma avaliação por Atividade. A navegação
continua progressiva, sem retorno a questões anteriores; respostas não enviadas
existem apenas na memória da aba e se perdem na saída ou recarga.

# 2. Implementation Contract

| ID | RP/JN | Comportamento exigido |
| --- | --- | --- |
| RF-01 | RP-05, RP-06; JN-04 | Iniciar somente por “Iniciar Habilidade” na experiência não iniciada. Cada entrada posterior antes do término cria execução nova e começa na primeira Atividade; uma segunda aba invalida a anterior. Sair informa perda do avanço. |
| RF-02 | RP-06, RP-10, RP-26; JN-04; pedido direto de envio único | Percorrer todas as Competências na ordem curricular, e em cada uma fácil, média e difícil, sem saltos por desempenho. Avançar pelas questões sem envio oficial intermediário e oferecer uma única ação final para enviar o conjunto completo. Cada Atividade recebe uma tentativa válida própria: escolha única, conjunto não vazio de múltipla seleção, ou arquivos de código aceitos pelo Currículo. |
| RF-03 | RP-06, RP-07, RP-10, RP-11, RP-12, RP-26, RP-27 | Durante e depois do diagnóstico, omitir resposta correta, nota, correção, critérios, comentários, interpretação de IA e observação individual por questão. Não oferecer material, dicas nem ajuda contextual do Mentor para o item atual. A prática de código não é nota oficial. |
| RF-04 | RP-11, RP-12, RP-13, RP-14; JN-21 | Diferenciar avaliação pendente, falha do Shifu e erro da solução. Falha obrigatória preserva a resposta e permite reavaliá-la sem novo envio; observação auxiliar inconclusiva não vira zero nem impede o fim quando a nota obrigatória é válida. |
| RF-05 | RP-05, RP-06, RP-07, RP-13, RP-27; JN-04, JN-05 | Manter tentativas, avaliações e observações diagnósticas provisórias na execução corrente. Somente a confirmação automática solicitada pela página ainda ativa após todas as avaliações obrigatórias aplica o resultado uma vez. Abandono ou substituição elimina dados provisórios quando observado pelo servidor e invalida trabalhos e comandos antigos. |
| RF-06 | RP-07, RP-15, RP-27; JN-05, JN-18 | Calcular a base de cada Conceito por média das evidências válidas de cada dificuldade, dando peso igual às dificuldades. Preservar parcialidade, dificuldades ausentes, desconhecido e zero observado; não reaplicar as observações diagnósticas no cálculo 70/30. |
| RF-07 | RP-05, RP-07, RP-15, RP-16, RP-17, RP-19, RP-28; JN-05, JN-18, JN-21 | Após confirmação, consolidar todas as Competências, inclusive bloqueadas, pelos parâmetros globais vigentes; determinar domínio estável, conteúdo liberado, primeira Competência em foco e recomendação ou lacuna de conteúdo. Concluir diretamente apenas quando todas forem dominadas e não houver verificação ou avaliação obrigatória pendente. |
| RF-08 | RP-07, RP-15, RP-19; JN-05 | Mostrar resultado consolidado imediatamente em rota autenticada e permitir retorno posterior por link na Habilidade, sem revelar itens. Na conclusão direta, preservar inicial = final e não alegar evolução. |
| RF-09 | RP-25; JN-04, JN-05 | Apresentar estados, ações e explicações em pt-BR; oferecer foco, teclado, anúncio de atualização e layout sem corte no desktop e mobile, sem depender apenas de cor. |
| RF-10 | RP-28 | Aplicar uma única política global de aprendizagem a todas as experiências existentes e novas, sem identificador ou parâmetros de política persistidos ou expostos por experiência; preservar resultados oficiais já concluídos. |
| RF-11 | PRD Curriculum RP-06; pedido direto do usuário | Omitir da estrutura de desenvolvimento as Habilidades sem prontidão diagnóstica e cada Goal seed que as referencia, junto dos registros dependentes; manter Skills compatíveis e Goals não afetados. A mudança não executa `db:seed`, não altera dados já persistidos nem remove o gate de prontidão. |

| ID | RF | Requisito | Dado | Quando | Então | Evidência esperada |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Início explícito | Habilidade não iniciada e Currículo elegível | Usuário escolhe Iniciar Habilidade | Data de início é gravada uma vez e abre a primeira Atividade; clique repetido não cria duas execuções | caso de uso, HTTP, VM-01 |
| CA-02 | RF-01, RF-05 | Reinício e invalidação | Execução com respostas enviadas, em duas abas ou após navegação/recarga | Outra entrada é iniciada | Primeira Atividade reaparece; dados anteriores não contam; aba anterior recebe mensagem ao agir | caso de uso, HTTP, Page |
| CA-03 | RF-02 | Ordem e avanço | Currículo com várias Competências e três dificuldades | Usuário avança após uma resposta válida | Próxima questão ou Competência segue a ordem completa, sem POST ou pausa de avaliação; avanço não mostra nota | Page, VM-01 |
| CA-04 | RF-02, RF-03 | Escolhas | Questão única ou múltipla | Usuário seleciona e envia | Uma opção na única, conjunto não vazio na múltipla; seleção exata vale 100, demais 0 internamente; nenhum retorno individual é exposto | caso de uso, HTTP, Page |
| CA-05 | RF-02, RF-03, RF-04 | Código | Questão de código curricular | Usuário pratica, edita e envia | Saída/erro de prática são visíveis sem nota; avaliação oficial segue rubrica e resposta enviada; falha técnica é recuperável | caso de uso, Page |
| CA-06 | RF-03 | Sigilo | Diagnóstico ativo ou concluído | Usuário ou Mentor consulta prévia, tentativa ou resultado | Prévia e detalhe individual são negados; UI mostra apenas avanço e resultado consolidado | HTTP, Page, VM-01 |
| CA-07 | RF-04, RF-05 | Pendência e reavaliação | Conjunto completo enviado, avaliação pendente ou falha | Avaliações terminam, falham ou usuário tenta novamente | Um único estado consolidado de espera; sem novo envio na pendência; retentativa usa a mesma resposta da Atividade com falha; saída antes da confirmação impede efeito tardio | caso de uso, job, HTTP |
| CA-08 | RF-05 | Confirmação única | Todas as avaliações obrigatórias concluídas na execução ativa | Página ativa confirma, inclusive sob repetição | Um resultado e eventos confirmados são persistidos; sem confirmação, nenhum progresso definitivo ou evento de conclusão | caso de uso, HTTP, job, VM-01 |
| CA-09 | RF-05 | Concorrência e isolamento | Duas abas, repetição do job ou conta distinta | Comandos chegam fora de ordem | Apenas execução/conta vigente modifica seus dados; replay não duplica efeito; outra Habilidade continua independente | caso de uso, HTTP, job |
| CA-10 | RF-06, RF-08 | Evidência parcial | Fácil inconclusivo, médio 0 e difícil 100; ou nenhuma observação numérica | Resultado é consolidado | Base parcial é 50 no primeiro caso, desconhecida no segundo; zero observado permanece zero, com cobertura explícita | caso de uso, HTTP, Page |
| CA-11 | RF-06, RF-07 | Política e aprendizagem | Diagnóstico completo com lacunas, pré-requisitos ou evidência inconclusiva | Resultado é confirmado | Foco/recomendação seguem RP-16/17, sem inventar conteúdo; tentativa de aprendizagem preenche cobertura sem repetir diagnóstico | caso de uso, HTTP, Page, VM-01 |
| CA-12 | RF-07, RF-08 | Conclusão direta | Todas as Competências dominadas e estáveis | Resultado é confirmado | Habilidade termina uma vez, resumo inicial e final coincide e apresenta Ver resumo da Habilidade | caso de uso, HTTP, Page |
| CA-13 | RF-08 | Resultado posterior | Diagnóstico já confirmado | Usuário abre a rota de resultado ou volta à Habilidade | Resultado autenticado permanece; Habilidade abre sua página habitual com acesso ao resultado | HTTP, Page, VM-01 |
| CA-14 | RF-01, RF-05, RF-08 | Autorização | IDs ausentes, malformados ou de outra conta | Qualquer operação ou rota é acessada | Não há leitura, alteração, confirmação ou inferência de resultado alheio | HTTP, Page |
| CA-15 | RF-01, RF-03, RF-09 | Acessibilidade | 1440 × 900 e 390 × 844, teclado e leitor de tela | Usuário navega, seleciona, recebe aviso e conclui | Ações operáveis, estados anunciados, foco coerente e conteúdo sem corte; ausência de evidência e foco têm texto | Page, VM-01, VM-02 |
| CA-16 | RF-10 | Política global sem versão por experiência | Experiência antiga em andamento e uma nova; experiência já concluída | Recomendações e resumos são lidos/calculados | Uma política global rege experiências não concluídas, nenhuma resposta ou DTO contém policy ID/version, e resultado oficial concluído permanece idêntico | Core, HTTP, migração |
| CA-17 | RF-11 | Seed sem Skills ou Goals incompatíveis | Seed de desenvolvimento com Skills sem cobertura e Goals que as referenciam | A seed é construída | Permanecem as Skills prontas “Decisões em algoritmos” e “Laboratório de decisões adaptativas”; os Goals “Laboratório de progresso adaptativo” e “Testar diagnóstico inicial” permanecem. Saem as 8 Skills incompletas (“Lógica de programação”, “Python essencial”, “Estruturas de dados”, “Algoritmos de busca”, “Modelagem de dados”, “APIs web”, “Testes automatizados” e “Projeto integrador”), os Goals “Aprender a programar” e “Mapa de desenvolvimento de software” e todos os registros seed dependentes. Nenhum dado persistido é removido. | Auditoria da estrutura `DevelopmentSeed` e gate curricular existente |
| CA-18 | RF-02, RF-05 | Envio único atômico | Todas as questões da execução atual respondidas | Usuário escolhe Enviar diagnóstico uma vez ou repete o pedido por falha de rede | Uma operação grava uma tentativa e avaliação por Atividade, na ordem curricular, ou nenhuma; repetição idêntica devolve a mesma execução sem duplicar tentativa/evento | caso de uso, HTTP, Page, VM-01 |
| CA-19 | RF-02, RF-05 | Conjunto inválido | Falta resposta, revisão mudou, atividade extra ou outra conta/execução | Usuário tenta enviar o conjunto | Nada é gravado nem avaliado; a interface conserva respostas em memória na aba ativa para correção quando recuperável | caso de uso, HTTP, Page |
| CA-20 | RF-02, RF-03 | Uma avaliação após o envio final | Conjunto aceito | Avaliações assíncronas terminam | Somente um estado de espera após o envio final e um resultado consolidado; nenhum feedback ou retorno individual é exposto | job, HTTP, Page |

**Restrições transversais.** Excluir uma execução afeta somente tentativas
diagnósticas dessa experiência, avaliações e observações dependentes; não
remove aprendizagem, revisão, outra Habilidade ou fatos confirmados. Nenhuma
resposta pendente vira rascunho. Observações individuais continuam internas a
Learning; o Mentor recebe somente contexto consolidado permitido. Eventos de
diagnóstico e conclusão são publicados apenas na transação de confirmação.
A política adaptativa é global e única. Experiências não carregam nem expõem
identificadores ou versões de política; resultados já concluídos não são
recalculados.

## Design Contract

O [handoff visual](./design/handoff.md) contém o inventário dos dez quadros do
Pencil, capturas salvas, estados e ambiguidades. A superfície de Atividade usa
a rota existente e seus widgets de escolha/código; o resultado usa
`/learning/goals/$goalId/skills/$skillId/diagnostic/result`. Os quadros de
origem medem 1440 × 900; a validação adicional usa 390 × 844 com o mesmo
conteúdo essencial. Confirmação de saída, pendência oficial, invalidação por
outra aba, carregamento e recuperação seguem PRD e `documentation/design.md`.
O exemplo Python e os números ilustrativos não restringem o Currículo. No
quadro `zaJXn`, ignorar marcadores ilustrativos de foco e bloqueio quando
todas as Competências estão dominadas. Usar tokens existentes e estados
acessíveis; cor isolada não comunica seleção, progresso ou erro.
Na entrega, a validação visual abrange somente o caminho feliz: comparar
capturas frescas da seleção diagnóstica e do resultado normal em 1440 × 900
(VM-01), e dessas duas superfícies em
390 × 844 (VM-02). Os demais quadros continuam referências de implementação;
seus estados são cobertos por testes automatizados e não exigem captura manual
própria para concluir esta revisão.

# 3. Technical Contract

## Estado técnico e delta

CodeGraph consultado em 2026-09-27: `How does a skill diagnostic start, select
current activity, record attempts, evaluate asynchronously, and finalize a skill
experience?`, `Which SkillPage and ActivityPage widgets, hooks, routes and REST
services own diagnosis navigation, submission, leave handling, and result
display?`, e `How are diagnostic concept observations, competency and skill
progress summaries, learning recommendations, and SkillExperienceDetail computed
and persisted?`. As consultas localizaram a sequência, o job, os consumidores
web e o cálculo adaptativo; a fonte retornada foi inspecionada antes dos
caminhos delimitados abaixo. `.codegraph/` existe e funcionou.

| Evidência atual | Responsabilidade | Lacuna |
| --- | --- | --- |
| `StartSkillUseCase`, `SkillExperience`, `GetDiagnosticUseCase`, `DiagnosticSequence` | Iniciar uma vez e escolher próximo item por tentativas da experiência | Não identificam execução; reentrada retoma |
| `SubmitChoiceActivityUseCase`, `ActivityAttempt`, `RetryChoiceEvaluationUseCase` | Envio idempotente e retentativa de avaliação | Não vinculam comandos à execução vigente |
| `EvaluateChoiceActivityUseCase`, `EvaluateChoiceActivityJob` | Nota, observação, efeitos e eventos | Último job confirma mesmo após saída |
| `GetChoiceAttemptUseCase`, `PreviewActivityQuestionFeedbackUseCase` | Detalhe da tentativa e prévia | Detalhe diagnóstico já é negado; prévia deve ser explicitamente vedada |
| `AdaptiveLearningPolicy`, `ConceptObservation`, `ConceptState` | Base conceitual, cobertura, domínio e recomendação | Política reutilizável; aplicar só na confirmação e projetar parcialidade no resultado |
| `GetSkillExperienceDetailUseCase`, `SkillExperienceDetail` | Resumo da Habilidade | Ausência vira zero em alguns campos; não expõe cobertura geral ou motivo/gap da recomendação |
| `SkillPage`, `ActivityPage`, `learning-service.ts` | Navegação e REST autenticado | “Continuar diagnóstico”, prévia em fluxo misto e nenhum resultado dedicado |

`apps/web` usa React 19, TanStack Start/Router, React Query e Playwright; `apps/server`
usa FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic e Inngest. O índice de
rotas é gerado por `pnpm --filter web generate-routes`. O `run_id` já existente
em `ActivityEvaluation` identifica a **tentativa de avaliação** para retry;
não representa uma execução do diagnóstico.

## Solução e garantias de runtime

Learning mantém um identificador de execução por `SkillExperience` e o grava
em cada tentativa diagnóstica. O navegador cria uma chave UUID por entrada e
a guarda somente na memória da aba, associada a `goalId`/`skillId`; ela se perde
na recarga e não é credencial de autenticação. A mesma chave repetida no
`POST /start` é idempotente. Uma chave nova, sob bloqueio da linha da
experiência, exclui as tentativas provisórias anteriores e dependentes por
cascata, define a execução ativa e começa na primeira Atividade. A experiência
permanece `diagnosing`, e `started_at` não muda. Uma aba anterior recebe
`409` com o código compartilhado `conflict` na próxima chamada; a web consulta
`GET /diagnostic` com a mesma chave: outro `409` confirma execução substituída,
enquanto `200` indica outro conflito recuperável. Só no primeiro caso explica
o reinício.

`GET /diagnostic` sem chave durante `diagnosing` informa apenas que uma nova
entrada é necessária. Com chave vigente, fornece a sequência ordenada completa
de IDs de Competência/Atividade e, após o envio único, pendência e, quando
todos os itens estiverem avaliados, `readyToComplete`; não fornece notas.
Antes do envio, GET de Atividade diagnóstica permite qualquer item dessa
sequência na execução vigente para a página percorrê-la sem gravar tentativas.
Cada GET de Atividade, envio e retry diagnóstico exige essa mesma chave.
O POST individual de tentativa rejeita Atividade diagnóstica; permanece igual
para aprendizagem e revisão.

A página consulta a sequência antes do envio, guarda as respostas somente em
memória da aba, na ordem curricular e sem retorno a uma questão anterior.
Ao terminar uma Atividade que não é a última, registra suas respostas na
sessão em memória e navega diretamente à próxima rota de Atividade; a
`ActivityPage` carrega o próximo item sem consultar avaliação nem mostrar uma
tela de pausa. No último item, a ação Enviar diagnóstico
chama uma única vez `POST /diagnostic/submissions` com UUID de idempotência,
`diagnostic_revision` obrigatória e respostas de cada Atividade. Os snapshots
curriculares de escolha e de código expõem o mesmo campo opaco
`diagnostic_revision`. O provider do Currículo calcula HMAC-SHA-256 sobre uma
serialização canônica e determinística do conteúdo que afeta a avaliação de
cada tipo: enunciados, opções e gabarito/rubrica de escolha; enunciados,
arquivos, limites, entrypoint, dependências fixas e comandos permitidos de
código, rubrica e configuração do avaliador de código; em ambos, pesos e
relações conceituais. Learning compara cada revisão recebida com a revisão do
snapshot vigente antes de gravar;
uma alteração desde a leitura gera 409 sem efeito parcial. O GET expõe apenas
o token opaco, nunca o hash simples, gabarito ou rubrica. A chave HMAC é
exclusiva do servidor, estável entre instâncias e injetada por configuração;
rotação invalida envios abertos com 409 e não muda snapshots já avaliados.
Learning autoriza a experiência e
a execução, confere que o conjunto corresponde exatamente à sequência
curricular vigente, valida cada resposta pelo snapshot e, sob bloqueio da
experiência, grava uma tentativa, uma avaliação pendente e um evento de
avaliação por Atividade na **mesma transação**. Nenhum evento é publicado se
qualquer item falhar. A chave UUID de lote não ocupa diretamente o índice único
existente de `ActivityAttempt`: cada tentativa usa `UUIDv5(namespace=UUID do
lote, name=activity_id)` como `submission_key`. No replay, Learning deriva
todas as chaves, exige o conjunto inteiro da mesma execução e compara
identidade, revisão e respostas normalizadas com os snapshots salvos antes de
retornar as tentativas existentes. Não é necessária uma tabela nova de lote.
Uma repetição idêntica da mesma chave devolve as mesmas tentativas;
chave repetida com conteúdo diferente, conjunto parcial ou
execução vencida retorna 409. Depois do commit, a página acompanha somente o
estado agregado, sem pausa ou feedback entre Atividades. Falha de avaliação
permite retry da tentativa preservada; só então a confirmação existente ocorre.
Respostas de aprendizagem/revisão não a usam. Navegação confirmada para fora
chama abandono; `beforeunload` avisa e a web tenta comunicar a saída, mas
fechamento/recarga não garantem entrega. Nesses casos, a chave se perde e a
próxima entrada substitui e exclui a execução antiga. Até essa entrada,
qualquer avaliação tardia é apenas provisória e não publica progresso/evento.

O job verifica a tentativa de avaliação (`ActivityEvaluation.run_id`) e a
execução diagnóstica vigente, inclusive depois do avaliador externo e sob o
bloqueio da experiência. Na execução vigente, persiste avaliação e observações
por Conceito, sem progresso, conclusão nem evento de resultado. Falha técnica
marca somente a avaliação vigente; retry reavalia a resposta imutável.
Quando o GET sinaliza `readyToComplete`, a página ativa chama automaticamente
`POST /diagnostic/complete`. Esse caso de uso bloqueia a experiência, valida
que todas as Atividades curriculares têm uma avaliação oficial concluída na
execução atual e nenhuma pendência obrigatória, calcula a política adaptativa,
grava estados, progresso e resumo, muda a etapa e adiciona os eventos ao outbox
na **mesma transação**. Repetir a confirmação da mesma execução devolve o
resultado já fixado, sem novo evento; chamada antiga/incompleta retorna 409.
O navegador navega para a rota de resultado apenas após sucesso confirmado.

Autorização usa a conta da sessão autenticada em todos os controladores,
associando Objetivo, Habilidade, experiência, tentativa e execução antes de
qualquer leitura ou mutação. IDs de outra conta/experiência devolvem 404;
chave de execução desatualizada devolve 409 apenas depois de autorizar a
experiência. Dados de envio e avaliação jamais vão para URLs, logs de UI ou
contexto do Mentor. Falha de rede na confirmação conserva o estado provisório
para retry pela página aberta; se ela sair, novo início o descarta.
`ConflictError` usa o tradutor global existente (`code: conflict`); a web
identifica execução vencida pela reconsulta, sem depender de novo código HTTP.

| Fronteira | Produtor | Consumidor | Contrato | Garantia e erro |
| --- | --- | --- | --- | --- |
| Sessão da aba → REST | Skill/Diagnostic Page via `LearningService` | Controladores Learning | `entry_key` UUID em `/start`; `X-Diagnostic-Run-Id` UUID nos demais pedidos diagnósticos; UUID do envio final | Sem armazenamento persistente; 409 para execução vencida |
| REST → Core | Controladores | Casos de uso Learning | `account_id`, IDs curriculares, `diagnostic_run_id` e dados tipados | 401 sem sessão, 404 para escopo alheio, 409 para estado incompatível |
| Core → DB | Casos de uso | `LearningDatabase` e repositórios | `SkillExperience.diagnostic_run_id`, `ActivityAttempt.diagnostic_run_id` | Bloqueio de experiência, commit único, exclusão em cascata |
| Outbox → job | `SubmitDiagnosticUseCase` | `EvaluateChoiceActivityJob` | Um evento existente `learning/activity-submission.requested` por Atividade; `run_id` de avaliação | Eventos gravados no commit atômico; revalidação da execução antes de gravar |
| Core → outbox | `CompleteDiagnosticUseCase` | consumidores existentes | Eventos atuais `DiagnosticCompletedEvent`, `SkillCompletedEvent` quando cabível | Uma publicação após confirmação; replay sem duplicação |
| REST → web | GET `/diagnostic` e GET Habilidade | Resultado e Skill Page | valores numéricos ou `null`, cobertura, foco e recomendação | Ausência não serializa como zero; nenhum item individual |

## Contratos das camadas afetadas

### Domain e estruturas

| Caminho | Mudança | Declaração e esquema final | Garantias e consumidores | Teste/geração |
| --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/core/domain/entities/skill_experience.py` | Modify | `SkillExperience`: `id`, `goal_id`, `skill_id`, `inclusion_reason`, `status`, `created_at`, `updated_at`, `started_at?`, `completed_at?`, `completion_summary?`, `recommended_concept_id?`, **`diagnostic_run_id?` UUID**; transições de início, substituição, abandono e confirmação | Sem campo de versão/política; ID de execução permanece para replay idempotente; `started_at`/`completed_at` únicos | casos de uso |
| `apps/server/src/shifu/learning/core/domain/adaptive_learning_policy.py` | Modify | `AdaptiveLearningPolicy` | Única política global; remover `policy_id` e branches de compatibilidade/versionamento; experiências não selecionam parâmetros | casos de uso |
| `apps/server/src/shifu/learning/core/domain/structures/goal_skill_detail.py` | Modify | `GoalSkillDetail` | Remover `policy_id`; status e conteúdo curricular permanecem | controladores |
| `apps/server/src/shifu/learning/rest/controllers/get_goal_controller.py` | Modify | `SkillResponse` | Remover `policyId` de todas as respostas de Objetivo | HTTP |
| `apps/server/src/shifu/learning/rest/controllers/get_goal_detail_controller.py` | Modify | resposta de detalhe | Remover `policyId` de todos os DTOs de Habilidade | HTTP |
| `apps/server/src/shifu/learning/core/domain/entities/activity_attempt.py` | Modify | `ActivityAttempt`: `id`, `skill_experience_id`, `competency_id`, `activity_id`, `kind`, `answers`, `submitted_at`, `submission_key?`, `grading_snapshot?`, **`diagnostic_run_id?` UUID** | Não nulo para novas tentativas diagnósticas; nulo para aprendizagem, revisão e legado | casos de uso |
| `apps/server/src/shifu/learning/core/domain/structures/diagnostic_overview.py` | Modify | `DiagnosticOverview`: campos atuais mais `activity_sequence` de pares ordenados Competência/Atividade | Em diagnóstico sem chave, nenhum item; na execução ativa, sequência sem nota; resumo só em `settled` | HTTP |
| `apps/server/src/shifu/learning/core/domain/structures/diagnostic_competency_summary.py` | Modify | `DiagnosticCompetencySummary`: `competency_id`, `competency_name`, `position`, `progress?`, `coverage_complete`, `status`, `is_focus`, `content_released` | `progress=null` indica desconhecido, valor conhecido com `coverage_complete=false` é parcial | HTTP |
| `apps/server/src/shifu/learning/core/domain/structures/skill_experience_detail.py` | Modify | `SkillExperienceDetail`: campos atuais `goal_id`, `skill_id`, `skill_name`, `skill_status`, `focus_competency_id?`, `focus_competency_name?`, `competencies`, `recommendation?`, `evaluation?`; `overall_result?`, `overall_coverage_complete`, `recommendation_gap?` | Média completa apenas com todas as Competências completas | Skill Page |
| `apps/server/src/shifu/learning/core/domain/structures/skill_competency_summary.py` | Modify | `SkillCompetencySummary`: `competency_id`, `competency_name`, `position`, `progress?`, `coverage_complete`, `status`, `availability`, `is_focus` | `null`, parcial e zero distintos | Skill Page |
| `apps/server/src/shifu/learning/core/domain/structures/skill_recommendation.py` | Modify | `SkillRecommendation`: campos atuais de Competência/Atividade/dificuldade/tipo, mais `reason`, `target_concept_name?`, `material_id?`, `gap?` | Explica decisão da política; material opcional não bloqueia Atividade | Skill/Result Page |
| `apps/server/src/shifu/learning/core/domain/structures/concept_completion_summary.py` | Create | `ConceptCompletionSummary`: `concept_id`, `initial_progress?`, `final_progress`, `initial_observed_difficulties`, `final_observed_difficulties` | Snapshot consolidado sem resposta individual | resumo preservado |
| `apps/server/src/shifu/learning/core/domain/structures/competency_completion_summary.py` | Modify | `CompetencyCompletionSummary`: `competency_id`, `initial_progress?`, `initial_coverage_complete`, `final_progress`, `concepts` | Não alegar evolução completa de base parcial | resumo preservado |
| `apps/server/src/shifu/learning/core/domain/structures/skill_completion_summary.py` | Modify | `SkillCompletionSummary`: `competencies`, `initial_progress?`, `initial_coverage_complete`, `final_progress`, `started_at`, `completed_at` | Conclusão direta guarda inicial = final; snapshots antigos desserializam com padrões de compatibilidade | resumo preservado |
| `apps/server/src/shifu/learning/core/domain/structures/__init__.py` | Modify | Exportar `ConceptCompletionSummary` e estruturas alteradas | Sem dependência de infraestrutura | imports Core |

### Use cases e Interfaces

| Caminho | Mudança | Declaração/operação | Contrato e dependências | Teste |
| --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/core/use_cases/start_skill_use_case.py` | Modify | `StartSkillUseCase.execute(account, goal, skill, entry_key)` | Idempotência por chave; lock, primeira entrada ou substituição e exclusão provisória na mesma transação; rejeita experiência concluída/learning e Currículo inelegível | `test_start_skill_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/abandon_diagnostic_use_case.py` | Create | `AbandonDiagnosticUseCase.execute(account, goal, skill, run_id)` | Lock; se vigente, excluir provisórios e limpar ID; se outra execução, 409 sem tocar nela | `test_abandon_diagnostic_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/complete_diagnostic_use_case.py` | Create | `CompleteDiagnosticUseCase.execute(account, goal, skill, run_id)` | Verificação integral, política, estados, resumo, transição e outbox em transação; replay da mesma confirmação não duplica | `test_complete_diagnostic_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/get_diagnostic_use_case.py` | Modify | `GetDiagnosticUseCase.execute(..., run_id?)` | Estado sem entrada, andamento/pending/ready ou resumo confirmado; timeout vigente sem criar nota | `test_get_diagnostic_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/diagnostic_sequence.py` | Modify | `DiagnosticSequence.ordered/next_item` | Contar somente tentativas da execução ativa; três dificuldades e todas as Competências | `test_get_diagnostic_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/get_choice_activity_use_case.py` | Modify | `GetChoiceActivityUseCase.execute(..., run_id?)` | Antes do envio final, autorizar qualquer item da sequência na execução vigente; obter código diagnóstico pelo port curricular novo e ocultar critérios/rubrica na projeção pública; não servir item de aba vencida | `test_get_choice_activity_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/submit_choice_activity_use_case.py` | Modify | `SubmitChoiceActivityUseCase.execute(..., run_id?)` | Rejeitar envio diagnóstico individual; aprendizagem/revisão conservam replay e bloqueio por avaliação pendente | `test_submit_choice_activity_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/submit_diagnostic_batch_use_case.py` | Create | `SubmitDiagnosticBatchUseCase.execute(account, goal, skill, run_id, submission_key, items)` | Conferir conjunto completo, ordem, snapshots curriculares de escolha ou código e respostas; bloquear experiência; gravar todos os pares tentativa/avaliação/evento no mesmo commit; replay idêntico sem duplicação; avaliador atual consome o snapshot imutável salvo | caso de uso, HTTP |
| `apps/server/src/shifu/learning/core/use_cases/retry_choice_evaluation_use_case.py` | Modify | `RetryChoiceEvaluationUseCase.execute(..., run_id?)` | Retry diagnóstico só na execução vigente e com mesma resposta; avaliação ganha novo `run_id` próprio | `test_retry_choice_evaluation_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/evaluate_choice_activity_use_case.py` | Modify | `EvaluateChoiceActivityUseCase.execute` | Job diagnóstico salva apenas avaliação/observação provisória após conferir execução; extrair aplicação final para confirmação; todas as experiências não concluídas usam a política global | `test_evaluate_choice_activity_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/preview_activity_question_feedback_use_case.py` | Modify | `PreviewActivityQuestionFeedbackUseCase.execute` | Negar questão diagnóstica antes de chamar avaliador; não devolver score/critérios | `test_preview_activity_question_feedback_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/get_skill_experience_detail_use_case.py` | Modify | `GetSkillExperienceDetailUseCase.execute` | Projetar nulo/parcial/cobertura e motivo/gap pela política, sem zero fictício | `test_get_skill_experience_detail_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/get_goal_use_case.py` | Modify | projeção de Objetivos | Não incluir identidade de política nas Habilidades retornadas | teste HTTP de GET de Objetivo |
| `apps/server/src/shifu/learning/core/use_cases/get_goal_detail_use_case.py` | Modify | `GetGoalDetailUseCase._to_skill_detail` | Projetar somente dados curriculares e progresso; sem `policy_id` | `test_get_goal_detail_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/get_choice_attempt_use_case.py` | Modify | projeção de tentativa | Remover branches de versão por experiência; manter sigilo diagnóstico e contrato de tentativa | `test_get_choice_attempt_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/get_competency_detail_use_case.py` | Modify | seleção da política de progresso | Aplicar política global sem consultar a experiência | `test_get_competency_detail_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/__init__.py` | Modify | Exportar novos casos de uso | Usado pelos controladores, sem instanciar infraestrutura no Core | imports REST |
| `apps/server/src/shifu/learning/core/interfaces/activity_attempts_repository.py` | Modify | `remove_diagnostic_by_experience(experience_id)`, busca por execução | Exclusão delimitada; dependentes via FK, sem `commit` no repositório | casos de uso/HTTP |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_skill_snapshot.py` | Modify | `CurriculumSkillSnapshot.diagnostic_coverage_gaps` e `diagnostic_ready` | Nomes sem versionamento; prontidão exige competências e cobertura válida | Curriculum provider e Learning |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_learning_activity_snapshot.py` | Modify | `CurriculumLearningActivitySnapshot.diagnostic_revision` | Aceitar `activity_type=diagnostic` com uma ou mais questões e rubrica válida; carregar token opaco obrigatório para novo diagnóstico de código; preservar exigência de 3–5 questões para `learning`; snapshot continua privado e imutável | provider, Learning |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_choice_activity_snapshot.py` | Modify | `CurriculumChoiceActivitySnapshot.diagnostic_revision` | Mesmo campo e semântica do snapshot de código: token opaco obrigatório para novo diagnóstico de escolha, calculado pelo provider; ausente apenas em snapshots históricos | provider, Learning |
| `apps/server/src/shifu/shared/settings.py` | Modify | `Settings.diagnostic_revision_hmac_key` | Segredo servidor obrigatório para oferecer diagnóstico; nunca serializar ou registrar; valor estável entre instâncias | composição |
| `apps/server/.env.example` | Modify | `DIAGNOSTIC_REVISION_HMAC_KEY` | Documentar geração de segredo aleatório forte para ambientes; nenhum segredo real no Git | operação |
| `apps/server/src/shifu/app.py` | Modify | composição do `DatabaseCurriculumContentProvider` | Injetar chave por configuração sem expô-la a Learning ou HTTP; falhar fechado se ausente | composição |
| `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py` | Modify | `CurriculumContentProvider.get_diagnostic_activity(activity_id)` | Retorna snapshot privado misto de escolha/código somente para Activity diagnóstica, inclusive revisão e rubrica, ou `None`; Learning nunca lê entidade Curriculum diretamente | provider e use cases |
| `apps/server/src/shifu/curriculum/core/domain/structures/diagnostic_coverage.py` | Rename/Modify | validador de prontidão curricular | Cobertura diagnóstica completa, avaliador confiável, relações válidas e integridade curricular; gaps determinísticos | domínio Curriculum |
| `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Modify | montar snapshot, validar Skill e implementar `get_diagnostic_activity` | Serializar conteúdo canonicamente e gerar revisão diagnóstica com HMAC-SHA-256; snapshot misto diagnóstico inclui código/rubrica; `get_learning_activity` continua restrito à aprendizagem; conteúdo ausente não é elegível silenciosamente | Curriculum provider |
| `apps/server/src/shifu/learning/core/use_cases/{create_goal_use_case.py,list_available_skills_use_case.py,start_skill_use_case.py,get_diagnostic_use_case.py,complete_diagnostic_use_case.py,get_choice_activity_use_case.py,submit_choice_activity_use_case.py,choice_evidence_eligibility.py}` | Modify | verificações de entrada e evidência | Referenciar `diagnostic_ready`; preservar gate de prontidão curricular | casos de uso |
| `apps/server/src/shifu/learning/core/use_cases/{evaluate_choice_activity_use_case.py,retry_choice_evaluation_use_case.py}` | Modify | avaliação e reavaliação | Aplicar política global às experiências não concluídas e não consultar identidade persistida de política | suítes de avaliação e retry |
| `apps/server/src/shifu/shared/database/seed_data.py` | Modify | filtrar Skills incompatíveis e Goals dependentes na estrutura `DevelopmentSeed` | Remover 8 Skills sem Conceitos e os Goals seed `Aprender a programar` e `Mapa de desenvolvimento de software`, junto de todos os registros seed dependentes; manter as 2 Skills prontas e os Goals `Laboratório de progresso adaptativo` e `Testar diagnóstico inicial`; nenhuma mutação em banco | auditoria explícita do resultado seed |

`build_development_seed()` apenas constrói dados em memória. O comando
`db:seed` chama `SeedOrchestrator.clear()` antes de gravar e, portanto, é
destrutivo para dados persistidos no banco escolhido. Esta entrega não executa
`db:seed` no banco compartilhado; uma eventual validação de gravação usa
somente banco descartável e exige autorização de teste aplicável.

### Database e Messaging

| Caminho | Mudança | Declaração/operação | Contrato e dependências | Teste/geração |
| --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/database/sqlalchemy/models/skill_experience_model.py` | Modify | `SkillExperienceModel.diagnostic_run_id` | `VARCHAR(36) NULL`; remover a coluna ORM `policy_id`; linha bloqueada pelo repositório existente para serializar entradas e confirmação | migração |
| `apps/server/src/shifu/learning/database/sqlalchemy/models/activity_attempt_model.py` | Modify | `ActivityAttemptModel.diagnostic_run_id` | `VARCHAR(36) NULL`, índice por experiência/execução/tipo; FK da experiência já existente | migração |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/skill_experience_mapper.py` | Modify | `SkillExperienceMapper` | Leitura/gravação do ID nullable, inclusive registros anteriores; não ler nem gravar `policy_id` | casos de uso |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py` | Modify | `ActivityAttemptMapper` | Leitura/gravação do ID nullable sem alterar snapshots curriculares ou respostas | casos de uso |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/activity_attempts_repository.py` | Modify | `SqlalchemyActivityAttemptsRepository.remove_diagnostic_by_experience` e consulta delimitada | `DELETE` apenas `kind=diagnostic` daquela experiência; cascata apaga avaliações e observações; flush antes de reutilizar chave de envio | HTTP integrado |
| `apps/server/migrations/versions/e7d45a1b9c02_isolate_learning_diagnostic_runs.py` | Create | Alembic `revision=e7d45a1b9c02`, `down_revision=c9e4f6a7b8c1` | Colunas e índice de execução diagnóstica; antigas experiências `diagnosing` reiniciam na próxima entrada | migração em BD descartável |
| `apps/server/migrations/versions/e8d45a1b9c03_remove_skill_experience_policy_id.py` | Create | Alembic `revision=e8d45a1b9c03`, `down_revision=e7d45a1b9c02` | Remover somente `learning_skill_experiences.policy_id`; preservar linhas e resumos; downgrade recria coluna default sem restaurar valores antigos | migração em BD descartável |
| `apps/server/src/shifu/learning/messaging/inngest/jobs/evaluate_choice_activity_job.py` | Modify | `EvaluateChoiceActivityJob._is_current_sync/_mark_failed_sync` | Conferir também o ID da execução da tentativa contra o da experiência; sem efeito para evento apagado/vencido, inclusive no callback de falha | `test_evaluate_choice_activity_job.py` |

### Testes do servidor

Cada caso de uso e controlador novo ou alterado tem sua suíte espelhada. Os
cenários válidos das suítes agregadas antigas migram para seus donos antes da
remoção dessas suítes.

| Caminho | Mudança | Declaração/operação | Contrato e garantias | Teste/geração |
| --- | --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_start_skill_use_case.py` | Create | `TestStartSkillUseCase` | Entrada idempotente, reinício e isolamento sob lock | unit |
| `apps/server/tests/learning/core/use_cases/test_abandon_diagnostic_use_case.py` | Create | `TestAbandonDiagnosticUseCase` | Exclusão delimitada e rejeição de chave vencida | unit |
| `apps/server/tests/learning/core/use_cases/test_complete_diagnostic_use_case.py` | Create | `TestCompleteDiagnosticUseCase` | Cobertura, confirmação única, resumo e outbox | unit |
| `apps/server/tests/learning/core/use_cases/test_get_diagnostic_use_case.py` | Create | `TestGetDiagnosticUseCase` | Entrada necessária, sequência ordenada, pendência e confirmação pronta | unit |
| `apps/server/tests/learning/core/use_cases/test_create_goal_use_case.py` | Create | `TestCreateGoalUseCase` | Seleção de Skill diagnóstica pronta e erro para conteúdo curricular incompleto | unit |
| `apps/server/tests/curriculum/core/domain/test_diagnostic_coverage.py` | Rename/Modify | validador existente de prontidão de Habilidade | Preservar os cenários existentes; rejeitar gaps sem rótulo de versão | unit |
| `apps/server/tests/learning/server/controllers/test_get_goal_controller.py` | Create | resposta de Habilidade no Objetivo | Ausência de `policyId` e contrato sem versão | HTTP |
| `apps/server/tests/learning/server/controllers/test_get_goal_detail_controller.py` | Modify | resposta detalhada das Habilidades do Objetivo | Ausência de `policyId` nos DTOs da resposta | HTTP integration |
| `apps/server/tests/learning/core/use_cases/test_get_competency_detail_use_case.py` | Modify | `TestGetCompetencyDetailUseCase` | Preservar cenário de alvo viável e progresso desconhecido | unit |
| `apps/server/tests/learning/core/use_cases/test_adaptive_diagnostic_flow.py` | Remove | suíte agregada antiga | Migrar cenários vigentes para suítes espelhadas; descartar asserções que exigem conclusão pelo job | nenhuma perda de cobertura válida |
| `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | Modify | `TestSubmitChoiceActivityUseCase` | Envio por execução e replay | unit |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | Modify | `TestEvaluateChoiceActivityUseCase` | Avaliação provisória e nenhum efeito tardio | unit |
| `apps/server/tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py` | Modify | `TestRetryChoiceEvaluationUseCase` | Retry da mesma resposta vigente | unit |
| `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | Modify | `TestGetChoiceActivityUseCase` | Item da execução vigente | unit |
| `apps/server/tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py` | Modify | `TestPreviewActivityQuestionFeedbackUseCase` | Prévia diagnóstica negada | unit |
| `apps/server/tests/learning/core/use_cases/test_get_skill_experience_detail_use_case.py` | Modify | `TestGetSkillExperienceDetailUseCase` | Resumo parcial, nulo e recomendação | unit |
| `apps/server/tests/learning/server/controllers/test_start_skill_controller.py` | Create | `TestStartSkillController` | Entrada HTTP, autorização, persistência e 409 | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_abandon_diagnostic_controller.py` | Create | `TestAbandonDiagnosticController` | Abandono HTTP e exclusão no banco | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_complete_diagnostic_controller.py` | Create | `TestCompleteDiagnosticController` | Confirmação HTTP, outbox e replay | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_get_diagnostic_controller.py` | Create | `TestGetDiagnosticController` | Leitura HTTP com/sem chave e conta | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_adaptive_journey_controller.py` | Remove | suíte agregada antiga | Migrar asserções vigentes para controladores espelhados; preparação de Objetivo vira fixture | nenhuma perda de cobertura válida |
| `apps/server/tests/learning/server/controllers/test_get_competency_detail_controller.py` | Modify | `TestGetCompetencyDetailController` | Preservar fluxo de duas Competências, aprendizagem e recomendação após diagnóstico | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py` | Modify | `TestGetChoiceActivityController` | Header e sigilo | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py` | Modify | `TestSubmitChoiceActivityController` | Envio, replay e escopo | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_retry_choice_evaluation_controller.py` | Modify | `TestRetryChoiceEvaluationController` | Retry e chave vencida | HTTP integration |
| `apps/server/tests/learning/server/controllers/test_get_skill_experience_detail_controller.py` | Modify | `TestGetSkillExperienceDetailController` | Campos nullable e cobertura | HTTP integration |
| `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | Modify | `TestEvaluateChoiceActivityJob` | Evento antigo, falha e execução vigente | job integration |

Na remoção das suítes agregadas, preservar os nove cenários Core vigentes:
criação do Objetivo em `test_create_goal_use_case.py`; recusa de início em
`test_start_skill_use_case.py`; pendência, ordem e sigilo em
`test_get_diagnostic_use_case.py`; retry da mesma resposta em
`test_retry_choice_evaluation_use_case.py`; alvo viável em
`test_get_competency_detail_use_case.py`; rubrica congelada e avaliação
provisória em `test_evaluate_choice_activity_use_case.py`; avaliação de
revisão em `test_evaluate_choice_activity_job.py`. A conclusão antes feita
pelo último job muda para `test_complete_diagnostic_use_case.py`. Migrar as
asserções HTTP ainda válidas de `test_adaptive_journey_controller.py` para as
quatro suítes espelhadas do ciclo diagnóstico. O segundo cenário, que continua
pela aprendizagem e recomendação em duas Competências, preserva asserções em
`test_get_competency_detail_controller.py` e
`test_get_skill_experience_detail_controller.py`; os pedidos de criação e
listagem de Objetivo servem como preparação, sem reintroduzir teste misto.

**Migração.** Adicionar `learning_skill_experiences.diagnostic_run_id
VARCHAR(36) NULL` e `learning_activity_attempts.diagnostic_run_id VARCHAR(36)
NULL`; criar `ix_learning_attempt_experience_diagnostic_run_kind` em
`(skill_experience_id, diagnostic_run_id, kind)`. Nenhuma nova tabela ou FK é
necessária. As FKs existentes de `learning_activity_evaluations` e
`learning_concept_observations` para `learning_activity_attempts` têm
`ON DELETE CASCADE`; a exclusão é atômica na transação do caso de uso.
Dados anteriores permanecem com `NULL`; tentativas diagnósticas de uma
experiência antiga ainda `diagnosing` são removidas na primeira nova entrada.
O novo job não pode aplicar efeitos de tentativa diagnóstica sem ID vigente.
O downgrade remove índice e colunas somente com processos parados e sem
execução diagnóstica ativa; não preserva o isolamento de execução em um binário
antigo. Uma migração adicional remove `policy_id`, sem excluir experiências ou
`completion_summary`; snapshots de conclusão são preservados e valores antigos
de ID de política são descartados. O downgrade recria a coluna com o default
histórico, sem recuperar os IDs apagados. Validar a cadeia completa em banco
descartável, sem resetar dados compartilhados.

### REST e Composition do servidor

| Caminho | Mudança | Declaração/operação | Contrato e garantias | Teste/registro |
| --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/rest/controllers/start_skill_controller.py` | Modify | `StartSkillController` | `POST /learning/goals/{goal_id}/skills/{skill_id}/start`, corpo `{entry_key: UUID}`, 200 `{status:"diagnosing",diagnosticRunId:UUID}`; 409 para estado não iniciável | `LearningRouter`; `test_start_skill_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/abandon_diagnostic_controller.py` | Create | `AbandonDiagnosticController` | `POST /learning/goals/{goal_id}/skills/{skill_id}/diagnostic/abandon`, header `X-Diagnostic-Run-Id`, 204; 409 se vencido | `LearningRouter`; `test_abandon_diagnostic_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/complete_diagnostic_controller.py` | Create | `CompleteDiagnosticController` | `POST /learning/goals/{goal_id}/skills/{skill_id}/diagnostic/complete`, mesmo header, 200 com status `learning` ou `completed`; 409 se incompleto/vencido | `LearningRouter`; `test_complete_diagnostic_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/get_diagnostic_controller.py` | Modify | `GetDiagnosticController` | `GET /learning/goals/{goal_id}/skills/{skill_id}/diagnostic`, header opcional; na execução ativa inclui `activitySequence` ordenada; depois do envio, pendência ou `readyToComplete`; resumo consolidado nullable com cobertura | `test_get_diagnostic_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/get_choice_activity_controller.py` | Modify | `GetChoiceActivityController` | GET de Atividade existente; header obrigatório no diagnóstico; leitura de qualquer item ordenado antes do envio, 409 se execução vencida | `test_get_choice_activity_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/submit_choice_activity_controller.py` | Modify | `SubmitChoiceActivityController` | POST individual rejeita diagnóstico, preserva aprendizagem/revisão | `test_submit_choice_activity_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/submit_diagnostic_batch_controller.py` | Create | `SubmitDiagnosticBatchController` | `POST /learning/goals/{goal_id}/skills/{skill_id}/diagnostic/submissions`; header obrigatório `X-Diagnostic-Run-Id`, corpo JSON em snake_case `{submission_key: UUID, items: [{competency_id, activity_id, activity_revision: string, answers}]}`; resposta `{status:"pending",replayed:boolean}`, 201 inicial, 200 replay, 409 conflito | HTTP integrado |
| `apps/server/src/shifu/learning/rest/controllers/retry_choice_evaluation_controller.py` | Modify | `RetryChoiceEvaluationController` | POST retry existente; header obrigatório no diagnóstico, 202 mesma tentativa, 409 vencido | `test_retry_choice_evaluation_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/get_skill_experience_detail_controller.py` | Modify | `GetSkillExperienceDetailController` | GET da Habilidade com `overallResult` numérico ou nulo, `overallCoverageComplete`, cobertura por Competência, motivo/gap | `test_get_skill_experience_detail_controller.py` |
| `apps/server/src/shifu/learning/rest/controllers/__init__.py` | Modify | Exportar `AbandonDiagnosticController`, `CompleteDiagnosticController`, `SubmitDiagnosticBatchController` | Importações explícitas para o roteador | composição |
| `apps/server/src/shifu/learning/rest/router.py` | Modify | `LearningRouter.register` | Registrar envio único, abandono e confirmação sem sombrear rota dinâmica | HTTP integrado |
| `apps/server/rest-client/learning/learning.rest` | Modify | Requests rotulados de início, GET diagnóstico, envio único, abandono, confirmação e detalhe da Habilidade | Variáveis não secretas; header e corpo do envio idênticos ao controlador | paridade REST |
| `apps/server/rest-client/learning/activities.rest` | Modify | Requests rotulados de GET/retry da Atividade diagnóstica e prévia negada; POST individual diagnóstico documentado como rejeitado | Preservar requests de aprendizagem sem header de execução | paridade REST |

Todos os endpoints usam `AuthenticationPipe` e `LearningPipe` existentes;
nenhuma regra de Learning vai para essas pipes. A rota de prévia já registrada
mantém seu método e caminho, mas responde 404 a item diagnóstico antes de
acessar o avaliador. O GET de tentativa diagnóstica mantém 404. Cabeçalhos
inválidos recebem 422 do Pydantic; execução válida mas vencida recebe 409.

### UI, REST web e composição de rotas

Hierarquia esperada dos widgets:

| Widget | Tipo | Entrada | Filhos diretos | Contrato público | Dono do comportamento |
| --- | --- | --- | --- | --- | --- |
| `SkillPage` | Page | rota da Habilidade | `SkillExperience`, entrada diagnóstica, confirmação de remoção | Iniciar ou reentrar, sem “Continuar diagnóstico”; link posterior para resultado | `useSkillPage` e sessão em memória |
| `ActivityPage` | Page | rota de Atividade | cabeçalho diagnóstico, `ChoiceQuestion` ou `CodeQuestion`, controle de avanço/envio final | Avança sem POST entre Atividades; último item envia o conjunto; prática sem prévia pedagógica | `useActivityPage` |
| `DiagnosticResultPage` | Page | rota autenticada de resultado | síntese, lista consolidada, ação de recomendação/resumo | Carregamento, ausência privada, erro recuperável, parcial, desconhecido e conclusão direta | `useDiagnosticResultPage` |
| `SkillExperience` | Component da Page | `SkillPage` | `SkillOverview`, aviso, recomendação, Competências | Página habitual posterior com acesso ao resultado | props e hook pai |

Árvore prevista dos widgets criados ou estruturalmente alterados (testes
Vitest permanecem na pasta `tests/` do próprio widget):

```text
apps/web/src/ui/learning/widgets/pages/
├── activity-page/
│   ├── index.tsx
│   ├── use-activity-page.ts
│   ├── code-question/index.tsx
│   ├── code-question/tests/code-question.test.tsx
│   └── tests/
│       ├── activity-page.test.tsx
│       └── use-activity-page.test.ts
├── diagnostic-result-page/
│   ├── index.tsx
│   ├── use-diagnostic-result-page.ts
│   └── tests/diagnostic-result-page.test.tsx
└── skill-page/
    ├── index.tsx
    ├── use-skill-page.ts
    ├── skill-experience/
    │   ├── index.tsx
    │   └── tests/skill-experience.test.tsx
    ├── skill-overview/index.tsx
    ├── skill-competency-list/skill-competency-row/index.tsx
    └── tests/skill-page.test.tsx
```

| Caminho | Mudança | Declaração/operação | Contrato e garantias | Teste/geração |
| --- | --- | --- | --- | --- |
| `apps/web/src/core/learning/goal-detail.ts` | Modify | `DiagnosticOverview`, `DiagnosticCompetency` | DTO tipado com `runState`, `activitySequence`, cobertura, valores nullable e resultado | Page |
| `apps/web/src/core/learning/skill-experience.ts` | Modify | `SkillExperienceDetail`, `SkillCompetencySummary`, `SkillRecommendation` | Nulo/estimativa parcial/motivo/gap sem zero fictício | Page |
| `apps/web/src/constants/routes.ts` | Modify | `ROUTES.learningDiagnosticResult`, `learningDiagnosticResultPath` | Rota dinâmica fora de `StaticRouteName`; builder recebe `goalId` e `skillId` e codifica ambos quando URL precisa ser materializada fora do Router | Pages e testes de navegação |
| `apps/web/src/rest/services/learning-service.ts` | Modify | `startSkill`, `getDiagnostic`, `submitDiagnostic`, `abandonDiagnostic`, `completeDiagnostic`, GET/retry de Atividade | Mapear header de execução, resposta e erros; POST individual só para aprendizagem/revisão | Pages |
| `apps/web/src/ui/learning/diagnostic-run-session.ts` | Create | `get/set/clearDiagnosticRun`, respostas ordenadas e chave de envio final | Estado de aba em memória por Habilidade, sem persistência, URL ou cookie; limpar em abandono, invalidação e resultado confirmado | Pages |
| `apps/web/src/ui/learning/hooks/use-diagnostic-leave-guard.ts` | Create | `useDiagnosticLeaveGuard` | Avisar ao sair de diagnóstico incompleto; navegação interna para próximo item não interrompe; tentativa de abandono, falha segura e `beforeunload` | Pages e rota de Atividade |
| `apps/web/src/ui/learning/widgets/pages/skill-page/use-skill-page.ts` | Modify | `useSkillPage`, ações de início, reentrada, retry e confirmação | Gerar chave uma vez por entrada; sem loop de Strict Mode; reentrada automática só quando `diagnosing` e sem chave vigente | `skill-page.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/skill-page/index.tsx` | Modify | `SkillPage` | Substituir “Continuar diagnóstico” por avanço da execução atual; mostrar estados/invalidação e link posterior | `skill-page.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/skill-page/skill-experience/index.tsx` | Modify | `SkillExperience` | Link permanente para resultado consolidado após etapa confirmada | `skill-page.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/skill-page/skill-experience/tests/skill-experience.test.tsx` | Modify | teste público do componente | Link do resultado em aprendizagem/conclusão; composição preservada na `SkillPage` | Vitest |
| `apps/web/src/ui/learning/widgets/pages/skill-page/skill-overview/index.tsx` | Modify | `SkillOverview` | Resultado geral nullable e qualificador de cobertura | `skill-page.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/skill-page/skill-competency-list/skill-competency-row/index.tsx` | Modify | `SkillCompetencyRow` | Mostrar parcial, desconhecido, zero e liberação por texto | teste do widget dono |
| `apps/web/src/ui/learning/widgets/pages/activity-page/use-activity-page.ts` | Modify | `useActivityPage` | Guardar respostas de cada Atividade apenas na sessão em memória, avançar sem POST, enviar lote completo no último item, acompanhar estado agregado e retry da avaliação falha usando os IDs do item pendente retornado pelo GET; preservar aprendizagem/revisão | `use-activity-page.test.ts` |
| `apps/web/src/ui/learning/widgets/pages/activity-page/index.tsx` | Modify | `ActivityPage` | Mostrar próxima questão/Competência e somente no último item Enviar diagnóstico; editor e estados sem feedback individual; bloquear materiais/dicas da questão | `activity-page.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/index.tsx` | Modify | `CodeQuestion` | Esconder Avaliar questão quando a Page não fornecer `onAssess`; manter editor/prática e expor envio oficial na Page | `code-question.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/tests/code-question.test.tsx` | Modify | teste do widget | Sem botão de prévia em diagnóstico, prática/editabilidade preservadas | Vitest |
| `apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx` | Modify | testes do widget | Sigilo, código, envio, erro e estado acessível | Vitest |
| `apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts` | Modify | testes do hook de comportamento | Resposta congelada, envio idempotente e nenhuma prévia diagnóstica | Vitest |
| `apps/web/src/ui/learning/widgets/pages/skill-page/tests/skill-page.test.tsx` | Modify | testes da Page | Início, reentrada, ausência e link posterior | Vitest |
| `apps/web/src/ui/learning/widgets/pages/diagnostic-result-page/index.tsx` | Create | `DiagnosticResultPage` | Resultado nos estados de Pencil, erro/retry, ação e sem item individual | teste da Page |
| `apps/web/src/ui/learning/widgets/pages/diagnostic-result-page/use-diagnostic-result-page.ts` | Create | hook de estado | Consultar resumo e detalhe apenas após confirmação; motivo/gap e navegação | teste da Page |
| `apps/web/src/ui/learning/widgets/pages/diagnostic-result-page/tests/diagnostic-result-page.test.tsx` | Create | teste do widget | Hierarquia e estados públicos | Vitest |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/index.tsx` | Modify | `SkillRoute` | Guardar saída quando houver diagnóstico ativo; rota permanece fina | browser Page |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx` | Modify | `ActivityIndexRoute` | Avisar/abandonar saída; permitir avanço interno sem envio; redirecionar entrada direta sem sessão em memória para Habilidade | browser Page |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/diagnostic/result/index.tsx` | Create | rota `DiagnosticResultPage`, `beforeLoad` autenticado | Não inicia nova execução; parâmetros tipados | browser Page |
| `apps/web/src/routeTree.gen.ts` | Generate | árvore TanStack | Gerar com `pnpm --filter web generate-routes`, nunca editar à mão | build |
| `apps/web/tests/learning/activity-page.test.ts` | Modify | Playwright Page | Fluxo de escolhas/código, navegação, sigilo, erros, 390/1440 | transporte mockado |
| `apps/web/tests/learning/skill-experience-page.test.ts` | Remove | suíte com nome anterior | Migrar cenários úteis para a suíte da `SkillPage` | sem duplicação |
| `apps/web/tests/learning/skill-page.test.ts` | Create | Playwright Page | Entrada, reinício, link posterior e estado habitual | transporte mockado |
| `apps/web/tests/learning/choice-activity-page.test.ts` | Remove | duplicata idêntica de `activity-page.test.ts` | Manter uma suíte por `ActivityPage` | sem duplicação |
| `apps/web/tests/learning/diagnostic-result-page.test.ts` | Create | Playwright Page | Parcial, desconhecido, conclusão direta, autorização e responsividade | transporte mockado |

Os testes de integração web seguem `apps/web/tests/learning/<page>.test.ts`,
por Page, não por arquivo de rota. Não criar teste direto de query/action hook,
`LearningService` ou provedor. `use-diagnostic-leave-guard` é hook de
comportamento compartilhado; sua integração é verificada nas Pages. A execução
real autenticada com servidor e persistência pertence a VM-01; VM-02 verifica
layout e teclado mobile com transporte simulado, além dos testes HTTP/controlador.

**Limites e saída do Builder.** Os caminhos classificados nas tabelas acima
são o conjunto permitido para código, migração, clientes REST e testes; a
árvore gerada só muda pelo comando declarado. O handoff e esta Spec são
contratos do Orchestrator. Não editar `design/shifu.pen`, módulos
Gamification, Intelligence ou Identity, nem criar `apps/web/tests/routes`,
testes diretos do serviço web ou testes de hooks de query/action. A entrega
termina quando CA-01–CA-20 têm evidência automatizada nos seus limites,
VM-01 comprova uma jornada autenticada e persistida, VM-02 cobre layout e
teclado mobile, os contratos REST têm paridade e a migração foi verificada em
banco descartável. Comparar capturas frescas da seleção e do resultado normal
nos dois viewports; estados de erro, recuperação e demais desfechos não
exigem comparação visual nem captura para concluir.
Estados de carregamento, vazio privado, sucesso, erro e recuperação, além de
seleção, foco, ação desabilitada, teclado e movimento reduzido, devem ser
exercitados nas Pages afetadas sem expor avaliação individual.

| Decisão | Escolha | Alternativa | Motivo | Custo aceito |
| --- | --- | --- | --- | --- |
| Identidade da execução | UUID em `SkillExperience` e tentativa diagnóstica, sem tabela de execução | Tabela separada de sessões | Uma execução ativa por experiência e exclusão simples sob lock | Sessão abandonada sem nova chamada só é limpa na próxima entrada |
| Chave no navegador | Memória da aba | `sessionStorage` ou token na URL | Recarga e nova aba devem iniciar outra execução | Deep link diagnóstico volta à Habilidade para nova entrada |
| Conclusão | POST automático da página ativa | Job conclui ao terminar última avaliação | Evita conclusão após saída | Página precisa permanecer até confirmar; retry em falha de rede |
| Resultado | Rota web própria usando resumo persistido | Estado temporário da Skill Page | Acesso posterior sem trocar a entrada habitual | Mais uma Page e integração de rota |
| Política | Uma `AdaptiveLearningPolicy` global; sem identidade de política por experiência, banco ou HTTP | Manter ID de versão por experiência | PRD Learning v24 exige uma regra comum; snapshots concluídos permanecem imutáveis | Experiências históricas não concluídas passam à política global |
| Compatibilidade da seed | Omitir Skills sem cobertura e Goals seed que dependem delas; manter intactos registros persistidos e o gate curricular | Completar todo o catálogo ou apagar conteúdo/banco persistido | Pedido direto do usuário; evita Goals sem diagnóstico testável na seed | Uma nova seed de desenvolvimento deixa de mostrar os dois Goals removidos |
| Envio do diagnóstico | Uma ação final e um commit com tentativa/avaliação/evento por Atividade | POST por Atividade durante o percurso | Pedido direto do usuário elimina pausas entre itens e mantém evidência por Atividade | Respostas ficam só em memória até o último item; sair perde tudo |

# 4. Validation Contract

As evidências de implementação pertencem a `evaluation.md`, criado somente
no início da implementação. Testes web com `page.route` provam navegação e
contrato UI↔REST com transporte simulado; não provam autorização real,
persistência nem job. Testes de controlador com PostgreSQL descartável e de
job com Inngest/Testcontainers provam os respectivos limites. Playwright CLI
manual prova um fluxo autenticado integrado (VM-01). VM-02 prova composição
mobile e teclado com transporte simulado, sem alegar persistência. As
validações manuais exigidas cobrem somente caminhos felizes. Erro, recuperação,
concorrência, autorização negativa, evidência extrema e conclusão alternativa
são verificados pelas suítes automatizadas obrigatórias. Uma investigação
manual pontual de defeito pode ser registrada em `evaluation.md`, mas não
acrescenta uma VM nem se torna gate de conclusão.

| Arquivo/suíte | Tipo | Alvo | Meta de cobertura |
| --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_start_skill_use_case.py` | unit | `StartSkillUseCase` | entrada, reinício, isolamento e idempotência |
| `apps/server/tests/learning/core/use_cases/test_abandon_diagnostic_use_case.py` | unit | `AbandonDiagnosticUseCase` | exclusão provisória e chave vencida |
| `apps/server/tests/learning/core/use_cases/test_complete_diagnostic_use_case.py` | unit | `CompleteDiagnosticUseCase` | base por dificuldade, zero, desconhecido, cobertura, foco, corrida, resumo e eventos únicos |
| `apps/server/tests/learning/core/use_cases/test_get_diagnostic_use_case.py` | unit | `GetDiagnosticUseCase` | estados sem chave, sequência ordenada, pendente, pronto e confirmado |
| `apps/server/tests/learning/core/use_cases/test_create_goal_use_case.py` | unit | `CreateGoalUseCase` | seleção pronta e bloqueio de lacuna curricular |
| `apps/server/tests/curriculum/core/domain/test_diagnostic_coverage.py` | unit | validador curricular existente | lacunas de cobertura e avaliador confiável |
| `apps/server/tests/learning/server/controllers/test_get_goal_controller.py` | HTTP integration | GET de Objetivo | nenhuma identidade de política no contrato HTTP |
| `apps/server/tests/learning/server/controllers/test_get_goal_detail_controller.py` | HTTP integration | GET de detalhe do Objetivo | nenhuma identidade de política nos DTOs das Habilidades |
| `apps/server/tests/learning/core/use_cases/test_get_goal_detail_use_case.py` | unit | `GetGoalDetailUseCase` | detalhe construído sem ID de política |
| `apps/server/tests/learning/core/use_cases/test_get_choice_attempt_use_case.py` | unit | `GetChoiceAttemptUseCase` | projeção e avaliação sem branch de versão por experiência |
| `apps/server/tests/learning/server/controllers/test_adaptive_journey_controller.py` | HTTP integration | jornada e persistência após migração | ajustar a asserção para confirmar que política não é persistida e os resumos concluídos continuam iguais |
| `apps/server/tests/learning/core/use_cases/test_get_competency_detail_use_case.py` | unit | `GetCompetencyDetailUseCase` | alvo viável e progresso desconhecido migrados |
| `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | unit | envio | chave idempotente por execução, formas de resposta e conta |
| `apps/server/tests/learning/core/use_cases/test_submit_diagnostic_use_case.py` | unit | envio único | conjunto completo, UUIDv5 por item, replay, rollback, revisão, conta e execução |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | unit | avaliação | provisório, score de escolha/código, nenhuma aplicação tardia |
| `apps/server/tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py` | unit | retry | mesma resposta, execução vigente, falha do avaliador |
| `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | unit | leitura do item | qualquer item da sequência antes do envio, execução vigente e sigilo |
| `apps/server/tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py` | unit | prévia | diagnóstico negado antes do avaliador |
| `apps/server/tests/learning/core/use_cases/test_get_skill_experience_detail_use_case.py` | unit | resumo | nulo, parcial e completo, motivo/gap |
| `apps/server/tests/learning/server/controllers/test_start_skill_controller.py` | HTTP integration | início | auth, persistência, replay e 409 |
| `apps/server/tests/learning/server/controllers/test_abandon_diagnostic_controller.py` | HTTP integration | abandono | auth, exclusão e chave vencida |
| `apps/server/tests/learning/server/controllers/test_complete_diagnostic_controller.py` | HTTP integration | confirmação | auth, persistência, outbox e replay |
| `apps/server/tests/learning/server/controllers/test_get_diagnostic_controller.py` | HTTP integration | consulta | auth, header, estados e sigilo |
| `apps/server/tests/learning/server/controllers/test_get_competency_detail_controller.py` | HTTP integration | detalhe após diagnóstico | duas Competências, aprendizagem e recomendação preservadas |
| `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py` | HTTP integration | GET de Atividade | header e sigilo da execução |
| `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py` | HTTP integration | envio | 201/200/409, schema e escopo |
| `apps/server/tests/learning/server/controllers/test_submit_diagnostic_batch_controller.py` | HTTP integration | envio único | auth, 201/200/409, rollback e outbox por Atividade |
| `apps/server/tests/learning/server/controllers/test_retry_choice_evaluation_controller.py` | HTTP integration | retry | 202/409 e resposta preservada |
| `apps/server/tests/learning/server/controllers/test_get_skill_experience_detail_controller.py` | HTTP integration | resumo | campos nullable e cobertura |
| `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | job integration | evento outbox → avaliação | stale, callback de falha, execução válida, sem evento prematuro |
| `apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx` e `use-activity-page.test.ts` | component/hook | `ActivityPage` | seleção, código, envio sem prévia, erro |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/tests/code-question.test.tsx` | component | `CodeQuestion` | editor e prática sem botão de prévia diagnóstica |
| `apps/web/src/ui/learning/widgets/pages/skill-page/tests/skill-page.test.tsx` | component | `SkillPage` | entrada, reinício, link de resultado e estados |
| `apps/web/src/ui/learning/widgets/pages/skill-page/skill-experience/tests/skill-experience.test.tsx` | component | `SkillExperience` | link permanente para resultado e composição |
| `apps/web/src/ui/learning/widgets/pages/diagnostic-result-page/tests/diagnostic-result-page.test.tsx` | component | `DiagnosticResultPage` | listas consolidadas, parcial/desconhecido, conclusão |
| `apps/web/tests/learning/activity-page.test.ts` | browser Page | rota real de Atividade | header, envio, aviso, teclado, erro e mobile com transporte simulado |
| `apps/web/tests/learning/skill-page.test.ts` | browser Page | rota real da Habilidade | início, retorno, invalidação e acesso posterior com transporte simulado |
| `apps/web/tests/learning/diagnostic-result-page.test.ts` | browser Page | rota real do resultado | auth, resultado, navegação e responsividade com transporte simulado |

| Arquivo/suíte | Caso | Descrição | Asserções |
| --- | --- | --- | --- |
| `test_start_skill_use_case.py` | reinício com avaliação em voo | segunda entrada vence primeira | primeira Atividade e exclusão de tentativa/observação |
| `test_complete_diagnostic_use_case.py` | confirmação concorrente | duas confirmações da mesma execução | uma transição e uma publicação de cada evento aplicável |
| `test_abandon_diagnostic_use_case.py` | abandono após último job | avaliações completas, página saiu | sem progresso e sem `DiagnosticCompletedEvent` |
| `test_complete_diagnostic_use_case.py` | base parcial | fácil inconclusivo, médio 0, difícil 100 | 50 parcial, sem zero inventado ou dupla aplicação |
| `test_create_goal_use_case.py` | política de entrada | Currículo pronto ou com lacuna | experiência criada sem policy ID; lacuna continua bloqueada |
| `test_get_competency_detail_use_case.py` | alvo preservado | progresso desconhecido e conteúdo liberado | recomendação mantém alvo viável |
| `test_submit_choice_activity_use_case.py` | replay e abas | mesma chave repetida e chave da aba vencida | 200 idempotente vigente, 409 vencido, uma tentativa |
| `test_submit_diagnostic_use_case.py` | envio integral e replay | lote válido, item ausente/inválido, mesma chave repetida e execução vencida | todos os pares tentativa/avaliação/evento ou nenhum; replay sem duplicação |
| `test_evaluate_choice_activity_use_case.py` | código inconclusivo | rubrica obrigatória vs observação auxiliar | sem nota quando obrigatória falha; auxiliar não vira zero |
| `test_preview_activity_question_feedback_use_case.py` | sigilo | prévia para item diagnóstico | nenhuma nota, critério, comentário ou chamada ao assessor |
| `test_complete_diagnostic_controller.py` | conta e confirmação | conta alheia, execução incompleta e pronta | 404/409/200 corretos, DB e outbox coerentes |
| `test_evaluate_choice_activity_job.py` | evento antigo | abandono/substituição durante avaliação | job e on_failure não alteram nova execução |
| `activity-page.test.ts` | escolhas e código | navegar sem POST intermediário e enviar o lote final | um POST final com todos os itens, URL final, nenhuma correção visível |
| `skill-page.test.ts` | retorno e saída | saída confirmada e nova entrada | aviso, primeiro item, aba inválida explicada |
| `diagnostic-result-page.test.ts` | parcial e conclusão | dois payloads consolidados | badges com texto, links corretos, sem dados de item |

| CA | Automação obrigatória | VM de caminho feliz exigida | Alvo de evidência |
| --- | --- | --- | --- |
| CA-01 | início Core/HTTP; Skill Page | VM-01 | Evaluation: início |
| CA-02 | reinício e invalidação Core/HTTP; Skill e Activity Page | — | Evaluation: isolamento |
| CA-03 | sequência Core; Activity Page | VM-01 | Evaluation: ordem |
| CA-04 | envio/avaliação Core; Activity Page | VM-01 | Evaluation: escolhas |
| CA-05 | avaliação Core/HTTP/job; CodeQuestion e Activity Page | — | Evaluation: código |
| CA-06 | prévia/tentativa HTTP; Activity Page | VM-01 | Evaluation: sigilo |
| CA-07 | retry Core/HTTP/job; Pages | — | Evaluation: recuperação |
| CA-08 | confirmação Core/HTTP e outbox | VM-01 | Evaluation: confirmação |
| CA-09 | Core/HTTP/job concorrente | — | Evaluation: isolamento |
| CA-10 | base e cobertura Core/HTTP; Result Page | — | Evaluation: cobertura |
| CA-11 | política global Core/HTTP; Result Page | VM-01 | Evaluation: recomendação |
| CA-12 | conclusão Core/HTTP; Result Page | — | Evaluation: conclusão direta |
| CA-13 | HTTP; Skill e Result Page | VM-01 | Evaluation: retorno ao resultado |
| CA-14 | autorização HTTP e browser Page | — | Evaluation: autorização |
| CA-15 | browser Pages e widgets | VM-01 e VM-02 | Evaluation: acessibilidade e layout |
| CA-16 | casos de uso, `GET /goals`, `GET /goals/{goal_id}`, migração e replay histórico | — | Evaluation: política global e resultado concluído imutável |
| CA-17 | auditoria explícita da estrutura seed (não criar teste de seeder conforme Database Rules) | — | Evaluation: remoção das Skills e Goals seed incompatíveis |
| CA-18 | lote Core/HTTP; Activity Page com contrato de transporte | VM-01 | Evaluation: commit integral e um POST |
| CA-19 | lote Core/HTTP; Activity Page | — | Evaluation: rollback, revisão, conta e execução |
| CA-20 | job/HTTP; Activity Page | VM-01 | Evaluation: espera única e sigilo |

**Obrigatórias:** VM-01 e VM-02. Ambas exercitam somente o caminho feliz.
As demais CA permanecem obrigatórias nas suítes Core, HTTP, job, Page e
migração, sem VM manual. Defeitos observados durante as VMs devem ser corrigidos.

**Revisão paralela da entrega.** Após integrar código, executar os testes e
capturar as quatro imagens das VM, acionar em paralelo dois subagentes somente
de leitura sobre a mesma revisão da árvore: o
[`implementation-reviewer-agent`](../../../agents/implementation-reviewer-agent.md)
para o diff completo, contratos, CA e evidência; e o
[`visual-reviewer-agent`](../../../agents/visual-reviewer-agent.md) para abrir
as capturas e referências, comparar as duas superfícies nos dois
viewports e relatar diferenças concretas. O revisor visual usa as capturas já
exigidas, sem criar novos cenários manuais. O Orchestrator reconcilia ambos os
relatórios, corrige achados e repete apenas as verificações afetadas. Esses dois
relatórios compõem a revisão final; não há terceiro revisor serial obrigatório.

### VM-01 — Uma jornada autenticada e persistida (obrigatória)

**CA-01, CA-03, CA-04, CA-06, CA-08, CA-11, CA-13, CA-15.** Em ambiente
descartável, verificar saúde do web, FastAPI, PostgreSQL e Inngest. Usar uma
conta de teste autenticada com Objetivo/Habilidade elegível de uma Competência
e três Atividades diagnósticas de escolha, incluindo escolha única e múltipla,
nas dificuldades curricularmente ordenadas. O avaliador de escolha é
determinístico e os resultados levam ao ponto de partida normal com
recomendação; esta VM não requer
provedor externo de código, segunda conta ou falha induzida. Iniciar em
`/learning/goals/$goalId/skills/$skillId`, 1440 × 900. Comparar a seleção
com `XhhBc` ou `S4YpF1`, conforme o item, e o resultado normal com
`Yn7tE`.

1. Iniciar e responder as três Atividades em ordem, sem POST ou pausa entre
   elas; capturar uma seleção representativa e acionar Enviar diagnóstico uma vez.
2. Observar uma única espera agregada, aguardar a confirmação automática, abrir o resultado normal, voltar à
   Habilidade e reabrir o mesmo resultado; capturá-lo uma vez.

**Aprova se:** `POST /diagnostic/complete` termina com sucesso, a rota do
resultado abre e reabre, e um único resultado persiste no banco descartável
com foco/recomendação coerentes, sem erro inesperado no console/rede. Registrar
URL, resposta HTTP, ID do resultado e as duas capturas em 1440 × 900. Esta VM
prova o caminho integrado normal; repetição, falha, autorização negativa e
outbox duplicado são cobertos pela automação. Encerrar somente processos
iniciados para a validação e remover somente dados da fixture própria.

### VM-02 — Layout e teclado mobile (obrigatória)

**CA-15.** Com Playwright CLI e transporte determinístico das Pages, abrir em
390 × 844 uma Atividade diagnóstica com seleção e o resultado normal
(`XhhBc` ou `S4YpF1`, e `Yn7tE`). Percorrer seleção, envio e ação do resultado
pelo teclado; capturar uma imagem de cada superfície.

**Aprova se:** foco e aviso são perceptíveis, não há corte ou overflow
horizontal, a ação chega à URL esperada e não há erro inesperado no
console/rede. Registrar URL e duas capturas inspecionadas. Esta VM comprova
layout e interação mobile; autorização, persistência e job são cobertos pelos
respectivos testes automatizados.

| CI | Comando real | Limite |
| --- | --- | --- |
| CI-01 | `pnpm --filter web generate-routes` | gerar árvore após rota nova |
| CI-02 | `pnpm --filter web check:lint` | Biome web |
| CI-03 | `pnpm --filter web check:architecture` | dependências TS |
| CI-04 | `pnpm --filter web check:types` | TypeScript |
| CI-05 | `pnpm --filter web test:unit` | widgets e hooks |
| CI-06 | `pnpm --filter web test:integration tests/learning/activity-page.test.ts tests/learning/skill-page.test.ts tests/learning/diagnostic-result-page.test.ts` | Pages com transporte mockado |
| CI-07 | `pnpm --filter web build` | composição da rota |
| CI-08 | `cd apps/server && uv run poe check:lint` | Ruff |
| CI-09 | `cd apps/server && uv run poe check:architecture` | Tach |
| CI-10 | `cd apps/server && uv run poe check:types` | basedpyright |
| CI-11 | `cd apps/server && uv run poe test:unit` | casos de uso |
| CI-12 | `cd apps/server && uv run poe test:integration` | controladores + PostgreSQL descartável |
| CI-13 | `cd apps/server && uv run poe test:jobs` | Inngest/Testcontainers descartáveis |
| CI-14 | `cd apps/server && uv run poe build` | pacote Python |
| CI-15 | `cd apps/server && uv run poe db:upgrade head`; `uv run poe db:downgrade`; `uv run poe db:upgrade head` | somente banco descartável; conferir head |

`CI-15` exige URL de banco descartável e não autoriza downgrade do banco local
compartilhado. Os comandos `check:code` e `pnpm --filter web test` não existem
no manifesto atual e não são gates desta entrega. Além das suítes mockadas,
somente VM-01 exige Playwright CLI com servidor e persistência reais. VM-02
exige Playwright CLI para layout/teclado mobile com transporte simulado.
Ambas exigem capturas frescas das duas superfícies indicadas e inspeção de
console/rede; VM-01 confirma um resultado persistido no banco descartável.
Outbox, duplicação, erros e desfechos alternativos são verificados pela
automação, sem validação manual adicional.

# 5. Documentation alignment and revision history

| Documento | Autoridade | Estado | Mudança/confirmação |
| --- | --- | --- | --- |
| [PRD Learning v24](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB) | Produto | changed | Content ID `83066881`; RP-28 atualizado com confirmação explícita do usuário; política global sem versão por experiência |
| PRD Curriculum | Conteúdo e avaliação | confirmed | Content ID `83034113`, versão 12; Currículo mantém autoridade sobre cobertura, atividades diagnósticas e avaliadores |
| [SHIFU-77](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-77) | Origem de entrega | confirmed | Diagnóstico, resultado e reinício |
| `documentation/sdd.md` | SDD | confirmed | Spec e Evaluation governam a entrega; o registro de execução arquivado é histórico; Evaluation retém evidência histórica e acompanha a nova revisão |
| `documentation/modules.md` | Dono do produto | confirmed | Learning decide progresso; Curriculum fornece cobertura e avaliação; outros módulos só consomem fatos permitidos |
| `documentation/architecture.md` | Camadas e integração | confirmed | Core/REST/DB/outbox/Inngest existentes preservados |
| `documentation/design.md` | Experiência transversal | confirmed | Estados T19/T20/T21/T26 permanecem alinhados à experiência descrita na PRD |
| `documentation/rules/web-app-routing-rules.md` | Rotas e testes | changed | Suíte de integração por Page/Layout no módulo; scripts existentes |
| `documentation/tooling.md` e manifestos | Comandos | confirmed | pnpm web, uv servidor, jobs e migração reais |
| `AGENTS.md` | Exploração | changed | CodeGraph exigido antes de cada nova exploração de código |
| `documentation/features/learning/skill-experience/spec.md` | Contrato de entrega anterior | historical | Premissas de política por experiência deixam de reger novos cálculos; snapshots já concluídos não são alterados |
| [handoff do diagnóstico](./design/handoff.md) | Referências desta UI | updated | Dez PNGs em escala 1; revisão 6 limita a comparação visual a quatro capturas do caminho feliz em dois viewports |

| Rule Pack | Aplica-se a | Revisão avaliada |
| --- | --- | --- |
| `documentation/rules/typescript-conventions-rules.md` | TS web | 2026-09-27 |
| `documentation/rules/python-conventions-rules.md` | Python servidor | 2026-09-27 |
| `documentation/rules/ui-layer-rules.md` | widgets, hooks e REST web | 2026-09-27 |
| `documentation/rules/web-app-routing-rules.md` | rotas e árvore gerada | 2026-09-27, correção aprovada |
| `documentation/rules/widget-testing-rules.md` | Vitest e browser por Page | 2026-09-27 |
| `documentation/rules/core-layer-rules.md` | entidades, estruturas, use cases | 2026-09-27 |
| `documentation/rules/use-case-testing-rules.md` | testes Core | 2026-09-27 |
| `documentation/rules/rest-layer-rules.md` | controladores e adapter | 2026-09-27 |
| `documentation/rules/server-app-layer-rules.md` | `LearningRouter` e registro dos controladores | 2026-09-27 |
| `documentation/rules/controllers-testing-rules.md` | HTTP integrado | 2026-09-27 |
| `documentation/rules/database-layer-rules.md` | migração, modelos, repositórios | 2026-09-27 |
| `documentation/rules/provision-layer-rules.md` | port de Curriculum, settings, provider e composition | 2026-09-27 |
| `documentation/rules/messaging-layer-rules.md` | outbox e job | 2026-09-27 |
| `documentation/rules/jobs-testing-rules.md` | Inngest Testcontainers | 2026-09-27 |

| Revisão | Data | Mudança material | Motivo |
| --- | --- | --- | --- |
| 1 | 2026-09-27 | Contrato completo do diagnóstico com reinício, confirmação pela página ativa, resultado persistido e handoff visual | PRD Learning v23, SHIFU-77 e decisões confirmadas |
| 2 | 2026-09-27 | Uma jornada persistida e uma checagem mobile são as VM obrigatórias; matrizes de falha, código e desfechos extremos ao vivo passam a suplementares, com cobertura automatizada preservada | Decisão do usuário após observar atrasos e bloqueios causados por validação manual excessiva em entregas anteriores |
| 3 | 2026-09-27 | Validação visual somente do caminho feliz | Decisão explícita do usuário |
| 4 | 2026-09-27 | Toda validação manual exigida cobre somente caminhos felizes; casos negativos e desfechos alternativos ficam na automação | Esclarecimento explícito do usuário |
| 5 | 2026-09-27 | Cada VM foi reduzida a uma jornada com critério explícito de aprovação, evidência mínima e limite de conclusão | Pedido do usuário para validações manuais concisas e conclusivas |
| 6 | 2026-09-27 | Revisores de código e visual atuam em paralelo sobre a mesma entrega integrada; Orchestrator reconcilia os relatórios sem terceiro revisor serial | Decisão explícita do usuário |
| 7 | 2026-09-27 | Política global sem versionamento por experiência; catálogo existente de Habilidades integralmente apto ao diagnóstico, preservando validação curricular de qualidade | Emenda autorizada pelo usuário à PRD Learning v24 e autoridade do PRD Curriculum v12 |
| 8 | 2026-09-27 | Respostas de todas as Atividades reunidas em memória e um envio final atômico, com tentativa/avaliação por Atividade e uma espera agregada | Pedido direto do usuário após discussão do envio único |
| 9 | 2026-09-27 | Estrutura da seed omite 8 Skills incompletas e 2 Goals dependentes; nenhum comando de reseed é executado nesta entrega | Escolha explícita do usuário em vez de completar as Skills incompatíveis |
