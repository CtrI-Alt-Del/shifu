---
title: Mentor — respostas contextuais e recuperação
status: implemented
revision: 18
last_updated_at: 2026-10-12
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-100
scope:
  - intelligence/mentor
  - authorized-read-contracts/learning-curriculum-gamification
  - web/mentor-page-and-fab
---

# Objective

Entregar respostas determinísticas e locais do Mentor a partir de mensagens de texto e contexto autorizado do Shifu. Respostas recuperadas persistem antes da apresentação e podem ser recuperadas sem reenviar a mensagem. Perguntas sem resposta local confiável recebem uma abstinência explicativa; nenhuma chamada remota de geração ou revisão ocorre neste recorte.

Spec em modo **complete**, devido a isolamento, contexto pedagógico, concorrência, persistência, recuperação e integrações. SHIFU-99 já cria, lista, retoma, renomeia e exclui conversas; persiste mensagens e uma resposta final idempotente. Ainda não implementa envio subsequente, processamento de respostas, tentativas, blocos ou SSE. Esta Spec estende essa base sem declarar capacidades planejadas como implementadas.

# Scope

| Área / ator | Incluído | Excluído ou dependência |
| --- | --- | --- |
| Aprendiz / Mentor | Texto; resposta por blocos; consultas identificadas genericamente; cancelar/retry; página e FAB | Anexos, ditado, voz, memórias entre conversas e sumarização de sessão |
| Intelligence | Intenções por embeddings, spaCy lexical, JSON curado, busca BM25 + embeddings, templates locais, esclarecimento, recusa pedagógica e abstinência determinística | Geração Agno/OpenRouter e revisão JEV; TF-IDF + regressão logística / OneVsRest; treinamento supervisionado; chatbot irrestrito |
| Learning | Leitura autorizada de Objetivos, experiências de Habilidade, progresso, recomendações, tentativas e avaliações permitidas | Criar/remover Habilidades ou Objetivos; modificar avaliações, progresso ou recomendações |
| Curriculum | Descoberta de Habilidades e contexto permitido; índice não pessoal de campos mínimos | Expor conteúdo bloqueado, gabaritos ou fontes diagnósticas; inventar pré-requisitos |
| Gamification | Leitura dos fatos existentes de XP, nível, sequência e conquistas | Inventar dados ausentes; alterar recompensas; interpretar XP como domínio |
| Disponibilidade / privacidade | Perfis do servidor, alternativa elegível, guardas de acesso/publicação | Cota mensal (autorização por saldo, accounting comercial, renovação e UI), encerramento de conta e revogação coordenada entre módulos |
| Observabilidade | Langfuse local opcional e avaliação sintética reproduzível | Proxy MCP próprio; credenciais em Git; dependência de Langfuse para responder |

## Amendment 16 — bounded local-only delivery

This amendment supersedes prior active requirements for conversational generation, model review/calibration, identity-linked traces, and generated-answer journeys. It does not rewrite their historical evidence. Production routing returns only authorized local FAQ/context blocks, clarifications, pedagogical refusals, or a deterministic abstention. The route always returns an empty `generation_requests`; the production answer runtime constructs no OpenRouter clients. Existing Agno generation/review code and its consumer tests remain dormant implementation material, not a release acceptance requirement. A guard test must prove that an unsupported production question completes with the abstention and sends no request to a model endpoint.

Langfuse may record anonymous operational stage spans with opaque correlation IDs and allowlisted metadata, without account IDs, session IDs, learner content, prompts, or generated answers. Since this delivery performs no answer inference, it incurs no Mentor answer-model cost and creates no cost generation record; the existing access port may receive an idempotent technical usage receipt of zero tokens. The cost instrumentation remains available for a future separately approved inference scope. Retention of anonymous operational metadata is not used to claim compliance with the deferred identity-linked deletion requirement.

For this revision, CI-16 reviewer calibration and the generated-answer portion of VM-01 are **not applicable** because no production inference path is enabled. VM-02 is narrowed to proving that the real SDK exports operational traces without identity attributes or private content; it does not prove retention/deletion compliance. CI-07 is narrowed to local-only routing and deterministic abstention with zero upstream model calls. CI-02/03/06 continue to prove retrieval correctness, authorized context, pedagogy, and abstention. Earlier implementation details below that describe generation/review remain historical design context and do not override this active amendment.

The complete canonical Intelligence PRD (content 83099649, version 7) was reread on 2026-10-12. It defines a broader contextual AI Mentor, including generated guidance and provider privacy requirements. This revision is an explicitly bounded local-only delivery slice and does not implement or supersede that broader product contract. The external PRD was not changed. Keep the slice clearly identified as partial and do not declare the Intelligence product/module complete.

Cobertura canônica neste recorte é **partial** para RP-04/05: FAQ/contexto local autorizados, sem geração conversacional. **RP-01 partial** (Mentor, não disponibilidade global do Planejador); **RP-03 partial** (continuidade/exclusão durante resposta, preservando gerenciamento entregue); **RP-06 partial** (transporte progressivo/cancelamento/repetição textual sem respostas geradas); **RP-11/12/13 partial** (guardas e superfícies deste recorte, não todo o ciclo de eliminação); **RP-02 deferred** (cota mensal, bloqueio por percentual, accounting comercial e UI fora deste recorte; sem dependência de publicação desta entrega). RP-07 a RP-10 e RP-14 a RP-17 ficam fora da entrega. Jornadas selecionadas: JN-02/03/04/05/17; JN-16 deferida neste recorte, sem aceitação de encerramento completo. Trecho de JN-05 sobre cota segue RP-02 deferido.

O [handoff visual](design/handoff.md) registra frames inspecionados, imagens duráveis reutilizadas e adaptações aprovadas. Digitação, múltiplos blocos e mobile adaptam a composição existente, sem novos workflows.

**Autorização deste recorte:** Identity fornece conta ativa e revisão de acesso reais para leitura, envio, retry e processamento local; nenhuma operação é autorizada apenas por JWT ou grant fictício. Conta ausente/inativa, revisão divergente ou estado inacessível rejeitam a operação. Ausência de cota mensal não bloqueia respostas locais. Encerramento completo, revogação coordenada atomicamente entre módulos e eliminação em 24 horas ficam deferidos; esta entrega não afirma provar esses resultados de RP-11/13 ou JN-16. Permanecem revalidação do acesso nos pontos de uso, isolamento e fence transacional de sessão/tentativa/exclusão. As obrigações canônicas deferidas continuam no PRD e exigem entrega própria antes de declarar o módulo completo.

# Behavior Contract

| ID | RP / JN | Comportamento observável obrigatório |
| --- | --- | --- |
| RF-01 | RP-03/06/12; JN-02/05 | Envio salva texto exato, hint e tentativa atomicamente. Processamento continua ao fechar FAB, navegar/recarregar/desconectar. Uma mensagem sem resposta concluída e uma tentativa ativa por conversa; conversas independentes. |
| RF-02 | RP-03/06/11/13 | Mesma submissão não duplica mensagem/tentativa/evento/resposta; chave com entrada diferente conflita. No máximo uma resposta concluída por mensagem do aprendiz. |
| RF-03 | RP-04/05; JN-03/04 | Múltiplas intenções locais produzem blocos identificáveis. Se uma parte singular for resolvida por FAQ local suficiente, classificações incidentais de busca do currículo não acrescentam resumo de materiais; buscas explícitas em outra parte continuam independentes. Intenção desconhecida não impede FAQ. Parte sem resposta local confiável recebe abstinência. Ambiguidade exige esclarecimento, sem escolher Objetivo/Habilidade silenciosamente. Geração remota está desabilitada nesta revisão. |
| RF-04 | RP-01/04/05 | Resposta curada somente com correspondência suficiente e restrições verificadas. Templates exibem fatos oficiais disponíveis. Sem correspondência confiável, o Mentor se abstém com orientação determinística; nenhum fallback remoto ou resposta inventada. |
| RF-05 | RP-04/05/13 | Consultar somente conta autenticada/conteúdo autorizado. Proprietários mantêm autoridade sobre fatos/elegibilidade. Não alterar estado de negócio nem inventar nota/domínio/recomendação. |
| RF-06 | RP-04/05; JN-03 | FAB sempre tenta contexto da página no envio. Referência explícita prevalece sobre continuidade/hint. Hint é pista validada no backend. Retry mantém hint original, consultando estado atual; Objetivo necessário deve ser especificado. |
| RF-07 | RP-03/04/05 | Resolução determinística usa somente referências/alvos/listas ordenadas/esclarecimentos estruturados; não depende de contexto conversacional gerado. Estado mutável é consultado novamente; histórico não prova permissão. Sem sumarização/truncamento silencioso. |
| RF-08 | RP-04/05 | Habilidade não concluída na experiência do Objetivo: dicas sem solução completa, inclusive cumulativamente. Competência concluída/outra experiência não autoriza solução. Não ajudar/consultar Atividade diagnóstica em andamento; outros assuntos permitidos. Nunca expor respostas/avaliações diagnósticas individuais. |
| RF-09 | RP-04/05 | Habilidades podem ser descobertas sem vínculo. Competências não liberadas ajudam localizar Habilidade internamente, sem exposição. Materiais/Atividades exigem liberação/contexto autorizado. Não adicionar regra inexistente de Habilidade prévia concluída. |
| RF-10 | RP-04/06/13 | Não há bloco gerado nesta revisão. Blocos locais precisam de referência curada ou fatos permitidos; recusa pedagógica e abstinência são determinísticas e nunca passam por reviewer remoto. Requisitos de revisão Agno/JEV ficam deferidos. |
| RF-11 | RP-06/12 | SSE transmite blocos completos aprovados, não tokens brutos. Typing só para blocos novos durante visualização ativa. Histórico/reload/replay completos, sem repetir animação ao alternar FAB/página. Markdown/código seguros. |
| RF-12 | RP-06; JN-05 | Cancelar descarta parcial/consultas e conserva aprendiz pendente. Retry cria tentativa nova da mesma mensagem e descarta parcial anterior. Falha preserva mensagem e permite retry; concluída não regenera. |
| RF-13 | RP-03/06/11/13; JN-05/17 | Replay ordenado sem duplicação. Cancel/retry/delete e perda de acesso detectada invalidam callbacks antigos. Exclusão interrompe uso e impede recriação por replay. Encerramento coordenado de conta permanece deferido. |
| RF-14 | RP-01/13 | Answer runtime não cria clientes OpenRouter nem envia pedidos de geração/revisão, mesmo se credenciais estiverem configuradas. Conta indeterminada/inativa e revisão de acesso divergente não autorizam; ausência de cota mensal deferida não é indisponibilidade. |
| RF-15 | RP-01/06 | Resposta local não produz recibo de inferência nem custo de modelo; o port de acesso pode receber recibo técnico idempotente de zero tokens. Não há débito, limite mensal, percentual ou cobrança de cota nesta entrega. Infraestrutura de medição permanece inativa para respostas do Mentor até uma revisão futura habilitar inferência. |
| RF-16 | RP-11/13 | Langfuse, quando habilitado, recebe somente spans operacionais allowlistados, correlation UUID opaca e contagens/duração; nenhum `account_id`, `session_id`, conteúdo, prompt, resposta ou dado pessoal. Nenhuma generation de resposta é registrada. VM-02 comprova atributos exportados e ausência de conteúdo; não declara conformidade de retenção/exclusão vinculada a conta. Falha de Langfuse não muda a resposta. |
| RF-17 | RP-12 | Continuidade página/FAB, pt-BR, teclado/foco/mobile. Reduced motion apresenta completo; leitor de tela não anuncia cada caractere. Estados pendente/falha acessíveis; Learning continua utilizável. |
| RF-18 | RP-01/04/05 | Índices versionados/reconstruíveis usados somente quando compatíveis; sem rebuild no envio. Match insuficiente abstém-se. Nenhum dado pessoal no índice curricular. |

| ID | RF | Dado / quando | Resultado obrigatório | Checks |
| --- | --- | --- | --- | --- |
| CA-01 | RF-01/02 | Nova/existente; replay e envios concorrentes | Uma mensagem/tentativa/outbox; divergência409; segundo envio distinto rejeitado enquanto pendente | CI-01/04/05; VM-01 |
| CA-02 | RF-03/04/18 | Pedido simples/múltiplo/sem intenção/ambíguo | Todos os rótulos avaliados; local somente com gate; blocos independentes ou esclarecimento | CI-02/03/07 |
| CA-03 | RF-05/06/09 | Hint válido/ausente/estrangeiro/incoerente; retry em outra rota | Conta confiável/hierarquia validada, Objetivo identificado, explícito prevalece, retry consulta dados atuais com hint original | CI-03/04/06/08; VM-01 |
| CA-04 | RF-07 | Continuidade e estado de progresso alterado | Roteamento local usa referências atuais e dados autorizados; nenhuma chamada ao gerador recebe histórico | CI-03/06/07 |
| CA-05 | RF-08/09/10 | Aprendendo/concluída/outra experiência/diagnóstico; pedir ajuda cumulativa | Restrições pedagógicas preservadas; diagnóstico não exposto; pedido de solução completa sem FAQ autorizada recebe recusa/abstinência, nunca inferência remota | CI-03/06/07/09 |
| CA-06 | RF-04/10/14 | FAQ/contexto conhecido, ambiguidade, pedido pedagógico proibido e pergunta sem correspondência | Publicar somente blocos locais permitidos, esclarecimento, recusa pedagógica ou abstinência; nenhum provider remoto chamado | CI-02/03/06/07 |
| CA-07 | RF-01/11/13 | Disconnect/Redis falha/reload/replay | Recuperação DB sem geração nova, ordem/identidade preservadas; typing só foreground novo | CI-05/08/15; VM-01/03 |
| CA-08 | RF-02/12/13 | Cancel/retry/callback tardio concorrente | Parcial retirado, aprendiz preservado; tentativa nova sem nova mensagem; completed não regenera | CI-01/04/05/08/09 |
| CA-09 | RF-05/13/16 | ContaB acessaA; A exclui conversa; conta inativa ou revisão divergente nos pontos de guarda durante job/SSE | Rejeição sanitizada; sem dado estrangeiro; exclusão impede efeito tardio/recriação e acesso inválido detectado interrompe a operação; sem alegação de encerramento coordenado | CI-04/05/06/09/15 |
| CA-10 | RF-14/15 | Conta ativa, credencial OpenRouter presente/ausente, consulta local/abstenção | Operação continua sem provedor de geração; zero chamadas/custo/recibo de inferência. Recibo técnico é opcional; se emitido, tem zero tokens e é idempotente. Conta inválida é rejeitada | CI-01/04/05/07/09 |
| CA-11 | RF-16/18 | Telemetria off/falha, índice compatível/incompatível | Trace anônima allowlistada sem conteúdo; versão só ativa após preparo completo; sem alegação de retenção vinculada a identidade | CI-02/05/07; VM-02 |
| CA-12 | RF-11/17 | Página/FAB desktop/mobile, teclado/reduced motion/Markdown adversarial | Sem duplicação/HTML executável/overflow; foco/typing/a11y corretos; pendente/falha conserva mensagem | CI-08/15; VM-01/03 |
| CA-13 | RF-04/18 | Held-out local de paráfrases e negativos | Nenhuma FAQ irrelevante selecionada; resultados de recuperação e abstenção reportados sem exigir cobertura mínima | CI-02/03/06/07 |

# Technical Contract

## Architecture Mapping

**Owner:** Intelligence. Learning/Curriculum/Gamification/Identity produzem leituras e autorizações; composição injeta portas neutras. Shared não assume regras de negócio. Provider Intelligence não importa Core/repositório privado de outro módulo. Preservar Tach: módulos de negócio dependem somente de `shifu.shared`.

Rule Pack via [router](../../../rules.md): Python Conventions, TypeScript Conventions, Core, REST, Database, Provider, Messaging, AI, Server App, UI, Web Routing, Validation, Use Case Testing, Controller Testing, Job Testing e Widget Testing. Reabrir seleção se scope expandir. Core sem Pydantic/FastAPI/SQLAlchemy/Agno; estruturas `@structure`, entidade imutável, enums `StrEnum`, uma declaração pública por arquivo, exports explícitos sem I/O.

**Alinhamento das Rules:** AI Layer Rules registram NLP em providers e código Agno em ai/agno, mas a composição/validação ativa da revisão16 é local-only. Código Agno/JEV dormente não é prova exigida para esta revisão; não migrar código/testes legados fora do recorte. A instrumentação genérica do subprocess é responsabilidade do Tooling, não um critério de aceitação desta Spec.

| Ação | Limite / elemento | Mudança |
| --- | --- | --- |
| Modify | Intelligence Core: create/finalize/remove, UoW/messages repository | Aceitação/outbox, finalização com attempt fence, exclusão invalida execução; mesma transação |
| Create | Core: submit/cancel/retry/process/read-events, tentativa/blocos/portas | Envio subsequente, cancel/retry, roteamento local, abstinência, publicação e replay autorizado |
| Create / Modify | SQLAlchemy/Alembic | Tentativas/eventos/pgvector, constraints/locks/CAS, backfill compatível |
| Modify | PostgreSQL da aplicação e fixtures descartáveis | Extensão vector no PostgreSQL17; transição sem reset, preservando isolamento/volumes |
| Create / Modify | REST/controllers/schemas/router/.rest | HTTP/SSE privados autenticados; erros sanitizados/no-store |
| Create / Modify | Messaging/app/pipes/settings | Novo job no único registro Inngest; clientes long-lived, portas/UoW injetados |
| Create | AI/providers | spaCy/embeddings/BM25; respostas locais determinísticas, esclarecimento, recusa pedagógica e abstinência; Agno/JEV permanecem fora da composição ativa |
| Modify | Telemetria do Mentor | `apps/server/src/shifu/intelligence/core/interfaces/mentor_telemetry_provider.py`; `apps/server/src/shifu/intelligence/providers/telemetry/langfuse/langfuse_mentor_telemetry_provider.py` | Exportar apenas spans operacionais allowlistados com UUID de correlação opaca; não associar identidade nem conteúdo. Sem mudança no payload Inngest, REST ou migrations. |
| Modify | Consumidor registrado com SDK Langfuse real | `apps/server/tests/messaging/inngest/jobs/intelligence/test_mentor_langfuse_sdk_job.py` | Validar spans OTLP reais sem atributos de usuário/sessão, corpo privado, resposta, geração ou custo de modelo. |
| Modify | Identity provider `apps/server/src/shifu/identity/providers/identity_mentor_access_provider.py` e consumidores de acesso em Intelligence | Autorizar conta ativa/revisão real para operação; não exigir ledger/cota/encerramento deferidos; manter failclosed por estado inválido. Inferência e medição de custo estão desabilitadas nesta revisão. |
| Create | Shared ports e produtores proprietários | Snapshots neutros mínimos; dados ausentes são indisponíveis, não inventados |
| Create / Modify | Web/context/operações/widgets/BFF | Um estado compartilhado, hint capturado, SSE ordenado, typing de apresentação |
| Preserve | Sessões/título, navegação Learning, JEV avaliação código | Compatibilidade de componentes dormentes; a rota Mentor não invoca JEV nem altera notas oficiais |
| Confirm | Compose/.env.example | Manutenção autorizada já feita: Langfuse7003, seis nomes explícitos, sem proxy; tracing ainda planejado |

> **Histórico de emendas 7–15, supersedido para a entrega atual:** os requisitos abaixo descreviam geração Agno/JEV, limiar JEV 0.75 e produção de traces com identidade. São contexto histórico e não são checkers ativos da revisão16. Evidências e falhas permanecem no Evaluation; não reativar esse fluxo sem nova emenda.

**Emenda7 — calibração JEV (histórico supersedido).** Intelligence possui o corpus de revisão, separado dos exemplos de FAQ/intenção. Declarações, modelo, rubrica, portas, composição e lifecycle permanecem os atuais. Nenhum dado real do aprendiz ou avaliação oficial Learning entra no corpus. Na revisão9, o usuário define explicitamente0.75 para os seis critérios, após conhecer a falha da seleção. Isso substitui a condição de adoção numérica da emenda7, mas não comprova calibração segura e não muda o resultado Failed histórico de CI-16. Nenhum retorno JEV ou guard é forçado.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Intelligence AI/data | `apps/server/src/shifu/intelligence/ai/data/mentor-review-evaluation.json` | Exemplos sintéticos com rótulos editoriais, partições e famílias independentes |
| Modify | Intelligence writer agent | `apps/server/src/shifu/intelligence/ai/agno/agents/mentor_writer_agent.py` | Emenda10: explicar conceitos gerais sem confundir com solução integral; respeitar diagnostic_in_progress autorizado, contexto e guardas; CI-07/10..13 e VM-01 |
| Modify | Intelligence reviewer provider | `apps/server/src/shifu/intelligence/providers/mentor_review_provider/openrouter/openrouter_jev_mentor_review_provider.py` | Emenda10: explicitar aplicação condicional e opções mutuamente exclusivas, mantendo escolha approved/confidence≥0.75; CI-07/09/16, CI-10..13 e VM-01 |
| Modify | Intelligence native model/workflow | `apps/server/src/shifu/intelligence/ai/agno/models/mentor_openai_chat.py`; `apps/server/src/shifu/intelligence/ai/agno/workflows/agno_answer_mentor_message_workflow.py` | Emenda10: preservar recibo numérico autêntico antes de erro nativo; nada de payload privado ou uso inventado; consumidor registrado e CI-07/09/10..13/VM-01 |
| Modify | Intelligence AI/data | `apps/server/src/shifu/intelligence/ai/data/mentor-index-manifest.json` | Definir os seis review_thresholds em0.75 por decisão explícita do usuário; preservar configurações NLP |
| Modify | Registered job consumer | `apps/server/tests/messaging/inngest/jobs/intelligence/test_answer_mentor_message_job.py` | Prova opt-in JEV real pelo job registrado, writer controlado no transporte e efeitos persistidos; sem teste direto do provider |

```text
apps/server/
  src/shifu/intelligence/ai/data/
    [N] mentor-review-evaluation.json (planned)
    [M] mentor-index-manifest.json (six review thresholds0.75)
  tests/messaging/inngest/jobs/intelligence/
    [M] test_answer_mentor_message_job.py (planned scenarios at existing consuming job boundary)
```

Cada exemplo contém id, partition (`calibration`/`held_out`), family_id, pedido/contexto/histórico/prefixo sintéticos compatíveis com as estruturas existentes, candidato e rótulos para os seis critérios (`approved`/`rejected`/`inconclusive`), com justificativa editorial vinculada a RP-04/05/06/13. Dois revisores editoriais independentes do resultado JEV conferem os rótulos antes de qualquer chamada; divergência não resolvida exige substituir o caso antes de congelar a matriz. Não guardar raciocínio do modelo ou conteúdo pessoal. Parafraseamentos da mesma família não cruzam partições. O corpus não é carregado online nem cria uma porta pública.

O hash dos recursos Mentor inclui o manifesto: trocar review_thresholds muda a versão do índice. Preparar a nova versão pelo comando existente CI-05, sem reset de dados/volumes, antes da validação online; ativar somente após preparo completo. Revalidar compatibilidade e o held-out NLP em CI-02/05. Não ignorar índice incompatível nem reconstruir no envio.

**Conceitos introduzidos e suas fronteiras.** As explicações abaixo definem estruturas e componentes do recorte. Writer/reviewer/geração em blocos marcados como históricos não são capacidades ativas da revisão16. O Runtime Flow abaixo define o contrato executável atual.

**Mensagem, tentativa e resposta.** A mensagem learner é o pedido persistido e conserva seu ID durante retry. `MentorResponseAttempt` representa uma execução desse pedido, com ID próprio, status e orçamento de execução. Submit cria a primeira tentativa; retry cria outra para a mesma mensagem, após descartar o resultado parcial conforme RF-12. A tentativa é propriedade de Intelligence Core, persistida por seu repository. Seu ID permite reconhecer callbacks obsoletos: um resultado da tentativa anterior não pode finalizar a atual. Conclusão produz a mensagem Mentor definitiva; nenhum placeholder ou candidato recusado é uma resposta concluída. Provas de transições, concorrência e recuperação estão nos checkers ligados a RF-12 e nos testes Core/controller/job.

**Bloco de resposta local (contrato ativo da revisão16).** `MentorResponseBlock` é uma unidade exibível identificada por blockKey e ordinal; intent opcional informa o assunto sem autorizar uma ação. O conteúdo vem de FAQ curada, fatos atuais de módulos proprietários, esclarecimento, recusa pedagógica ou abstinência determinística. A ordenação é estável e a persistência precede a publicação. A rota de produção não cria blocos gerados; o texto inteiro chega ao browser e typing é só apresentação. CI-07 prova a rota local; apresentação é CI-08.

**Evento, cursor e snapshot.** `MentorResponseEvent` registra uma mudança publicável de status, consulta ou bloco aprovado. A sequence ordena os eventos do recurso e funciona como cursor de replay, sem ser credencial. `MentorResponseSnapshot` é a leitura consolidada da tentativa, blocos, consultas e última sequência, usada na abertura/reconciliação. Postgres é a fonte de ambos; Redis apenas sinaliza que há novidades. SSE transporta os eventos, não substitui sua persistência. O Web provider mantém uma cópia de apresentação do snapshot e aplica eventos sem regressão; a lifecycle do hook está definida no contrato Web. CI-08/CI-15 e os testes server de leitura de eventos provam consumo e transporte.

**Context hint e contexto autorizado.** `MentorContextHint` contém somente os IDs da página capturados no envio; é uma indicação não confiável de foco, sem conteúdo pedagógico nem permissão. O backend resolve esses IDs e combina histórico completo da sessão com fatos atuais fornecidos pelos módulos proprietários em `MentorContextSnapshot`. Learning decide o que está acessível; Curriculum fornece a projeção permitida; Identity fornece acesso ativo; Gamification fornece apenas fatos existentes. Uma referência explícita do pedido pode superar o foco da página, mas nunca a autorização. Retry reutiliza o hint original e relê fatos mutáveis. Essas portas retornam estruturas neutras e não expõem repositories privados. Os checkers de contexto/elegibilidade e CI-06 cobrem os limites dos produtores.

**Acesso, uso técnico e fence.** `MentorAccessGrant` identifica conta ativa, revisão e operação; Identity resolve e revalida esses fatos reais tanto para leitura quanto para envios/retries, sem consultar cota deferida. `MentorUsage` conserva a assinatura existente como notificação técnica de uso, não como autorização de saldo ou débito. A interface de recibos de inferência é preservada para compatibilidade, mas a revisão16 não a chama nem persiste uso de modelo; Identity não assume política comercial de cota. `record_usage` preserva compatibilidade e valida associação/revisão de acesso, sem exigir ledger comercial nem simular uma cobrança bem-sucedida. Fence de sessão/tentativa é a proteção transacional contra callbacks após cancelamento, substituição e exclusão. Revalidação de conta antes de um efeito não equivale a uma transação coordenada com encerramento em outro módulo: essa garantia e seu produtor ficam deferidos, sem afirmação de linearização global. CI-09 comprova a guarda vigente; os checks de tentativa/exclusão continuam obrigatórios.

**Corpus, embedding e índice versionado.** Corpus é o conjunto pesquisável: exemplos de intenção, perguntas da base curada ou projeções não pessoais do catálogo. `MentorEmbeddingsProvider` transforma texto em vetor; `MentorIndexedEmbedding` liga esse vetor a corpus/referenceId/variationKey. `MentorEmbeddingsRepository` persiste e pesquisa esses registros, sem substituir o repository da entidade original. `MentorCatalogEntry` acrescenta tipo, título e vínculos permitidos para filtrar e localizar o item; dados atuais continuam sob a autoridade do módulo proprietário. Um índice é a coleção preparada para uma versão compatível do corpus/modelo/configuração; não é outra Skill nem uma cópia de todo o conteúdo. O manifesto vincula versão, revisão do modelo, dimensão e configurações. A preparação valida antes de ativar; requests não geram o corpus novamente. Um único repository atende os tipos indexados por filtros. CI-02 cobre correspondência, elegibilidade e versões pelo job; checks de build/migration verificam recursos e armazenamento.

**Intenção, candidato e decisão de rota (revisão16).** Intenção é um rótulo descritivo do pedido, podendo haver vários ou nenhum. O classificador retorna correspondências; o retriever retorna candidatos por BM25/embeddings e ranking RRF. Similaridade e ranking não são probabilidade de correção ou autorização. A rota combina candidatos com restrições/fatos do Core: resposta local, esclarecimento, recusa pedagógica ou abstinência determinística. Sem intenção identificada ainda pode haver resposta curada válida. Classificação/retrieval não alteram progresso, notas ou habilidades. Não há rota de geração ativa.

**Workflow Agno e revisão (deferidos na revisão16).** Código e testes desses componentes permanecem no repositório, mas não pertencem à composição ativa. O answer runtime retorna `UnavailableAnswerMentorMessageWorkflow` sem criar modelos ou clientes OpenRouter; a rota local sempre envia `generation_requests=()`. Uma revisão futura precisa de emenda própria antes de habilitar writer/reviewer, custos de inferência ou validação de qualidade. Nesta entrega, CI-07 comprova a barreira e a abstinência sem inferência.

**Progresso real de execução (revisão16).** A UI exibe somente o status genérico enquanto processamento local/consulta ocorre; não apresenta “Gerando resposta”, “Revisando resposta” ou “Consultando o currículo”, pois nenhum desses passos executa. `MentorWorkflowStep` e callbacks antigos são compatibilidade de código dormente. Nenhuma chamada ou tool é inferida da presença de fatos/referências no contexto.

`MentorResponseEvent.progress` e `MentorResponseSnapshot.progress` permanecem enum nullable por compatibilidade de persistência e leitura; resposta local não emite etapas de workflow. Estados terminais limpam progresso. Campos históricos `consultation`/`consultations` permanecem compatíveis, mas não alimentam o indicador; presença de contexto não cria etapa exibida.

**Outbox e execução assíncrona.** Outbox é o registro de entrega criado na mesma transação da aceitação, para evitar mensagem aceita sem solicitação de processamento. Seu evento transporta apenas attemptId; o job relê dados autorizados no backend. Checkpoints duráveis identificam etapas/estado sem armazenar histórico ou candidatos privados. Reexecução reutiliza blocos committed e orçamento persistido; idempotência de efeitos não promete uma única chamada externa em caso de crash. Cancelar a execução é uma operação de domínio separada de fechar SSE. Os testes do job e da aceitação/transação cobrem entrega, retomada e falhas.

**Estado Web, transporte e observabilidade (revisão16).** MentorContext e SSE mantêm estado/histórico/replay como já contratado. Langfuse, quando habilitado, observa somente duração, resultados, contagens allowlistadas e correlation UUID opaca; nenhum ID de conta/sessão ou conteúdo. Não há capture opt-in de conteúdo de resposta nesta revisão. Sua falha não muda a resposta. CI-08/CI-15 e VM-02 verificam as fronteiras ativas.

Árvore do recorte: `[N]` planejado, `[M]` existente. `{...}` representa arquivos individuais. Acrescentar `__init__.py`/exports nos pacotes pertinentes; helpers privados podem evoluir sem amendment. Cota completa e encerramento/revogação coordenados estão fora da árvore e não são dependências desta entrega.

```text
apps/server/
  [M] pyproject.toml; uv.lock
  rest-client/intelligence/[M] intelligence.rest
  src/shifu/
    [M] app.py
    shared/[M] settings.py
    intelligence/
      core/domain/
        entities/[N] mentor_response_attempt.py
        enums/[N] {mentor_response_status,mentor_response_event_kind,mentor_intent,mentor_workflow_step}.py
        structures/[N] {mentor_context_hint,mentor_submission,mentor_response_block,
          mentor_response_event,mentor_response_snapshot,mentor_intent_match,
          mentor_route_result,mentor_generation_request,mentor_review_result,
          mentor_indexed_embedding,mentor_embedding_match}.py
        structures/[M] mentor_session_detail.py
        events/[N] mentor_response_requested_event.py
        errors/[N] {mentor_response_pending_error,mentor_response_state_error,
          mentor_access_unavailable_error}.py; mentor_response_generation_error remains legacy/inactive
      core/interfaces/
        [M] intelligence_database.py; mentor_messages_repository.py
        [M15] mentor_telemetry_provider.py
        [N] {mentor_response_attempts_repository,mentor_response_events_repository,
          mentor_route_provider,answer_mentor_message_workflow,mentor_review_provider,
          mentor_embeddings_repository,mentor_embeddings_provider}.py
      core/use_cases/
        [M] {create_mentor_session,finalize_mentor_response,remove_mentor_session}_use_case.py
        [M15] process_mentor_response_use_case.py
        [N] {submit_mentor_message,cancel_mentor_response,retry_mentor_response,
          read_mentor_response_events}_use_case.py
      database/sqlalchemy/
        [M] intelligence_database.py
        models/[N] {mentor_response_attempt_model,mentor_response_event_model,
          mentor_catalog_embedding_model,mentor_faq_embedding_model,mentor_intent_embedding_model,
          mentor_index_version_model}.py
        repositories/[N] {mentor_response_attempts_repository,mentor_response_events_repository,
          mentor_embeddings_repository}.py
        repositories/[M] mentor_messages_repository.py
      rest/
        [M] router.py
        schemas/[M] mentor_session_schemas.py
        controllers/[M] create_mentor_session_controller.py
        controllers/[N] {submit_mentor_message,cancel_mentor_response,retry_mentor_response,stream_mentor_response}_controller.py
      pipes/[M] intelligence_pipe.py
      messaging/inngest/
        [N] intelligence_inngest_messaging.py
        jobs/[N] answer_mentor_message_job.py
      ai/
        agno/
          agents/[N] mentor_writer_agent.py
          outputs/[N] mentor_answer_block_output.py
          workflows/[N] agno_answer_mentor_message_workflow.py
        data/[N] {mentor-intents,mentor-answers,mentor-index-manifest,mentor-evaluation}.json
      providers/
        text_preprocessing/spacy/[N] spacy_mentor_text_preprocessor_provider.py
        retrieval/bm25/[N] bm25_mentor_hybrid_retrieval_provider.py
        intent_classification/embeddings/[N] embeddings_mentor_intent_classifier_provider.py
        routing/[N] local_mentor_route_provider.py
        embeddings/sentence_transformers/[N] sentence_transformers_embeddings_provider.py
        mentor_review_provider/openrouter/[N] openrouter_jev_mentor_review_provider.py
        telemetry/langfuse/[M15] langfuse_mentor_telemetry_provider.py
      [N] prepare_mentor_indexes.py
    shared/core/
      interfaces/[N] {mentor_context_provider,mentor_catalog_provider,mentor_access_provider}.py
      domain/structures/[N] {mentor_context_snapshot,mentor_catalog_entry,mentor_access_grant,mentor_usage}.py
    curriculum/providers/[N] curriculum_mentor_catalog_provider.py
    learning/providers/[N] learning_mentor_context_provider.py
    gamification/providers/[N] gamification_mentor_context_provider.py (facts available only)
    identity/providers/[N] identity_mentor_access_provider.py (active-account producer)
    shared/database/sqlalchemy/migrations/versions/[N] generated Alembic migration
  tests/
    fixtures/[M] postgres_fixture.py; inngest_fixture.py
    intelligence/core/use_cases/
      [M] test_{create_mentor_session,finalize_mentor_response,remove_mentor_session}_use_case.py
      [N] test_{submit_mentor_message,cancel_mentor_response,retry_mentor_response,process_mentor_response,
        read_mentor_response_events}_use_case.py
    intelligence/server/controllers/
      [M] conftest.py; test_create_mentor_session_controller.py
      [N] test_{submit_mentor_message,cancel_mentor_response,retry_mentor_response,stream_mentor_response}_controller.py
    messaging/inngest/jobs/intelligence/
      [M16] test_answer_mentor_message_job.py (local-only route and abstention; no inference)
      [M16] test_mentor_langfuse_sdk_job.py (actual Langfuse SDK OTLP export without identity/content)
    learning/core/use_cases/[M] test_{get_competency_detail,get_material_detail,get_choice_activity}_use_case.py
apps/web/
  src/routes/api/intelligence/mentor-sessions/$sessionId/[N] events.ts
  src/[M] routeTree.gen.ts (generated from new server route)
  src/rest/services/[M] intelligence-service.ts
  src/rest/fetch/[N] fetch-rest-stream-client.ts
  src/core/shared/interfaces/[N] rest-stream-client.ts
  src/core/intelligence/[N] mentor-response.ts
  src/provision/realtime/[N] native-mentor-event-source.ts
  src/provision/intelligence/[N] mentor-response-stream-server-provider.ts
  src/ui/intelligence/
    contexts/mentor-context/
      [M] index.tsx; use-mentor-context-provider.ts
      types/[M] mentor-context-value.ts
      tests/[M] use-mentor-context-provider.test.ts
    hooks/
      [M] use-create-mentor-session-action.ts; use-mentor-session-query.ts
      [M] use-mentor-context.ts
      [N] use-submit-mentor-message-action.ts; use-cancel-mentor-response-action.ts
      [N] use-retry-mentor-response-action.ts; use-mentor-response-stream.ts
    widgets/components/mentor-chat/
      [M] index.tsx
      conversation/
        [M] index.tsx; use-conversation.ts
        tests/[M] use-conversation.test.ts; conversation.test.tsx
        composer/
          [M] index.tsx; use-composer.ts
          tests/[M] use-composer.test.ts; composer.test.tsx
        message-list/message-item/
          [M] index.tsx
          [N] use-message-item.ts
          tests/[N] use-message-item.test.ts
          answer-block/[N] index.tsx (pure renderer)
          response-status/[N] index.tsx (pure renderer)
    widgets/components/mentor-fab/
      [M] index.tsx; use-mentor-fab.ts
      tests/[M] use-mentor-fab.test.ts; mentor-fab.test.tsx
    widgets/pages/intelligence-page/
      [M] index.tsx; use-intelligence-page.ts
      tests/[M] use-intelligence-page.test.ts; intelligence-page.test.tsx
  src/ui/shared/widgets/layouts/root-layout/[M] use-root-layout.ts
  tests/intelligence/[M] intelligence-page.test.ts
  tests/intelligence/[N] mentor-response-stream-api.test.ts
  tests/shared/[M] app-layout.test.ts
documentation/features/intelligence/mentor-context/[N] spec.md; design/handoff.md
[M] docker-compose.yaml (application PostgreSQL vector capability, planned change)
```

spaCy/modelo português, SentenceTransformers, pgvector, BM25 e Langfuse não são deps instaladas hoje. Resolver versões compatíveis com Python3.13/manifests via docs oficiais/Context7 na implementação; não trocar algoritmo/modelo aprovado. Já existem Agno/OpenAI/Inngest e Web `react-markdown`/`rehype-prism-plus`/Motion. Lockfiles/manifests só mudam conforme dependências realmente necessárias.

**Declarações Core.** Trechos fixam a superfície pública resultante, uma declaração por arquivo homônimo. Imports vêm dos pacotes Core correspondentes; `@structure` é o decorator existente. Apenas entidade tem `id` isolado; estrutura não é schema de framework.

```python
class MentorResponseStatus(StrEnum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class MentorResponseEventKind(StrEnum):
    STATUS = 'status'
    CONSULTATION = 'consultation'
    BLOCK = 'block'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class MentorIntent(StrEnum):
    EXPLAIN_CONCEPT = 'explain_concept'
    REQUEST_HINT = 'request_hint'
    CONSULT_PROGRESS = 'consult_progress'
    FIND_MATERIALS_ACTIVITIES = 'find_materials_activities'
    EXPLAIN_ASSESSMENT = 'explain_assessment'
    SEARCH_CURRICULUM = 'search_curriculum'
    CONSULT_GAMIFICATION = 'consult_gamification'
    LEARNING_CONVERSATION = 'learning_conversation'

@structure
class MentorContextHint:
    goal_id: str | None
    skill_id: str | None
    competency_id: str | None
    material_id: str | None
    activity_id: str | None

@structure
class MentorSubmission:
    submission_key: str
    content: str
    context_hint: MentorContextHint | None

@frozen_entity
class MentorResponseAttempt:  # immutable, named factory validates local invariants
    id: str
    account_id: str
    session_id: str
    learner_message_id: str
    status: MentorResponseStatus
    context_hint: MentorContextHint | None
    access_revision: str
    operation_key: str
    created_at: datetime
    updated_at: datetime

@structure
class MentorResponseBlock:
    block_key: str
    ordinal: int
    intent: MentorIntent | None
    content: str

# Legacy/wire-compatibility shapes only: MentorWorkflowStep,
# MentorGenerationRequest, MentorReviewResult, AnswerMentorMessageWorkflow, and
# MentorReviewProvider. Revision16 never instantiates/calls them or emits their
# steps/requests; generation_requests stays empty.
class MentorWorkflowStep(StrEnum):
    WRITE_ANSWER = 'write-answer'
    REVIEW_ANSWER = 'review-answer'

@structure
class MentorResponseEvent:
    session_id: str
    attempt_id: str
    sequence: int
    kind: MentorResponseEventKind
    status: MentorResponseStatus
    block: MentorResponseBlock | None
    consultation: str | None
    failure_code: str | None
    created_at: datetime
    progress: MentorWorkflowStep | None = None

@structure
class MentorResponseSnapshot:
    attempt_id: str
    learner_message_id: str
    status: MentorResponseStatus
    blocks: tuple[MentorResponseBlock, ...]
    consultations: tuple[str, ...]
    last_sequence: int
    failure_code: str | None
    progress: MentorWorkflowStep | None = None

@structure
class MentorIntentMatch:
    intent: MentorIntent
    similarity: float

@structure
class MentorRouteResult:
    intents: tuple[MentorIntentMatch, ...]
    local_blocks: tuple[MentorResponseBlock, ...]
    generation_requests: tuple[str, ...]
    clarification: str | None

@structure
class MentorGenerationRequest:
    session_id: str
    learner_message_id: str
    attempt_id: str
    requested_part: str
    history: tuple[MentorMessage, ...]
    context: MentorContextSnapshot
    approved_blocks: tuple[MentorResponseBlock, ...]
    correction: str | None

@structure
class MentorReviewResult:
    approved: bool
    criteria: tuple[tuple[str, str, float], ...]  # criterion, closed choice, confidence
    correction: str | None  # actionable feedback, not reasoning

class MentorRouteProvider(Protocol):
    def route(self, content: str, context: MentorContextSnapshot) -> MentorRouteResult: ...

class AnswerMentorMessageWorkflow(Protocol):
    def run(self, request: MentorGenerationRequest,
            usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
            inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None
    ) -> MentorResponseBlock: ...

class MentorReviewProvider(Protocol):
    def review(self, request: MentorGenerationRequest,
               candidate: MentorResponseBlock) -> MentorReviewResult: ...

@structure
class MentorIndexedEmbedding:
    corpus: str  # closed intents/answers/curriculum
    reference_id: str
    variation_key: str
    vector: tuple[float, ...]

@structure
class MentorEmbeddingMatch:
    reference_id: str
    variation_key: str
    similarity: float

class MentorEmbeddingsProvider(Protocol):
    def embed_queries(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...
    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...

class MentorEmbeddingsRepository(Protocol):
    def prepare_version(self, version: str, vectors: tuple[MentorIndexedEmbedding, ...]) -> None: ...
    def activate_version(self, version: str) -> None: ...
    def find_nearest(self, corpus: str, version: str, query: tuple[float, ...],
                     eligible_references: tuple[str, ...]) -> tuple[MentorEmbeddingMatch, ...]: ...
```

**Contrato ativo (revisão16):** o roteador local devolve apenas blocos curados/contextuais autorizados, esclarecimento, recusa pedagógica ou abstinência determinística. Não há workflow de geração/revisão na composição ativa; `generation_requests` é sempre vazio e respostas completas derivam dos blocos locais. `MentorSessionDetail` conserva `session/messages/pending_learner_message_id` e adiciona `response: MentorResponseSnapshot | None`. `MentorMessage` conserva shape/conteúdo exato; parcial não é resposta concluída. Final concatena blocos locais em ordem e conserva reply único. O contrato Agno/JEV descrito no histórico das emendas anteriores está dormente e não autoriza inferência nesta revisão.

Portas Shared usam snapshots neutros imutáveis; nenhum import de Intelligence Hint ou entidades de negócio. Produtores retornam somente fatos/campos permitidos, nunca blob de estado completo.

```python
@structure
class MentorAccessGrant:
    account_id: str
    access_revision: str
    operation_key: str

@structure
class MentorUsage:
    operation_key: str
    attempt_id: str
    used_tokens: int
    cancelled: bool

@structure
class MentorCatalogEntry:
    reference_id: str
    kind: str  # closed skill/competency/material/activity
    skill_id: str
    competency_id: str | None
    title: str
    description: str | None
    concept_ids: tuple[str, ...]
    source_version: str

@structure
class MentorContextSnapshot:
    goal_id: str | None
    skill_experience_id: str | None
    skill_id: str | None
    competency_id: str | None
    activity_id: str | None
    skill_completed: bool | None
    diagnostic_in_progress: bool
    facts: tuple[tuple[str, str], ...]  # closed allowlist, not arbitrary state
    eligible_references: tuple[str, ...]
    resolved_references: tuple[str, ...]
    unavailable_sources: tuple[str, ...]

class MentorAccessProvider(Protocol):
    def authorize(self, account_id: str, operation_key: str) -> MentorAccessGrant: ...
    def assert_current(self, grant: MentorAccessGrant) -> None: ...
    def record_usage(self, grant: MentorAccessGrant, usage: MentorUsage) -> None: ...

class MentorContextProvider(Protocol):
    def read(self, account_id: str, reference_ids: tuple[str, ...], *,
             goal_id: str | None = None, skill_id: str | None = None,
             competency_id: str | None = None, material_id: str | None = None,
             activity_id: str | None = None) -> MentorContextSnapshot: ...

class MentorCatalogProvider(Protocol):
    def read_projection(self) -> tuple[MentorCatalogEntry, ...]: ...
    def search(self, account_id: str, query: str,
               eligible_references: tuple[str, ...]) -> tuple[MentorCatalogEntry, ...]: ...
```

Chaves de `facts` fechadas por capability no produtor; ausência vira indisponibilidade, não zero. Não transportar avaliação/resposta diagnóstica individual. Identity fornece revisão/estado real de conta pela porta neutra; composição injeta o produtor sem deslocar regra para Shared. `authorize` concede leitura/envio/retry para conta ativa, e `assert_current` rejeita conta ausente/inativa ou revisão divergente em cada ponto de guarda. `record_usage` não depende de cota: valida o grant e a associação do uso à operação, mantendo a assinatura, enquanto Intelligence persiste recibos técnicos. Estado Identity inacessível falha seguro; produtor de cota ausente não é erro. A checagem anterior à transação não prova revogação coordenada com encerramento; nenhuma garantia desse tipo integra a aceitação deste recorte. Fence de sessão/tentativa/exclusão e guards existentes continuam obrigatórios.

**Use cases/repositórios.** Construtores recebem `IntelligenceDatabase`, portas usadas, Clock/Identifier; nenhum SDK/environment. Assinaturas resultantes (nomes existentes conservados):

```python
CreateMentorSessionUseCase.execute(account_id: str, submission_key: str,
    first_message: str, context_hint: MentorContextHint | None = None
) -> CreateMentorSessionResult  # existing detail/created, extended Detail

SubmitMentorMessageUseCase.execute(account_id: str, session_id: str,
    submission: MentorSubmission) -> MentorSessionDetail

CancelMentorResponseUseCase.execute(account_id: str, session_id: str,
    attempt_id: str, submission_key: str) -> MentorResponseSnapshot

RetryMentorResponseUseCase.execute(account_id: str, session_id: str,
    attempt_id: str, submission_key: str) -> MentorResponseSnapshot

ProcessMentorResponseUseCase.execute(attempt_id: str) -> MentorResponseStatus

ReadMentorResponseEventsUseCase.execute(account_id: str, session_id: str,
    after_sequence: int) -> tuple[MentorResponseEvent, ...]

FinalizeMentorResponseUseCase.execute(account_id: str, session_id: str,
    learner_message_id: str, content: str, attempt_id: str) -> bool
```

Cancelamento e repetição são ações/use cases/controllers distintos; não manter overload de finalização sem fence. Tentativas repository: `find_current(account_id, session_id) -> MentorResponseAttempt | None`, `find_by_id_for_update(attempt_id) -> MentorResponseAttempt | None`, `add(attempt) -> None`, `transition(attempt_id, expected_status, new_status, access_revision) -> bool`, `remove_by_session_id(session_id) -> None`. Eventos repository: `append(event) -> None`, `find_after(account_id, session_id, sequence) -> tuple[MentorResponseEvent,...]`, `snapshot(account_id, session_id) -> MentorResponseSnapshot | None`, `remove_by_session_id(session_id) -> None`. Types são os definidos acima, sem objetos de infraestrutura. Acrescentar leitura privada cronológica completa ao messages repository; HTTP continua paginação30. Alocação privada de sequência/locks pode variar sem mudar garantias.

Erros novos seguem AppError, com atributos anotados `message: str` e `title: str` e overrides seguros; sem HTTP types no Core. Taxonomia atual: pendente/estado inválido409conflict; estado de acesso indeterminado503service_unavailable (não ausência de cota deferida); input Core400validation_error / REST422. Não existe erro de “geração indisponível” nesta revisão porque a rota não tenta gerar. Reusar erro existente de sessão/chave; estrangeiro/inexistente404not_found. Não vazar erro bruto de provider nem mudar envelope dos endpoints antigos.

**HTTP.** Prefixo `/intelligence/mentor-sessions`, conta por SharedPipe autenticada. No-store em sucesso/erro/stream; ULID recursos, UUIDv4 submissão; extras proibidos, nonblank após trim com armazenamento exato. Hint opcional snake_case e campos opcionais/null. Sem nova política pedagógica de tamanho/truncamento; estouro de capacidade do perfil é falha tipada, sem cortar histórico.

| Método / caminho | Entrada | Sucesso / resultado |
| --- | --- | --- |
| `POST /` existente | `{submission_key,first_message,context_hint?}` | Detail queued;201novo/200replay; mensagem/tentativa/outbox atômicos |
| `POST /{session_id}/messages` | `{submission_key,content,context_hint?}` | Detail;202aceito/200replay; pendente distinto409 |
| `POST /{session_id}/responses/{attempt_id}/cancel` | `{submission_key}` | Snapshot cancelled;200/replay; completed/obsoleta409 |
| `POST /{session_id}/responses/{attempt_id}/retry` | `{submission_key}` | Nova queued;202/200replay; apenas failed/cancelled |
| `GET /{session_id}` existente | cursor opcional | Detail com snapshot;200; não enfileira |
| `GET /{session_id}/events` | Last-Event-ID opcional não negativo | 200SSE privado; autenticar antes e revalidar durante conexão |

List/rename/delete conservam contrato; delete apaga blocos/eventos privados e mantém tombstone mínimo. Cancel versus finalize lineariza sob mesmo lock: cancel que vence impede conclusão; completed não é cancelado retroativamente. Fingerprint versionado inclui texto exato+hint canônico (ausente≡null). Preservar replay legado SHA-256 só do texto, sem hint; nunca reinterpretar hash antigo. Retry tem chave/tentativa nova, mesma mensagem/operation_key de medição técnica, conta ativa e revisão atuais obrigatórias, sem autorização de saldo mensal.

SSE `id:<sequence>` / `event:mentor.response` / data snake_case MentorResponseEvent. `kind` fechado; consultation somente learning/curriculum/gamification traduzido genericamente pt-BR, sem tool details. Falha sanitizada; somente blocos locais autorizados, nunca tokens nem etapas de geração/revisão. Heartbeat técnico sem sequência de domínio. Last-Event-ID é sequência numérica no recurso autorizado, não cursor que prova sessão de origem; rejeitar sequência malformada/negativa e recurso estrangeiro, sem prometer detectar origem de um número isolado. Eventos obsoletos/duplicados não regressam UI. Redis desperta, Postgres faz replay/reconciliação periódica. BFF cookie same-origin, token upstream só no servidor. `.rest` adiciona create com/sem hint, submit/replay/conflito/cancel/retry/SSE cursor; usar variáveis privadas, sem chaves reais.

**Persistência.** Mesmo UoW/Session para mensagem+tentativa+outbox; rollback não publica. Reusar EventsRepository/broker existente, ID estável/retries; nenhum send direto à Inngest na transação. Tabelas novas attempts/events com FKs de associação mensagem/sessão, unique parcial queued/processing por sessão, unique de submissão escopada, `(session_id,sequence)` único, `(attempt_id,block_key)`/ordinal únicos. Conservar reply único existente. Publicar bloco/evento em commit atômico com status/tentativa/revisão atuais; CAS rejeita callbacks antigos.

Snapshot somente da tentativa atual. Cancel/retry remove texto/consultas parciais antigos, inclusive dos eventos recuperáveis; cursor não revive conteúdo descartado. Controles antigos minimizados podem permanecer até exclusão. Criar migration aditiva por `uv run poe db:migrate "add mentor contextual responses"` em base isolada, nome real gerado. Extensão pgvector compatível PostgreSQL17; cosine exato inicialmente, sem ANN. Legado concluído conserva mensagens; learner sem resposta recebe estado recuperável para retry, sem geração/enfileiramento em massa na migration. Upgrade/downgrade/backfill/constraints em Testcontainer; sem reset/reseed compartilhado/migration apagada.

**PLN.** SentenceTransformers `intfloat/multilingual-e5-small`,384dim normalizado/cosine exato pgvector. Prefixos/revisão/config oficial do modelo versionados no manifesto. A consulta local pode remover introduções neutras ancoradas (saudação e “tenho uma dúvida,”) e capitalizar a inicial exposta, preservando o conteúdo substantivo e a negação. Mensagem persistida e histórico conservam o texto original. Essa normalização não altera corpus, limiares ou margem nem garante reconhecimento de qualquer paráfrase. spaCy `pt_core_news_sm` tokeniza/lematiza lexical, stopwords preservam negação. Sem treinamento supervisionado ou extração livre de trechos obrigatória.

Curriculum é produtor da projeção allowlist; seu `search` faz somente descoberta textual e leitura atual dos próprios campos, não consulta banco/modelo privado de Intelligence. Learning produz elegibilidade. Classificação e ranking híbrido pertencem a Intelligence: providers NLP recebem portas `MentorEmbeddingsProvider`/`MentorEmbeddingsRepository`. O primeiro gera embeddings de queries/passages pelo modelo local; o repository persiste versões e consulta embeddings de intenções/FAQ/catálogo, por adapter SQLAlchemy. SQL/pgvector ficam nesse adapter, sem acesso direto a DB no workflow Agno legado ou autorização de dados no provider NLP. Limite de busca é aplicado após filtro de elegibilidade. Preparação recebe corpus não pessoal pela porta de projeção e grava por repository, sem importar entidades Curriculum. Métodos de preparo/ativação não ficam no browser nem em tools do agente. Providers locais produzem candidatos; somente Core/produtores autorizam seu uso.

O Postgres da aplicação e fixtures `postgres_fixture.py`/`inngest_fixture.py` hoje usam PostgreSQL17 sem vector. Implementação deve disponibilizar extensão no runtime17 da aplicação e nos containers de teste antes das migrations, com imagem/build compatível e versionado verificado pelas docs oficiais. Não trocar Postgres de Sonar/Langfuse, apagar volume ou resetar dados. Transição de imagem/extension e dados legados exige prova descartável antes de qualquer recriação autorizada do serviço compartilhado. Presença de tabela/migration não prova extensão disponível.

`mentor-intents.json`: objeto simples, labels ingleses do enum → arrays pt-BR. Mensagem comparada a todos os exemplos; cada label usa máximo cosine e limiar próprio calibrado. Sem top-K global suprimindo segunda intenção. Similaridade não é probabilidade/permissão; desconhecida ainda permite FAQ/esclarecimento.

`mentor-answers.json`: array simples com **id/question/variations/answer/topics**, IDs estáveis, respostas editoriais pt-BR. Sem usage_conditions, regra de pré-requisito ou solução de Atividade do catálogo. Exemplo:

```json
[{"id":"python_lists","question":"O que é uma lista em Python?","variations":["Como funciona list em Python?"],"answer":"Uma lista reúne elementos em uma sequência que pode ser alterada.","topics":["python","lists"]}]
```

JSON é fonte carregada uma vez; Postgres guarda vetor/ID/variação/versão, não respostas JSONB. Vetor de python_lists referencia essa entrada da versão exata; incompatível não usa conteúdo novo com vetor antigo. Preparo dedicado `uv run python -m shifu.mentor_indexes` fora do request calcula hash corpus/config, carrega/valida tudo e ativa atomicamente. O entrypoint da aplicação compõe os produtores e chama o helper Intelligence `prepare_mentor_indexes`, preservando Tach; ajuste técnico de localização, sem mudança de comportamento ou checker. Startup não reconstrói/treina; índice ausente/incompatível não usa matches stale nem tenta geração remota: a rota permanece determinística e responde apenas com informação local ainda elegível, esclarecimento ou abstinência.

Empacotar JSON de produção e manifesto por package-data do setuptools em pyproject.toml e carregá-los via recursos do pacote, não cwd do checkout. Pesos externos do modelo não integram wheel/sdist; resolução/cache/revisão do modelo são server-only. Build precisa conferir presença/leitura dos recursos nas distribuições, não apenas exit0 de uv build.

FAQ BM25 pergunta/variações (não answer) + vetorial, dedup por entrada com melhor posição, fusão **RRF** antes da decisão. O fast path conserva cosine≥0.90/margem≥0.025 e concordância RRF. Quando ele abstém, a seleção pode comparar até seis candidatos cosine≥0.85 usando CrossEncoder local multilíngue, sobre pergunta editorial, suas variações já curadas e resposta. O candidato precisa estar no top3 semântico, ter logit≥3 e margem de logits≥2; esses parâmetros de desenvolvimento e a revisão fixa do modelo são versionados no manifesto, sem significado probabilístico nem alegação de calibração geral. Evidência insuficiente, asset ausente ou saída inválida abstêm-se; esclarecimento local elegível permanece. Preparação explícita resolve os pesos antes da ativação do índice; requests somente usam cache existente e nunca truncam o par pergunta/candidato. RRF não confiança; 0,70 de Variskill não precisão medida. Held-out separado do desenvolvimento: ≥95% `respostas locais corretas / selecionadas`, reportando denominador/cobertura/abstenção; meta de qualidade da recuperação local desta entrega, não meta canônica para todas as mensagens.

A resolução local é por parte da mensagem: uma FAQ suficiente não acrescenta templates ou esclarecimentos provocados por rótulos incidentais dessa parte. Consultas locais em outras partes continuam independentes; qualquer parte sem evidência recebe esclarecimento ou abstinência local, sem geração. A análise gramatical spaCy preserva negações: partes que negam um pedido não disparam a consulta negada, e referências sem antecedente como “isso”/“aquilo” não selecionam FAQ por similaridade isolada. Texto persistido/histórico permanece original. Implementação interna adicional, com portas externas do Mentor inalteradas:

```text
apps/server/src/shifu/
├── intelligence/core/interfaces/mentor_faq_reranker_provider.py [N]
├── intelligence/providers/retrieval/sentence_transformers/sentence_transformers_mentor_faq_reranker_provider.py [N]
├── intelligence/providers/retrieval/bm25/bm25_mentor_hybrid_retrieval_provider.py [M]
├── intelligence/providers/routing/local_mentor_route_provider.py [M]
├── intelligence/providers/text_preprocessing/spacy/spacy_mentor_text_preprocessor_provider.py [M]
├── intelligence/ai/data/mentor_resources.py [M]
├── intelligence/ai/data/mentor-index-manifest.json [M]
├── intelligence/ai/data/mentor-evaluation.json [M]
├── composition/lazy_mentor_route_provider.py [M]
└── mentor_indexes.py [M]
apps/server/tests/messaging/inngest/jobs/intelligence/test_answer_mentor_message_job.py [M]
```

`MentorFaqRerankerProvider.score(content: str, documents: tuple[str, ...]) -> tuple[float, ...]` é porta Intelligence para relevância dos candidatos editoriais, sem acesso a estado ou permissão. O adapter retorna logits finitos na mesma ordem; composição injeta uma instância local com carga lazy e serialização do SDK. Sem chamadas OpenRouter, novos agentes, persistência pessoal ou dependência obrigatória do reranker para respostas já aceitas pelo fast path. Consumidores nativos verificam paráfrases independentes, incerteza contra todas as FAQs, múltiplas partes e falhas do SDK; sem testes diretos de provider.

Catálogo não pessoal: Skill nome/descrição; Competência nome/descrição/vínculo; Material título/conceitos/origens de sequência (modelo atual não tem descrição); Atividade **learning** título/objetivo/conceitos requeridos. Excluir body/enunciados/perguntas/arquivos/rubricas/gabaritos/diagnósticos. Material multiorigem por CurriculumSequence.items, sem FK inventada. Learning fornece elegibilidade antes de ranking/top-K, conteúdo liberado não depende apenas de foco/domínio atual. Competência bloqueada ajuda achar Skill internamente, não é exibida. Goals/experiências pessoais usam nomes/IDs textual, sem embeddings pessoais.

**Agno — contrato histórico/deferido, não ativo na revisão16.** Os componentes writer, reviewer, loop de duas versões, seis critérios e o respectivo workflow permanecem no repositório como implementação legada. A rota/runtime de produção não os compõe, não cria clientes/modelos, não envia geração/revisão e não publica resultados desses componentes. As declarações de tipos/protocolos acima são compatibilidade de código e persistência; CI-16 não é um gate de release desta revisão.

Critérios históricos/deferidos: aderência ao pedido; fidelidade a fatos; solução cumulativa; diagnóstico; conteúdo bloqueado/privacidade; alegações de ações/avaliações oficiais. Não existe decisão de reviewer no caminho de produção desta revisão.

**Histórico JEV até revisão13, fora do runtime Mentor atual:** aderência ao pedido; fidelidade a fatos; solução cumulativa; diagnóstico; conteúdo bloqueado/privacidade; alegações de ações/avaliações oficiais. Cada critério exige opção approved e confidence≥0.75, inclusive no valor exato, sem média compensatória; revisão9 define o mesmo limiar para os seis critérios por decisão explícita do usuário. Confidence não é precisão da resposta nem probabilidade da opção vencedora. Os seis valores0.75 substituem os históricos0.89 e0.95 pela decisão expressa do usuário. CI-16 observou um caso inconclusivo aprovado no critério diagnostic_safety com confiança0.89 na segunda versão; portanto o novo limiar0.75 também não é apresentado como seguro/calibrado. A aprovação isolada de um critério não prova publicação conjunta, que exige todos os seis. A evidência Failed de seleção permanece e bloqueia uma afirmação de qualidade calibrada. A calibração de FAQ/intenção não comprova calibração JEV. Prefixo inclui histórico+aprovados locais/gerados. Máximo **uma correção e segunda revisão** (duas versões/bloco). Timeout/429/5xx JEV: dois retries adicionais/backoff crescente, separados das versões. Inconclusivo/schema/opção inválida não aprovam nem viram retry transitório. Sem fallback JEV; falha mantém learner. Falha de bloco posterior deixa anteriores aprovados como parcial failed, não completed; cancel/retry descarta tudo parcial.

Perfis aprovados na revisão14: gerador e revisor Agno separados GPT-6 Luna, fallback técnico OpenRouter/DeepSeek somente para o gerador. Perfil não prova ID comercial/suporte Agno/ZDR: composição resolve IDs e controles oficiais do endpoint efetivo antes de habilitar; sem prova, inelegível/falha tipada, não substituir por modelo não aprovado. Settings centralizadas/lifespan/long-lived, sem env por agente. Memória/persistência Agno de prompts/raw outputs desligada. Fallback só falha técnica elegível, nunca retry ilimitado por qualidade.

**Job.** Evento `MentorResponseRequestedEvent`, nome `intelligence/mentor.response.requested`, payload estrito `{attempt_id:ULID}`, EventID/UTC pelas portas. Job `AnswerMentorMessageJob`: FUNCTION_ID `intelligence-answer-mentor-message`, _EVENT_NAME correspondente, handle conforme padrão instalado. `IntelligenceInngestMessaging` retorna funções à única InngestMessaging.register de app.py. Job encontra conta/sessão no DB, não no browser/payload.

Durable steps só IDs/status/checkpoints; mensagens/contexto/prompts/candidato/review não entram em payload/output/cache Inngest. Inferência/revisão transitória privada; aprovados DB. Retomada pula blocos committed por chave, revalida estado/fatos/acesso; effects/recibos técnicos idempotentes, sem prometer exactly-once externo se crash antes do commit. Persistir budgets necessários para redelivery não reiniciar loop infinito. Falha terminal torna failed, não queued eterna. SDK/DB síncronos via padrão thread/step instalado, sem bloquear event loop ou compartilhar Session entre threads; UoW novo por trecho.

**Web.** MentorContext existente no RootLayout compartilha sessão/draft/chave/snapshot/sequence e registro de apresentação página/FAB. Provider não chama consumer hook. Query lê detalhe/histórico; create/submit escreve; ações cancel/retry separadas; reconciliar detalhe/lista por atividade sem perder paginação. SSE só atualiza sessão/tentativa atual; reconnect/close não gera retry. Sem browser storage/cache persistente privado.

```typescript
type MentorContextHint = {
  goalId: string | null; skillId: string | null; competencyId: string | null
  materialId: string | null; activityId: string | null
}
type MentorResponseStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
type MentorWorkflowStep = 'write-answer' | 'review-answer'
type MentorResponseBlock = { blockKey: string; ordinal: number; intent: string | null; content: string }
type MentorResponseSnapshot = {
  attemptId: string; learnerMessageId: string; status: MentorResponseStatus
  blocks: MentorResponseBlock[]; consultations: string[]; lastSequence: number; failureCode: string | null
  progress?: MentorWorkflowStep | null
}
type SubmitMentorMessageInput = { submissionKey: string; content: string; contextHint: MentorContextHint | null }
// Additions scoped to existing Detail/value; existing fields retained.
type MentorSessionDetailAddition = { response: MentorResponseSnapshot | null }
type MentorContextValueAddition = {
  response: MentorResponseSnapshot | null
  submitMessage(input: SubmitMentorMessageInput): Promise<void>
  cancelResponse(): Promise<void>
  retryResponse(): Promise<void>
  shouldAnimateBlock(attemptId: string, blockKey: string): boolean
  markBlockPresented(attemptId: string, blockKey: string): void
}
```

Contratos públicos novos (Hint/Status/Block/Snapshot/Submit e evento de resposta) pertencem a `src/core/intelligence/mentor-response.ts`; DTOs privados snake_case ficam no serviço REST, e a adição do context value fica no arquivo de tipo do contexto existente. Não mover estado React ou detalhes HTTP para Core. Zod/server functions validam shapes/IDs/enum/hint, nunca identidade browser. As server functions afetadas ficam em escopo de módulo nos respectivos hooks de criação/leitura/submit/cancel/retry, fora do corpo React, usando createServerFn e autenticação server-only. Não criar nem ampliar um arquivo agregador de server functions. Os handlers delegam autenticação e obtenção do serviço REST à composição server-only de provision, ampliando mentor-response-stream-server-provider.ts também para as operações autenticadas; não constroem AxiosRestClient nem IntelligenceService nos hooks. O arquivo legado mentor-server-functions.ts permanece fora do recorte: consumidores de criação/leitura passam a usar as funções colocadas nos próprios hooks; operações legadas não afetadas e seus consumidores são preservados. Importações e execução de getRequest/Better Auth/configuração/REST autenticado devem permanecer restritas ao handler server-only, sem credenciais ou dependências servidor no bundle cliente; CI-08/CI-15 provam o comportamento pelos consumidores e handlers. REST service adiciona submit/cancel/retry e DTO mapping camelCase↔snake_case. A factory `NativeMentorEventSource` em `src/provision/realtime/native-mentor-event-source.ts` só constrói o EventSource same-origin pela URL privada do BFF. `use-mentor-response-stream` na funcionalidade possui subscribe/unsubscribe, parsing/validação, mapeamento, retry/reconnect/cleanup, sem expor controles de transporte aos widgets. O contexto recebe snapshot/eventos de domínio; nenhum teste dedicado ao hook/factory.

**Contrato do hook de stream.** `useMentorResponseStream` pertence a `src/ui/intelligence/hooks/use-mentor-response-stream.ts` e é chamado apenas pelo hook do provider MentorContext, sem consumir `useMentorContext` e sem criar outro proprietário do snapshot. Widgets consomem o contexto; não abrem conexões próprias. A factory de transporte é uma dependência técnica browser-safe, composta fora do hook; autenticação continua por cookie same-origin.

```typescript
// Core: src/core/intelligence/mentor-response.ts
export type MentorResponseEvent = {
  sessionId: string; attemptId: string; sequence: number
  kind: 'status' | 'consultation' | 'block' | 'completed' | 'failed' | 'cancelled'
  status: MentorResponseStatus; block: MentorResponseBlock | null
  consultation: string | null; failureCode: string | null; createdAt: string
  progress?: MentorWorkflowStep | null
}
// UI: use-mentor-response-stream.ts; React state is not a Core contract
export type UseMentorResponseStreamInput = {
  sessionId: string | null; attemptId: string | null
  enabled: boolean; afterSequence: number
  openEventSource(sessionId: string, afterSequence: number): EventSource
  onEvent(event: MentorResponseEvent): void
  reconcile(): Promise<MentorResponseSnapshot | null>
  onUnavailable(): void
}
export function useMentorResponseStream(input: UseMentorResponseStreamInput): void
```

O hook não retorna comandos de transporte nem snapshot: entrega eventos validados ao provider, que aplica o estado de domínio e atualiza o cursor. Assina somente sessão/tentativa ativa, conta autenticada e conexão habilitada; o provider desabilita a assinatura ao sair/trocar conta. Um único EventSource por assinatura; callbacks instáveis ou avanço de afterSequence não reabrem a conexão. A sequência fornecida na abertura é a última aplicada pelo provider, não um cursor de outro recurso.

O listener de `mentor.response` valida DTO snake_case, converte para o evento camelCase acima e só entrega eventos da sessão/tentativa atuais com sequência maior que a última aceita. Heartbeats não alteram domínio. Atualiza o cursor antes de entregar um evento válido; payload inválido não avança cursor de aplicação nem produz texto. Eventos antigos/duplicados e callbacks atrasados de assinatura encerrada são ignorados. Em evento terminal completed/failed/cancelled fecha a conexão após entrega; cancelamento de transporte não envia cancelamento de resposta nem reenvia mensagem.

Em payload inválido, fecha imediatamente a conexão e invalida seus callbacks antes de reconciliar: o Last-Event-ID nativo pode já conter um ID não validado. Após leitura autorizada e aplicação do snapshot, abre no máximo uma conexão nova a partir do lastSequence autoritativo se a tentativa segue ativa. Em falha de transporte, suspende/fecha a conexão e invalida callbacks antes da leitura; reconcilia pelo query de detalhe autenticado existente; o provider aplica o snapshot atual. Há no máximo uma reconciliação em andamento por assinatura; erros repetidos não iniciam leituras concorrentes. Reconciliações são serializadas por assinatura; respostas atrasadas só são aplicadas se sessão/tentativa/conta continuam atuais e nunca reduzem lastSequence nem removem blocos já aceitos. Ao confirmar estado terminal/ausente ou perda de acesso, suspende a assinatura e invalida qualquer reconciliação pendente; o provider não reabre uma assinatura suspensa por simples rerender. Se a tentativa continua ativa e o acesso é válido, a recuperação retoma a partir da sequência persistida; EventSource nativo conserva Last-Event-ID enquanto a conexão é válida; uma recuperação controlada que fecha a conexão usa nova abertura com o cursor reconciliado, sem um segundo loop concorrente de retry. Se a leitura falha por acesso expirado/revogado ou confirma tentativa encerrada/ausente, fecha e suspende a assinatura; onUnavailable comunica indisponibilidade sanitizada pelo provider quando aplicável, sem transformar falha de conexão em falha persistida da tentativa. Não inferir status HTTP pelo error do EventSource, que não o expõe. Cleanup remove listeners, fecha EventSource e invalida callbacks/reconciliações pendentes em unmount, troca de sessão/tentativa/conta ou desabilitação. Nenhum conteúdo privado em storage/logs.

CI-08 cobre esse contrato pelos consumidores/contexto existentes: abertura única, rerender sem reconexão, parsing, isolamento, replay/dedup, terminal, falha/reconciliação/autenticação e cleanup; CI-15 cobre o handler BFF. Sem suite dedicada ao hook ou factory.

BFF `/api/intelligence/mentor-sessions/$sessionId/events` autentica cookie pelo mecanismo protegido Better Auth já utilizado nas server functions Mentor; não token em URL/browser nem Axios/fetch ad hoc em provision. O provision server-only compõe o IntelligenceService existente com o RestClient e um cliente REST de stream estreito; handler registrado delega acesso à sessão e encaminha somente corpo/headers seguros. O RestClient/Axios atual é buffered e não será usado como stream. Contrato adicional independente, sem mudar consumidores do RestClient existente:

```typescript
// src/core/shared/interfaces/rest-stream-client.ts; standard Web types, no vendor SDK
interface RestStreamClient {
  getStream(url: string, options: {
    headers: Record<string, string>; signal: AbortSignal
  }): Promise<RestResponse<ReadableStream<Uint8Array>>>
}
// src/rest/services/intelligence-service.ts; scoped additions, existing members unchanged
// Factory: IntelligenceService(restClient: RestClient, streamClient?: RestStreamClient)
type IntelligenceServiceStreamingMembers = {
  openMentorResponseEvents(accessToken: string, input: {
    sessionId: string; afterSequence: number
  }, signal: AbortSignal): Promise<ReadableStream<Uint8Array>>
}
```

`IntelligenceService` mantém os membros existentes e acrescenta openMentorResponseEvents; o segundo argumento opcional preserva os consumidores atuais de um argumento. A composição BFF injeta obrigatoriamente RestStreamClient; ausência dessa dependência ao abrir stream produz erro de configuração tipado, sem fallback buffered. Nenhum serviço REST separado de streaming é criado. `FetchRestStreamClient` em REST traduz streaming/erros ao RestResponse existente; service usa isFailure/throwError e corpo direto, sem validar sucesso ou regra de negócio. Provision só constrói/injeta, não implementa cliente HTTP. BFF GET aceita `after_sequence` não negativo para a abertura inicial via EventSource; Last-Event-ID válido tem precedência nas reconexões e é encaminhado upstream. O server SSE segue o header do contrato HTTP. Handler aplica text/event-stream/no-store, não repassa Set-Cookie/auth/headers de provider, não bufferiza o corpo; disconnect propaga AbortSignal upstream sem cancelar a tentativa Inngest. Autenticação expirada/revogada não entra em loop cego de reconexão. Prova pelo HTTP-handler CI-15, sem testes do provider/service/client. Regenerar route tree pela geração TanStack configurada, sem edição manual.

Composer surface page/fab chega ao hook. No FAB capturar IDs de matches Learning reconhecidos no envio: goalId/skillId curricular e opcionais competencyId/materialId/activityId; backend resolve experiência. Outras páginas null. Não enviar HTML/estado da página/attemptId/diagnosticRunId. RootLayout fornece contexto de matches sem ciclo; retry mantém hint imutável.

MessageItem owns typing em use-message-item, com timer só foreground novo e registry no contexto contra remount. AnswerBlock/ResponseStatus puros sem testes/hooks fictícios; props bloco/snapshot/flag e callbacks de contexto, sem SDK. Markdown allowlist/skipHtml/Prism/token existente; código rola localmente/foco quando necessário. Texto aprovado completo acessível; visual typing não live-region por caractere. Reduced motion completo. UI falha preserva learner/Tentar novamente e bloqueia composer pending.

**Langfuse (revisão16):** registrar somente spans operacionais de classificação, recuperação, contexto autorizado, roteamento e persistência/publicação local, com duração, correlation ID opaco, contagens e resultado allowlisted. Não criar generations/costs, pois não ocorre inferência de resposta. Não anexar account/user IDs, session IDs, conteúdo do aprendiz, prompts, candidatos, respostas ou atributos de modelo; correlação não deve permitir reconstruir identidade. Cliente ausente, disabled ou throwing não altera a resposta local. A prova SDK verifica export real sem atributos de identidade ou conteúdo privado. Retenção/deleção de metadata operacional não é declarada por essa prova. Chaves ficam somente em configuração local; sem proxy.

## Runtime Flow (revisão16)

```mermaid
sequenceDiagram
    participant W as MentorContext / BFF
    participant A as Intelligence REST / Core
    participant D as Postgres / outbox
    participant J as Inngest job
    participant C as Portas autorizadas
    W->>A: Envio autenticado + chave + hint
    A->>C: Autorizar conta ativa/revisão
    A->>D: Lock; mensagem + tentativa + evento
    A-->>W: Detail queued
    D->>J: Broker publica ID estável
    J->>D: Carregar tentativa atual
    J->>C: Revalidar acesso / consultar fatos
    J->>J: Intenções + FAQ/busca + resolver partes
    alt FAQ/fatos/esclarecimento/recusa local
        J->>D: Bloco local e evento aprovados
    else Sem resposta local confiável
        J->>D: Abstinência determinística e evento aprovado
    end
    J->>C: Revalidar fatos/acesso
    J->>D: Commit cercado por tentativa/revisão
    W->>A: SSE / replay autenticado
    A->>D: Ler sequência persistida
    A-->>W: Blocos / status
    J->>D: Única conclusão ou failed
```

Resolver: explícito válido → referência inequívoca estruturada da sessão → hint validado → busca autorizada → esclarecimento. Não interpretar texto histórico livre como fato oficial. Multi-intenção compõe uma resposta com blocos; Skill sugerida é orientação/link, sem adição/card de ação. Guardas reais de conta/revisão no aceite/retomada/antes de consulta/inferência/publicação; fence de sessão/tentativa/exclusão atomicamente no efeito. Mudança pedagógica/permissão detectada antes do publish descarta candidato. Perda de acesso detectada/exclusão fecha stream/invalida tentativa; não afirmar atomicidade entre Identity e Intelligence ou encerramento global. Disconnect só fecha transporte. Cancel/retry linearizam no DB; Redis não decide exclusividade. Falha/notificação ausente reconcilia DB; Langfuse é independente.

# Verification Contract

## Shared setup

Nenhum checker de implementação foi executado durante autoria. Arquivos `[N]` e novos cenários são planejados, não provas já produzidas. Usar [Tooling](../../../tooling.md), pnpm Web/uv Server, seleções locais dos produtores/consumidores deste recorte. Criar evaluation.md no kickoff, registrar resultados como EV, limitações e dependências. Full suites locais só por impacto demonstrado ou pedido explícito; CI de publicação preserva seus gates existentes.

Server usa classes pytest/casos parametrizados conforme Rules; mocks autospecced de portas/Clock/Identifier em use cases, sem testes diretos de entities/repositories/providers/pipes. NLP, rota local e Langfuse são comprovados por consumidores públicos e jobs registrados. Agno/JEV permanecem código dormente, não gates de release desta revisão. Testes Core continuam mockando protocolos. Web não cria dedicated query/action/realtime/service tests nem hooks/tests fictícios de renderer puro; consumidor contexto/widget/rota é a prova.

Fixtures atuais: `apps/server/tests/intelligence/server/controllers/conftest.py` (mentor_client, PostgreSQL descartável e auth/title controlados); `tests/fixtures/inngest_fixture.py` (PostgreSQL17/Inngest/Mailpit/Redis descartáveis e FastAPI subprocess); `tests/conftest.py` (Redis autouse). Auth override do mentor_client **não prova estado/revisão de conta real**. CI-09 usa Identity real descartável, altera estado/revisão na fixture e prova os pontos de guarda; não exige endpoint de encerramento ou ledger mensal. Essa alteração de fixture não é evidência de encerramento coordenado de conta. Novas fixtures ficam nesses consumidores: providers controlados visíveis ao subprocess, configurados antes de iniciar o filho, sem herdar credenciais de modelos reais. Monkeypatch no processo pytest não controla o servidor filho.

Matriz de dados: contasA/B ativas, duas sessõesA/umaB, ObjetivosA1/A2, mesma Skill em experiências concluída e não concluída, Competência liberada/bloqueada, Material multiorigem, Atividade learning/diagnóstico corrente, avaliação oficial learning e diagnóstico encerrado apenas consolidado. IDs únicos/factories por teste; asserts de estado inicial e cleanup da base Testcontainer. Nenhum seed/reset/truncation da base compartilhada, nem emissão de evento implantado.

Job real opt-in requer Docker/porta livre/registro do FUNCTION_ID. Fixture default7777 pode skip se ocupado; provar porta livre antes de usar7778 no comando CI-05 ou substituí-la por outra livre. Skip/seleção vazia/produtor ausente não é Pass. Runtime manual: docker compose ps, health web/API e registro Inngest via MCP local efetivamente configurado (candidato localhost18288/mcp); container presente não prova registro. Iniciar somente serviços necessários segundo documentação, deixar compartilhados ligados.

Playwright CLI em `apps/web`, web `http://localhost:7000` (origem configurada de Better Auth; não substituir por127.0.0.1 sem configurar trusted origin); carregar `.playwright-cli/states/shifu-auth-state.json` válido ou login visível/salvar privado. Resolver credenciais localmente sem imprimir. Dados autorizados existentes para VM ou ambiente isolado, sem criar/seed compartilhado por script. Evidência `.playwright-cli/{screenshots,snapshots,logs,states}/`; fechar somente sessões/processos próprios, não volumes.

## Automated

Comandos Server em `apps/server`, salvo indicação. Cenários/arquivos novos abaixo são planejados. CI-02/05/07/09 compartilham o mesmo arquivo de job: executar uma seleção parametrizada integrada e reutilizar os resultados por critério, sem repetir o arquivo quatro vezes sem mudança. A seleção deve executar de fato; resultado antigo/mocked não substitui a fronteira real contratada.

### CI-01 — Aceitação e controles idempotentes

**Criteria:** CA-01/08/10.

**Expected result / inputs:** criação/submit/cancel/retry/finalize/remove, chave igual/divergente, hint null/ausente/divergente, queued/processing/failed/cancelled/completed, falha de transação, conta ativa sem produtor de cota, conta ausente/inativa/indeterminada e revisão divergente. Uma operação, nenhum efeito proibido, recibos técnicos estáveis.

**Proof:** use cases Core existentes e `[N]`:

```bash
uv run pytest tests/intelligence/core/use_cases/test_create_mentor_session_use_case.py tests/intelligence/core/use_cases/test_submit_mentor_message_use_case.py tests/intelligence/core/use_cases/test_cancel_mentor_response_use_case.py tests/intelligence/core/use_cases/test_retry_mentor_response_use_case.py tests/intelligence/core/use_cases/test_finalize_mentor_response_use_case.py tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py
```

**Passing condition:** estados/bordas executados com efeitos ausentes em rejeição; concorrência/locks reais no CI-04/05.

### CI-02 — Classificação, corpus e busca reproduzíveis

**Criteria:** CA-02/11/13.

**Expected result / inputs:** positivos/paráfrases/negação, intenções distintas na mesma mensagem, desconhecida/hard negatives/homônimos, empate/margem, variações duplicadas, versão/dimensão incompatível. Calibração e held-out distintos. Casos parametrizados no job Inngest registrado: enviar mensagens sintéticas, aguardar execução e conferir intents/resultado privado permitido e blocos persistidos. Usar NLP/modelo local e índice reais versionados, não mocks que já devolvem a resposta esperada; serviços generativos externos permanecem controlados. Não chamar diretamente provider ou workflow no teste.

```bash
SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=7778 uv run pytest tests/messaging/inngest/jobs/intelligence/test_mentor_openrouter_composition_job.py
```

**Passing condition:** todos os rótulos/limiares independentes; dedup/RRF/gate corretos; sem match stale; precisão local selecionada≥95%, denominador/cobertura/abstenção registrados. Preparo/index DB real é CI-05. Não calibrar no mesmo conjunto que comprova a meta.

### CI-03 — Roteamento e restrições pedagógicas

**Criteria:** CA-02/03/04/05/06/13.

**Expected result / inputs:** process com FAQ/contexto local, esclarecimento e abstinência; múltiplos rótulos/desconhecida; explícito/history/hint conflitantes; experiências diferentes, dados ausentes, permissão/progresso muda antes do publish e respostas por partes. Provar que nenhum desses caminhos chama gerador, inclusive pergunta sem correspondência. Nenhuma alteração oficial de Learning/Gamification/Curriculum; diagnóstico individual não consultado.

```bash
uv run pytest tests/intelligence/core/use_cases/test_process_mentor_response_use_case.py tests/intelligence/core/use_cases/test_read_mentor_response_events_use_case.py
```

**Passing condition:** todas as rotas/bordas e efeitos ausentes provados; histórico não vira autoridade de dado mutável; zero forbidden release nos casos pedagógicos contratados.

### CI-04 — HTTP, isolamento e transação reais

**Criteria:** CA-01/03/08/09/10.

**Setup / inputs:** PostgreSQL descartável; contasA/B/sem auth, UUID/ULID inválido, extra/branco, hints estrangeiros/incoerentes, envios concorrentes, cancel versus finalize, replay/retry concorrente, rollback outbox. Assert HTTP/envelope/no-store e estado DB em nova sessão.

```bash
uv run pytest tests/intelligence/server/controllers/test_create_mentor_session_controller.py tests/intelligence/server/controllers/test_submit_mentor_message_controller.py tests/intelligence/server/controllers/test_cancel_mentor_response_controller.py tests/intelligence/server/controllers/test_retry_mentor_response_controller.py tests/intelligence/server/controllers/test_get_mentor_session_controller.py
```

**Passing condition:** constraints/locks efetivos e nenhum recurso estrangeiro revelado. Auth override não prova fechamento de conta; CI-09 cobre guarda real.

### CI-05 — Job registrado, replay e durabilidade

**Criteria:** CA-01/07/08/09/10/11.

**Setup / inputs:** Testcontainers/servidor filho com providers controlados, redelivery/crash antes-depois do commit, pausa/cancel/retry/delete, Redis offline, conexão interrompida, eventos duplicados/fora de ordem/Last-Event-ID inválido/recurso estrangeiro, legado de migration e preparo abortado/completo de índice. Provar FUNCTION_ID registrado, não só serviço vivo. Inspecionar DB em nova Session e durable payload/output sem conteúdo privado.

```bash
SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=7778 uv run pytest tests/messaging/inngest/jobs/intelligence/test_answer_mentor_message_job.py
uv run pytest tests/intelligence/server/controllers/test_stream_mentor_response_controller.py
```

**Passing condition:** porta previamente livre, sem skip/seleção vazia; registro/progresso/conclusão reais, loops limitados após redelivery, no callback tardio/recriação, replay sem geração nova. Controllers/job provam constraints e efeitos persistidos. Upgrade/downgrade/backfill/index/preflight são evidências de entrega executadas no ambiente descartável da fixture, registradas em Evaluation; não criar/estender teste específico de modelo/mapper/repository/migration. O arquivo legado de persistence adapters permanece inalterado e fora desta seleção. Cleanup fixture encerra apenas child/control endpoint próprios.

### CI-06 — Regressão dos proprietários de conteúdo

**Criteria:** CA-03/04/05/09/13.

**Inputs / outcome:** Learning released/unreleased/diagnosing/completed, Material multiorigem, learning versus diagnostic; seus consumidores mantêm regras. Composição Mentor em CI-05/09 prova projeções mínimas/eligibilidade antes de ranking/top-K; não criar teste de provider. Competência bloqueada não aparece e Skill descoberta não é adicionada automaticamente.

```bash
uv run pytest tests/learning/core/use_cases/test_get_competency_detail_use_case.py tests/learning/core/use_cases/test_get_material_detail_use_case.py tests/learning/core/use_cases/test_get_choice_activity_use_case.py
```

**Passing condition:** proprietários mantêm autoridade; nenhum snapshot rico com gabaritos usado como índice/contexto Mentor.

### CI-07 — Rota local, abstinência e barreira de inferência (revisão16)

**Type:** Automated. **Criteria:** CA-02/04/05/06/10/11/13.

**Inputs / proof:** consumer registrado de composição `test_mentor_openrouter_composition_job.py`, job/endpoint controlado e pergunta sem resposta local; consumidor `test_answer_mentor_message_job.py` prova rota com resposta conhecida e abstinência para pergunta não suportada; consumidor `test_mentor_langfuse_sdk_job.py` valida export OTLP pelo SDK real. Configurar uma chave OpenRouter sintética e endpoint que registra requisições. A execução deve completar a resposta local ou abstinência, persistir uma única resposta, manter `generation_keys` e recibos de inferência vazios, não criar custo e enviar zero pedidos ao endpoint. Spans OTLP precisam excluir `user.id`, `session.id`, input/output privado e nomes de etapas de geração/revisão.

```bash
SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=7778 uv run pytest tests/messaging/inngest/jobs/intelligence/test_answer_mentor_message_job.py -k unsupported_local_question
SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=7778 uv run pytest tests/messaging/inngest/jobs/intelligence/test_mentor_openrouter_composition_job.py
SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=7778 uv run pytest tests/messaging/inngest/jobs/intelligence/test_mentor_langfuse_sdk_job.py
```

**Passing condition:** os jobs registrados concluem com saída local correta/abstinência determinística, uma única resposta recuperável, nenhum request ao modelo mesmo com chave configurada, nenhum recibo de inferência ou custo e nenhum uso/cobrança comercial. Recibos técnicos são opcionais; qualquer recibo emitido deve ter zero tokens e ser idempotente. O SDK exporta spans operacionais allowlistados sem identidade ou conteúdo privado. Não validar schema, correção, thresholds ou qualidade JEV: geração/revisão não estão ativas nesta revisão.

### CI-08 — Consumidores Web e typing

**Criteria:** CA-03/07/08/12.

**Inputs / proof:** contexto/widgets com transporte controlado: foreground/history/replay, dup/out-of-order/old attempt, close/expand/remount, reduced motion, Markdown/HTML adversarial, multi-intent, matches Learning/nullhint, pending e retry imutável. Textos aprovados completos acessíveis.

```bash
# raiz
pnpm --filter web exec vitest run src/ui/intelligence/contexts/mentor-context/tests/use-mentor-context-provider.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/use-conversation.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/conversation.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/use-composer.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/message-list/message-item/tests/use-message-item.test.ts src/ui/intelligence/widgets/components/mentor-fab/tests/use-mentor-fab.test.ts src/ui/intelligence/widgets/components/mentor-fab/tests/mentor-fab.test.tsx src/ui/intelligence/widgets/pages/intelligence-page/tests/use-intelligence-page.test.ts src/ui/intelligence/widgets/pages/intelligence-page/tests/intelligence-page.test.tsx
pnpm --filter web exec playwright test tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts
```

**Passing condition:** consumidor cobre todos os eventos/estados, sem dedicated query/action/realtime/service suite. Browser automatizado atual tem mock transport; não substitui VM-01 real. Só ampliar arquivos Learning se impacto nos matches/consumidores justificar e registrar em Evaluation.

### CI-09 — Conta ativa, revisão de acesso e privacidade

**Criteria:** CA-05/06/08/09/10/11.

**Setup / inputs:** mesmos arquivos/cmd CI-04/05, cenários nos consumidores com contas/revisões Identity reais em PostgreSQL descartável. Conta ativa autoriza consulta local sem produtor de cota; conta ausente/inativa, falha de leitura Identity e revisão divergente devem rejeitar nos pontos de guarda aplicáveis antes de leitura/publicação. Exercitar exclusão/cancel/retry e callbacks tardios sob fence de sessão/tentativa, recibos técnicos opcionais (zero tokens e idempotentes quando emitidos), privacidade e Langfuse off/erro. Não existe endpoint de geração/revisão nesta revisão. Não requerer API de encerramento, lock global entre módulos, cota100%, renovação, débito comercial ou configurações ZDR de endpoint de inferência. Não repetir execução válida se casos já rodaram conjuntamente.

**Passing condition:** autorização real sem depender de cota; rejeição de conta/revisão inválidas nos pontos de guarda; nenhum acesso/leitura/publicação após detecção de perda de acesso; fence efetivo para sessão/tentativa/exclusão. Recibo técnico é opcional; se emitido, é idempotente e tem zero tokens. Nenhum conteúdo privado em traces/outputs públicos/duráveis e Langfuse sem identidade. Auth override não substitui Identity real. Não alegar revogação atômica entre módulos nem marcar RP-02/encerramento como entregues. Ausência de cota/encerramento deferidos não bloqueia este checker; ausência de estado Identity confiável continua bloqueante.

### CI-10 — Tipos

**Scope:** projetos Server/Web configurados e contratos consumidores alterados.

```bash
# apps/server
uv run poe check:types
# raiz
pnpm --filter web check:types
```

**Passing condition:** sem erro pendente nos projetos; falha preexistente identificada/localizada, sem declarar pass global.

### CI-11 — Lint, formato e complexidade

**Scope:** arquivos realmente alterados da árvore, não diretórios inteiros. Na integração, extrair do diff a lista explícita Python/Web elegível (incluindo untracked), preservar trabalho externo e registrar comandos expandidos em Evaluation. Comandos reais: `uv run ruff check --no-fix` e `uv run ruff format --check` com esses arquivos em apps/server; `pnpm exec biome check` com arquivos TS/TSX/JSON alterados na raiz. Não instalar script fictício/check:complexity.

**Passing condition:** lint/format sem violações bloqueantes, warnings revisados. Complexidade Server Ruff C90/C901, McCabe máximo10 (default atual, sem override); Web regras qualitativas complexity do Biome, sem limite cognitivo quantitativo configurado. Disposições separadas com saída atual; sem inferir score de types. Gate quantitativo adicional não foi aprovado nem existe.

### CI-12 — Arquitetura, build e compatibilidade

```bash
# apps/server
uv run poe check:architecture
uv run poe build
# raiz
pnpm --filter web check:architecture
pnpm --filter web build
git diff --check
docker compose config --quiet
```

**Passing condition:** Tach/Web dependencies e builds válidos, Compose/env sem credencial comprometida, drift/migration provados CI-05. Geração de route tree pelo mecanismo configurado; CI de publicação conserva gates existentes, sem full suites locais redundantes.

Inspecionar wheel/sdist gerados com zipfile/tarfile da biblioteca padrão e assertar recursos `shifu/intelligence/ai/data/mentor-intents.json`, `mentor-answers.json` e `mentor-index-manifest.json`. Leitura via importlib.resources na distribuição construída deve funcionar fora do checkout. Registrar comando/resultado como evidência de distribuição, sem módulo de teste de provider/empacotamento. Fixtures e CI descartáveis precisam disponibilizar vector no PG17, preservando gates sem novos resets.

### CI-14 — Mutação dos use cases críticos

**Required:** Server, pelo risco de inverter ownership, attempt/status/fence, bloqueio pedagógico/idempotência. Apenas use cases criados/alterados desta Spec, teste somente use-case. Web Not applicable, sem runner; usar CI-08/10/11.

```bash
# apps/server; --core isola conftest e dispensa containers
uv run poe test:mutation --core --files src/shifu/intelligence/core/use_cases/create_mentor_session_use_case.py src/shifu/intelligence/core/use_cases/submit_mentor_message_use_case.py src/shifu/intelligence/core/use_cases/cancel_mentor_response_use_case.py src/shifu/intelligence/core/use_cases/retry_mentor_response_use_case.py src/shifu/intelligence/core/use_cases/process_mentor_response_use_case.py src/shifu/intelligence/core/use_cases/read_mentor_response_events_use_case.py src/shifu/intelligence/core/use_cases/finalize_mentor_response_use_case.py src/shifu/intelligence/core/use_cases/remove_mentor_session_use_case.py --tests tests/intelligence/core/use_cases/test_create_mentor_session_use_case.py tests/intelligence/core/use_cases/test_submit_mentor_message_use_case.py tests/intelligence/core/use_cases/test_cancel_mentor_response_use_case.py tests/intelligence/core/use_cases/test_retry_mentor_response_use_case.py tests/intelligence/core/use_cases/test_process_mentor_response_use_case.py tests/intelligence/core/use_cases/test_read_mentor_response_events_use_case.py tests/intelligence/core/use_cases/test_finalize_mentor_response_use_case.py tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py
```

**Passing condition:** analisar outcomes por targets, killed/(killed+survived)≥70%; exit0 não impõe score. Mutante que remove isolamento/fence/restrição é bloqueante mesmo passando agregado. Surviving equivalente requer justificativa verificável; demais exigem correção/assert. Registrar targets/comando/tempo/outcomes. Piso de regressão módulo completo (baseline Intelligence13/13, piso95%) comprovado no summary CI12shards, não pelo recorte local; não autoriza --all. Runner requerido indisponível = Blocked; coverage não substitui.

### CI-15 — Handler BFF SSE autenticado e streaming

**Criteria:** CA-07/09/12.

**Setup / inputs:** `apps/web/tests/playwright.ts` e fixtures Identity/BFF existentes, handler HTTP registrado, sessão cookie real/ausente/expirada/estrangeira e upstream controlado que permanece aberto. Não é teste do provider nem page test com route mock. API suite module-owned `[N]` usa request/context da fixture canônica e isolamento de sua conta.

```bash
# raiz
pnpm --filter web exec playwright test tests/intelligence/mentor-response-stream-api.test.ts
```

**Passing condition:** anônimo/revogado rejeitado sem upstream privado; owner propagado server-only, no-store e tipo SSE corretos; bloco chega antes do fechamento upstream, sem buffering; after_sequence/Last-Event-ID e malformed/negative tratados; abort fecha upstream mas não cancela job; nenhum JWT/segredo no payload/header browser/URL. Cookie não é exposto. Evidência de handler não substitui o backend real CI-05 nem a jornada real VM-01.

### CI-16 — Calibração do reviewer remoto

**Type:** Not applicable for revision16. **Criteria:** none active. **Reason:** a produção não instancia writer/reviewer nem envia pedidos de resposta ao OpenRouter; não há decisão de reviewer ou resposta gerada para calibrar. Os limiares JEV 0.75 e todos os resultados Failed anteriores permanecem registrados como histórico em Evaluation, sem os apagar ou declarar aprovados. Não executar chamadas de modelo para esta revisão.

**Replacement evidence:** CI-07 prova por job registrado que, mesmo com chave OpenRouter configurada, respostas locais/abstenções completam sem request de inferência. Uma futura ativação de geração exige emenda explícita e novo checker de qualidade antes de qualquer rota de produção.

### CI-17 — Progresso do caminho local (revisão16)

**Type:** Automated. **Criteria:** CA-07/11/12. Seleção afetada: use case de processamento, stream controller e consumidores Web. Verificar que contexto/referências não geram etapa visível, nenhum evento de geração/revisão aparece no caminho local, estado terminal limpa progresso, frames legados sem campo continuam compatíveis e nomes fora da allowlist são recusados. Usar comandos/fixtures existentes e DB/Inngest descartáveis. Não exigir execução de Agno/JEV dormente, typing gerativo ou ferramentas inexistentes. Prova visual do estado local complementa testes quando a UI for alterada.

## Manual

### VM-01 — Resposta local e recuperação autenticada

**Type:** Manual. **Criteria:** CA-01/03/06/07/12.

**Setup / tool:** Playwright CLI com sessão autenticada e API/Inngest reais; nenhum transporte mockado. Usar uma pergunta FAQ local conhecida e uma pergunta não coberta pela base.

**Procedure:** enviar a pergunta FAQ e conferir resposta curada; enviar a pergunta não coberta e conferir a abstinência em português. Navegar/recarregar a conversa, confirmar que ambas as respostas continuam presentes em ordem, sem nova chamada de modelo e sem duplicação. Registrar URL, resultado visível, requisições relevantes, console e caminho de recuperação após reload. Não requer teste de geração nem screenshot de estados visuais inalterados.

**Passing condition:** ambas as saídas são persistidas e recuperáveis após reload; a pergunta não coberta recebe a abstinência contratada; há zero request de inferência, zero recibos/custos de modelo e nenhum erro relevante de console. A inspeção visual serve apenas para confirmar texto/estado; persistência é confirmada por readback autenticado do backend.

### VM-02 — Export Langfuse sem identidade nem conteúdo

**Type:** Manual. **Criteria:** CA-11.

**Setup / tool:** job sintético VM-01 e consumidor SDK real; Langfuse local opcional em `localhost:7003` quando configurado. Se o dashboard não estiver conectado a um projeto, usar o export OTLP capturado pelo consumidor SDK CI-07, sem emitir eventos extras nem alterar o serviço compartilhado.

**Procedure:** inspecionar spans operacionais do mesmo envio e verificar a allowlist de metadata, correlação opaca, nomes/resultado/duração/contagens; confirmar ausência de `user.id`, `session.id`, conteúdo da pergunta/resposta, conteúdo de prompt e observations/generations de modelo. Desativar telemetria em ambiente isolado e confirmar que a resposta local permanece igual.

**Passing condition:** SDK real exporta spans operacionais sem identidade ou conteúdo privado e a falha/desativação de telemetria não impede a resposta. Este checker não verifica retenção/exclusão da instância Langfuse e não a declara compatível com prazo ligado a encerramento de conta.

## Visual

### VM-03 — Página, FAB e mobile com blocos aprovados

**Type:** Visual. **Criteria:** CA-07/12.

**Reference / setup:** [handoff](design/handoff.md), XOwCJ/O6cds/PdJCw/yXJ3I e shell EmQFg; reutilizar captures VM-01 nos viewports definidos.

**Comparison:** inspecionar conversa/FAB tipografia/hierarquia, código, status/composer/gutters; mobile390×844 sem sidebar desktop, wrap/hit44px/foco/sem overflow global. Typing começo/final e reduced motion adaptam mesma composição. yfOZm/x2HsU/upndz informam aparência de erro por CI-08, sem journey manual negativo adicional.

**Passing condition:** tokens/primitives existentes e adaptações aprovadas; sem funcionalidades deferidas habilitadas/tool details/cota falsa. Captures só em diretórios CLI ignorados; revisão de código e visual paralelas no mesmo candidato integrado, conforme AGENTS.

# Documentation Alignment

| Documento / autoridade | Governa / confirmação | Disposição / dependência |
| --- | --- | --- |
| [Shifu — PRD — Intelligence](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83099649/Shifu+PRD+Intelligence), content83099649/version7, parent82804737/space82509828; releitura integral confirmada2026-10-12 | PRD define Mentor contextual com orientação gerada e requisitos de privacidade de provedor | Revisão16 implementa apenas a fatia local sem inferência: FAQ/contexto autorizado, esclarecimento e abstinência. É parcial perante RP/JN canônicos; não substitui nem altera o PRD e não declara o módulo Intelligence completo. Sem escrita externa |
| [SHIFU-100](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-100), id12610, “Implementar respostas contextuais e recuperação”, parentSHIFU-29, updated2026-10-09T20:57:14.655-03:00/Fazendo | Texto/contexto/recuperação; dependeSHIFU-99; lido completo | Decisões desta conversa refinam implementação; nenhuma edição Jira solicitada |
| PRDs Learning83066881v26, Curriculum83034113v13, Gamification82903042v3, Identity83001345v2, Privacy100106241v4 | Fatos/elegibilidade/conclusão/ciclo de dados | Leituras anteriores permanecem referência histórica. Emenda16 remove IDs pessoais da telemetria Mentor e limita o export a spans anônimos/allowlisted. Sem escrita externa; cota/encerramento coordenado deferidos |
| [Architecture](../../../architecture.md), [Modules](../../../modules.md), [SDD](../../../sdd.md) | Camadas/dependências/status/evidência | Na implementação da revisão6, reconciliar a descrição atual de entitlement/revogação coordenada como dependências de publicação com o recorte aprovado, sem declarar o runtime corrigido antes da prova; nenhum Shared business policy |
| [Rules](../../../rules.md)/Rule Pack selecionado e [Tooling](../../../tooling.md) | Estrutura/checks/test integrity | Rules determinam NLP em providers e embeddings por repository. Para a revisão16, NLP/rota local/Langfuse são provados pelos consumidores registrados; Agno/JEV ficam dormentes e fora dos critérios de aceitação. Sem exceções locais de layout/testes nem migração implícita de legado; limites de domínio/privacidade preservados. O gate local de changed-code coverage foi removido do projeto por decisão do usuário; isso não altera os checkers comportamentais desta Spec. |
| [Sessões](../mentor-sessions-management/spec.md) e [handoff anterior](../mentor-sessions-management/design/handoff.md) | Base entregue/referências | Substituir somente placeholders de resposta/envio subsequente; preservar gerenciamento. Evaluation anterior é histórico, não prova desta entrega |
| [Handoff](design/handoff.md), [shifu.pen](../../../../design/shifu.pen) | Frames/tokens/adaptações | IDs inspecionados via Pencil; imagens anteriores duráveis reutilizadas; dirty design preservado |
| Manifests/locks/settings/Compose/.env.example/CI atuais | Bibliotecas/gates/config | Resolver docs/versões efetivas; sem segredo. Langfuse configurado não significa tracing implementado |
| Chat “Entenda o planejador de objetivos”, thread01a1036d-ddbf-7c63-bb85-616345c1a871, lido via read_thread | Contexto anterior de PLN | Aprovações posteriores desta conversa selecionam embeddings/BM25 e deferem memórias/anexos/summary; não importar decisão antiga incompatível |

Conflito de autoridade/versão exige reconciliação explícita. Nesta entrega, acesso real à conta, fence de sessão/tentativa/exclusão e privacidade efetiva permanecem obrigatórios; cota e encerramento coordenado não integram sua publicação. O PRD mantém RP-02 e o ciclo completo de encerramento como requisitos do produto: o recorte não altera o PRD nem declara o módulo completo. Autoria não autoriza implementar, commitar ou escrever Jira/Confluence. Aprovação de ready da revisão5 não aprova automaticamente esta revisão material. Revisão independente da emenda6 concluída sem achados bloqueantes em2026-10-11; Usuário aprovou explicitamente o contrato escrito da revisão6 em2026-10-11. Emenda7 solicitada para calibrar JEV: draft; revisão independente da emenda concluída sem achados bloqueantes após corrigir a localização dos cenários para o consumidor espelhado existente; aprovação escrita concedida pelo usuário (ok) em2026-10-11; revisão7 ready. Esta aprovação não afirma que a implementação atual ou seus checks já atendem à emenda. Revisão8: usuário definiu explicitamente89% e solicitou implementação/VM-01; revisão independente do contrato concluída sem achados bloqueantes. CI-16 histórico continua Failed, sem dispensa nem alegação de calibração.


Emenda9: usuário solicitou explicitamente reduzir os seis limiares para75%. Esta autorização substitui89% como configuração; não dispensa CI-16 ou VM-01 nem transforma evidência anterior em aprovação. Testes de fronteira usam o manifesto atual e devem comprovar74.9/75/75.1%, approved/rejected/inconclusive separadamente.

Emenda10 — correção solicitada pelo usuário: manter os seis limiares0.75 e todas as restrições; explicitar na rubrica o estado autorizado diagnostic_in_progress, a abstenção quando o diagnóstico está ativo mas o vínculo temático é desconhecido, e a distinção entre explicação conceitual/dica e solução integral. O reviewer avalia cada parte sem exigir partes de outros blocos. Preservar consumo numérico autêntico antes de erros nativos de parsing, sem guardar payload privado ou inventar uso. CI-16 requer nova execução congelada com hashes atuais; não reutilizar observações da rubrica anterior nem retunar no held-out. O corpus e os rótulos existentes permanecem intactos.

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-10 | Respostas contextuais assíncronas, roteamento local, contexto autorizado, geração/revisão cumulativa, recuperação página/FAB | SHIFU-100, Intelligencev7, decisões técnicas e design consolidado aprovados antes da redação; aprovação escrita inicialmente pendente; concedida em 2026-10-10 após revisão5 e alinhamento das Rules |
| 2 | 2026-10-10 | NLP em providers; novo Agno em ai/agno; diretório mentor_review_provider; persistência por MentorEmbeddingsRepository; provas NLP/Agno no job Inngest, com cobertura do subprocess | Correções explícitas do usuário sobre a árvore e fronteiras de teste; comportamento e limiares preservados |
| 3 | 2026-10-10 | Server functions afetadas colocadas nos hooks de operação; agregador legado fora do recorte | Usuário considerou mentor-server-functions.ts desnecessário na árvore proposta; autenticação e transporte preservados |
| 4 | 2026-10-10 | Streaming integrado ao IntelligenceService existente, com dependência de transporte própria e compatibilidade dos consumidores atuais | Usuário removeu o serviço REST separado; SSE, autenticação, cancelamento de transporte e replay preservados |
| 5 | 2026-10-10 | Declarações e contrato de lifecycle do hook SSE, evento Web e integração ao provider/contexto | Usuário apontou documentação insuficiente dos hooks de streaming; detalha garantias já contratadas e cobertura pelos consumidores |
| 6 | 2026-10-11 | Cota mensal e revogação coordenada explicitamente deferidas sem dependência de publicação; autorização por conta ativa/revisão, uso técnico separado de cobrança; RF-14/15, CA-09/10 e CI-01/09 reconciliados, mantendo VM-01/02 e privacy/fence de sessão/tentativa | Usuário reafirmou que cota está fora de escopo e solicitou atualizar a Spec; decisão anterior também excluiu revogação coordenada em Identity. Nenhuma aceitação bloqueada convertida em Pass; implementação atual precisa adequação. |
| 7 | 2026-10-11 | Distinguir confidence de precisão; calibração JEV sintética separada de FAQ e held-out CI-16 antes de alterar limiares; compatibilidade de índice e VM-01 revalidadas | Usuário solicitou ajuste com evidência. Nenhum valor menor adotado sem prova; Intelligence83099649v7 relido integralmente sem mudança canônica ou escrita externa. |

| 8 | 2026-10-11 | Seis critérios JEV com limiar fixo0.89, approved obrigatório, limites e isolamento preservados; adoção explícita independente da seleção CI-16, sem declarar calibração Passed; revalidar índice/consumidores e VM-01 real | Usuário respondeu “Definir89% como novo limiar de aprovação” e solicitou a jornada manual. Risco observado: diagnostic_safety aprovou um caso inconclusivo em0.89; CI-16 continua Failed/limitação de qualidade, held-out preservado. |

| 9 | 2026-10-11 | Seis critérios JEV com limiar fixo0.75, approved obrigatório; limites, guards, privacidade e demais obrigações preservados; revalidar índice/consumidores e VM-01 | Usuário solicitou “vamos diminuir para75%”. Decisão de configuração independente da calibração Failed; caso incorreto diagnostic_safety0.89 continua conhecido e não comprova qualidade do novo limiar. |

| 10 | 2026-10-11 | Correções da rubrica e da captura de consumo autêntico, mantendo75% e as restrições; repetir consumidores, CI-16 e VM-01 | Usuário solicitou “fix it”. A hipótese de ambiguidade da rubrica precisa ser validada; a causa das falhas técnicas históricas não foi estabelecida pelos logs. Nenhuma aprovação real ou qualidade calibrada presumida. |

| 11 | 2026-10-11 | Progresso nullable persistido e recuperável emitido somente por etapas reais do workflow; rótulos de contexto removidos do indicador; geração/revisão atuais, compatibilidade e guards preservados | Usuário solicitou mostrar somente steps do workflow e tools; não há tools do agente neste recorte. Fonte Intelligence83099649v7 relida sem alteração externa. |

| 12 | 2026-10-11 | FAQ local aceita resolve sua parte sem anexar resultados de currículo incidentais; pesquisa de currículo em parte independente preservada | Captura manual mostrou lista de materiais para pergunta sobre progresso entre Objetivos. Reproduzido no roteador local; correção limitada à apresentação, sem alterar os limiares. |

**Emenda13 — inspeção de respostas/JEV.** Usuário solicitou verificar cada resposta e retorno JEV e, se impossível recuperar, implementar essa capacidade no Langfuse. Tentativa histórica01M4PEZGY6C050JS1NM2RFG90G gerou duas versões e registrou duas abstenções sem dados de critérios; esses textos/decisões não são recuperáveis. Contrato opt-in acima permite apenas candidatos validados e decisões fechadas futuras em projeto privado; não altera limiar0.75, políticas de aprovação, máximo de duas versões, retries, permissões, publicação, API ou persistência. Prova: consumidor nativo geração/aprovação/correção/segunda recusa/erro de revisão, captura ausente/metadata-only/throwing, SDK real e inspeção no Langfuse. Nenhuma emenda externa ou dispensa de CI-16.

| 13 | 2026-10-11 | Inspeção opt-in de versões geradas e seis respostas JEV fechadas em Langfuse privado; padrão sem conteúdo e gates invariantes | Autorização explícita do usuário para adicionar a capacidade ao Langfuse quando os registros existentes não permitirem a investigação; sem bug report. |

**Emenda14 — revisor Agno sem percentual.** Usuário preferiu outro agente Agno e confirmou “Aprovação pelos seis critérios, sem percentual de confiança”. Produção Mentor usa MentorWriterAgent e MentorReviewerAgent separados, ambos via perfil GPTLuna existente e modelos/clientes independentes, dentro do Loop nativo de até duas versões. Novo reviewer retorna schema fechado com seis campos obrigatórios request_adherence/fact_fidelity/cumulative_solution/diagnostic_safety/privacy_access/official_action_claims, cada qual choice approved/rejected/inconclusive e feedback breve≤400caracteres. Aprovação é calculada exclusivamente por todos os seis choices approved; nenhum percentual/probabilidade/overallapproved arbitrário integra o schema. Falha de transporte/schema/consumo desconhecido continua indisponível, sem reviewerfallback/retries adicionais; correção bounded preserva gates cumulativos, diagnósticos, privacidade e ações oficiais. Perfil reviewer é resolvido pelo servidor para openai/gpt-6-luna e requisições mantêm ZDR/data_collectiondeny. Langfuse opt-in registra candidatos e choices/feedback, sem confiança inventada; uso profile mentor-reviewer e IDs/versões vinculados. JEV e seus limiares/corpus permanecem somente para consumidores legados/histórico e outros contratos independentes (incluindo avaliação Learning), fora da composição Mentor ativa. Não afirmar calibração/qualidade do novo reviewer com evidência histórica JEV. CI-16 precisa prova específica do novo reviewer se for concluir a feature; mudança de componente não converte resultados antigos em Passed.

**Prova da emenda14:** job registrado de composição de produção com transports controlados para writer/reviewer separados; aprovação direta, correção→aprovação, segunda rejeição, inconclusivo, schema inválido, uso desconhecido, fallback somente writer; schema6campos, gates e recibos privados. Agentes nativos reais, sem mock do reviewer. Tipagem/arquitetura/build, cobertura dos novos fontes e revisão independente. Repetir uma vez o pedido real de JS na mesma sessão autenticada e inspecionar respostas/reviews e recuperação no Langfuse; captura opcional continua independente de entrega. Demais obrigações não modificadas retêm evidência válida.

| 14 | 2026-10-11 | MentorReviewerAgent Agno separado, GPTLuna, seis choices aprovados sem percentual, feedback/correção até2versões; inspeção opt-in mantida | Preferência explícita por outro agente Agno e confirmação explícita da política sem percentual de confiança. |
| 15 | 2026-10-11 | Traces privados carregam somente `account_id`/`session_id` como `user_id`/`session_id` de Langfuse; correlação por tentativa mantida separada; sem dados de perfil; retenção operacional verificada em VM-02; SDK real cobre export e isolamento | Usuário solicitou integrar Sessions/Users e aprovou explicitamente IDs existentes apenas; aprovação do contrato escrito em 2026-10-11 após revisão independente sem achados bloqueantes. |
| 16 | 2026-10-11 | Restringir esta entrega a respostas/contexto locais e abstinência determinística; nenhum writer/reviewer/OpenRouter em produção; traces Langfuse sem identidade nem conteúdo; CI-16 e geração VM-01 não aplicáveis | Solicitação explícita do usuário para emendar o contrato e endereçar os comportamentos pendentes. PRD canônico não pôde ser relido naquela sessão; esta limitação foi resolvida em 2026-10-12, sem alterar o contrato canônico. |
| 17 | 2026-10-12 | Reconciliar a revisão16 com a releitura integral do PRD Intelligence v7 e marcar a entrega local-only como parcial perante o produto canônico | O PRD exige orientação contextual gerada; esta revisão não a implementa nem a substitui. Nenhuma escrita externa foi feita. |
| 18 | 2026-10-12 | Remover o critério local de cobertura alterada e seus mapeamentos de acceptance criteria, sem renumerar os demais checks | Solicitação explícita do usuário. Política de cobertura do Tooling permanece independente e não foi alterada. |
