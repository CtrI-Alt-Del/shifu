---
title: Preparação prática culinária em Atividades de aprendizagem
status: ready
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-130
scope:
  - Curriculum
  - Learning
  - Shared content contract
  - Intelligence (adaptador de avaliação por visão)
  - Web Learning
last_updated_at: 2026-11-21
---

# Objective

Adicionar a questão de preparação prática às Atividades de aprendizagem. O aprendiz prepara um prato, registra de 1 a 5 fotos pedidas pelo Currículo, escreve uma reflexão opcional e envia. A IA avalia só o que as fotos mostram, pela rubrica do Currículo. Learning valida o resultado e calcula a nota. Quando as fotos não bastam, a tentativa se encerra sem nota. Este é um contrato completo: envolve armazenamento privado de fotos, rascunho entre dispositivos, concorrência, avaliação durável por IA, remoção de dados e interface. Base de conhecimento e decisões: [plano de implementação](../../../../SHIFU-130-plano-de-implementacao.md), que não substitui esta Spec.

Decisões já registradas (Q1–Q6, usuário): upload multipart pela API; bucket privado novo de Learning; nova porta de avaliação em Shared com adaptador em Intelligence; limpeza por evento durável e job Inngest; fotos passam à tentativa no envio sem cópia; exemplo de legumes salteados só em dados de demonstração e teste.

Decisões novas (Q7–Q11), registradas com a opção recomendada conforme orientação do usuário e **abertas à sua revisão desta Spec**:

- Q7 = A. O cliente envia a revisão do rascunho que viu. Se outra revisão foi salva, o envio responde conflito e a página recarrega o rascunho.
- Q8 = A. A avaliação roda como workflow AgentOS de Learning, como a tradução, e escolhe o destino pelo `LearningWorkflowsRegistry`.
- Q9 = A. A condição de insuficiência vem do Currículo como lista de critérios cuja observação inconclusiva em um registro nomeado declara o registro insuficiente. Learning aplica a regra sobre o resultado validado, sem nova interpretação da IA.
- Q10 = A. As rotas de foto ficam sob o caminho da Atividade e usam PUT, DELETE e GET. O middleware de 512 KiB só cobre POST e portanto não atinge o PUT da foto. Um middleware novo limita o corpo multipart do PUT de foto em 10 MB mais sobrecarga, com 413 e 400 no contrato de erro do Mentor, e é registrado ao lado do limite de anexos do Mentor.
- Q11 = A. A verificação dos Conceitos afetados reaproveita a observação inconclusiva já derivada pela política adaptativa (valor nulo), sem estado persistido novo.

# Scope

| Área / ator | Incluído | Excluído ou adiado |
| --- | --- | --- |
| Autor de Curriculum | Questão `practical_preparation`: técnica ou prato, enunciado, orientações, referências com texto acessível, dificuldade, 1–5 registros fotográficos, critérios com pesos que somam 100%, níveis 0/25/50/75/100 com comentário predefinido, condições inconclusivas e de insuficiência, mapeamento de Conceitos. Uma única questão por Atividade, só de aprendizagem. | Autoria por interface. Habilidade real de Culinária publicada. |
| Aprendiz em Learning | Rascunho privado por experiência e Atividade (fotos e reflexão), retomável em outro dispositivo; upload, troca e remoção de foto antes do envio; envio com tentativa imutável; resultado com critérios, pesos, níveis e comentários; encerramento sem nota com nova tentativa; Tentar novamente em falha técnica. | Mentor, avaliação provisória, diagnóstico, edição de tentativa enviada. |
| Servidor / IA | Porta de avaliação em Shared, agente de visão em Intelligence com saída estruturada fechada, workflow AgentOS de Learning, jobs Inngest de limpeza de foto e de purga por conta encerrada. | Qualquer texto gerado pela IA, decisão de nota, progresso ou recomendação por IA. |
| Remoção e conta | Remoção de experiência, Habilidade, Objetivo e conta eliminam rascunho, fotos e objetos em até 24 horas. Efeitos tardios não recriam dados. | Restauração de dados removidos. |
| Interface desktop / mobile | Todos os estados do Design Contract. | Novas rotas. Redesenho dos demais formatos. |

Classificação: Learning RP-32 integral para o fluxo; RP-09/12/13/14/18/24/25/27/29, RP-21/22 e Curriculum RP-03 integrais no que tocam à preparação prática. Os requisitos gerais continuam sem entrega total de outras modalidades.

# Behavior Contract

| ID | RP/JN/fonte | Comportamento observável |
| --- | --- | --- |
| RF-01 | Curriculum RP-03; Learning RP-32; JN-26 | Curriculum valida a questão: exatamente uma por Atividade de aprendizagem, nunca no diagnóstico, 1–5 registros com chaves distintas, pesos dos critérios somando 100, quatro níveis intermediários mais 0 e 100 com comentário predefinido, cada comentário de insuficiência apontando um registro existente, Conceitos autorizados. |
| RF-02 | Learning RP-32/09; JN-26 | A leitura privada da Atividade entrega enunciado, orientações, referências, registros e critérios com pesos, sem condições internas de insuficiência. A Atividade de preparação prática é elegível com uma questão. |
| RF-03 | Learning RP-32/29; JN-26 | O rascunho é privado da conta, por experiência e Atividade, e retomável em outro dispositivo. A última alteração salva prevalece, sem mistura de versões. Cada gravação devolve o estado salvo e a revisão. O rascunho não expira. |
| RF-04 | Learning RP-32; JN-26 | Por registro: foto JPEG, PNG ou WebP de até 10 MB, decodificável, adicionável, substituível e removível antes do envio. Só foto validada e com upload concluído satisfaz o registro. Upload repetido com a mesma chave de upload não duplica a foto. |
| RF-05 | Learning RP-32/29; JN-26 | Foto removida ou substituída fica inacessível na hora e seu objeto sai do armazenamento em até 24 horas, por evento durável e job com novas tentativas, salvo se uma tentativa enviada a usa. Só o dono lê a foto. |
| RF-06 | Learning RP-32; JN-26 | Enviar sem todos os registros satisfeitos, com foto ainda em envio, com revisão do rascunho desatualizada ou com rascunho encerrado é recusado sem tentativa, nota ou avaliação. A reflexão, por ser opcional, nunca bloqueia o envio quando está vazia. Na web, o envio aguarda uma gravação de reflexão pendente ou com falha, para não congelar uma versão antiga do relato; o aprendiz pode tentar salvar de novo ou limpar o campo. |
| RF-07 | Learning RP-32/13/14; JN-26 | O envio cria, em uma transação, uma tentativa imutável com as fotos do rascunho e a reflexão confirmadas, avaliação pendente e evento durável, e encerra o rascunho. A chave de envio é idempotente. Foto ou edição tardia não altera a tentativa. |
| RF-08 | Learning RP-32/24/12; JN-26 | A IA vê só enunciado, critérios e fotos, sem identificadores. Devolve por critério um nível permitido ou inconclusivo e um comentário predefinido, e por registro se a evidência basta. Instruções dentro da foto são ignoradas. Fotos nunca entram em estado de execução, log ou telemetria. |
| RF-09 | Learning RP-32/12/18/27; JN-26 | Learning valida critérios completos, níveis permitidos, comentários existentes na rubrica e Conceitos autorizados, e só então calcula a nota ponderada e a evidência por Conceito, separadas. Nota alta não implica evidência máxima. A reflexão não entra na nota nem na evidência. |
| RF-10 | Learning RP-32/27; JN-26 | Se o resultado validado satisfaz uma condição de insuficiência do Currículo, a tentativa se encerra sem nota: sem zero, sem nota parcial, sem pesos redistribuídos, sem evidência nova, sem XP e sem progresso. Preserva fotos, reflexão e comentários, mantém contribuições anteriores válidas, abre a verificação dos Conceitos afetados e libera novos envios. |
| RF-11 | Learning RP-32/13/14; JN-26 | Falha técnica, indisponibilidade, resposta inválida ou incerteza que não prove insuficiência mantêm a avaliação recuperável. Tentar novamente reavalia a mesma tentativa, sem reenviar fotos nem criar tentativa. Nunca se encerra sem nota só para liberar envios. |
| RF-12 | Learning RP-32/18/25; JN-26 | Resultado e histórico mostram cada critério com peso, nível e comentário predefinido; mostram os registros e a reflexão em somente leitura; para tentativa sem nota mostram "sem nota", os registros não avaliáveis e a orientação, com as ações de nova tentativa e voltar à Habilidade. Nunca se apresenta como zero nem como em andamento. |
| RF-13 | Learning RP-21/22/29; JN-26 | Remover experiência, Habilidade, Objetivo ou conta elimina rascunho, fotos e objetos em até 24 horas, com nova tentativa e alerta em falha. Avaliação tardia, upload tardio ou limpeza tardia não recriam dados. Outros usuários não acessam fotos. |
| RF-14 | Learning RP-25/32; JN-26 | Interface em pt-BR; ações essenciais por teclado; estados de carregamento, salvamento, avaliação, falha e recuperação com texto e ícone, nunca só cor; regras de formato e tamanho visíveis antes da escolha; miniaturas com texto alternativo; reflexão identificada como relato do aprendiz; estado do rascunho sem prometer outro dispositivo quando há alteração não salva ou falha. |
| RF-15 | Learning RP-29; Atlassian Política v4 | As fotos são gravadas sem metadados (EXIF e GPS removidos antes do armazenamento e do envio ao modelo). Dados de rascunho e fotos seguem a política: eliminação em até 24 horas no encerramento da conta; a web só restaura rascunho depois de validação online da sessão; falha de conexão não prova encerramento de conta. A IA usa ZDR e trava de registro de prompts. |

| ID | RF | Dado | Quando | Então | Prova |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Conteúdo com 0/1/5/6 registros, pesos 100/99/101, chaves repetidas, nível ou comentário ausente, comentário de insuficiência para registro inexistente, duas questões, diagnóstico | Curriculum valida e publica | Só o conteúdo íntegro de aprendizagem com uma questão fica elegível | CI-01, CI-08 |
| CA-02 | RF-02 | Atividade de preparação prática liberada | Dono lê a Atividade; terceiro tenta | Dono recebe orientações e critérios públicos sem regras de insuficiência; terceiro é negado | CI-01, VM-01 |
| CA-03 | RF-03 | Dois dispositivos da mesma conta | Cada um salva reflexão ou foto, em ordem e em corrida | A última gravação salva prevalece, a revisão cresce, nada se mistura, a leitura devolve o estado salvo | CI-02, VM-02 |
| CA-04 | RF-04 | Arquivo inválido, não imagem, vazio, 10 MB e 10 MB + 1 byte, extensão incoerente, imagem não decodificável | Sobe a foto de um registro | Aceita só JPEG/PNG/WebP válido até 10 MB; recusa o resto sem gravar; repetir a chave de upload não duplica | CI-03, CI-07 |
| CA-05 | RF-05 | Foto trocada, removida e descartada; foto usada por tentativa enviada | Remove e roda o job de limpeza | Foto fica inacessível já; objeto é apagado com novas tentativas após falha; foto de tentativa nunca é apagada; só o dono lê | CI-03, CI-06 |
| CA-06 | RF-06 | Registro faltando, foto em envio, revisão antiga, rascunho encerrado | Tenta enviar | Recusa sem tentativa, avaliação ou evento | CI-04 |
| CA-07 | RF-07 | Rascunho completo com reflexão | Envia, repete a chave, concorre com edição atrasada | Uma tentativa imutável, avaliação pendente, um evento, rascunho encerrado; foto tardia recusada | CI-04, VM-01 |
| CA-08 | RF-08 | Foto com texto de instrução | Avaliador roda | Saída só em níveis permitidos ou inconclusivo, comentários predefinidos; entrada sem identificadores; sem foto em estado de execução ou log | CI-05 |
| CA-09 | RF-09 | Pesos 40/40/20 e níveis variados; resultado incompleto, nível fora do conjunto, comentário inexistente | Learning valida | Nota ponderada correta só com resultado válido; resultado inválido segue recuperação; evidência por Conceito separada | CI-05 |
| CA-10 | RF-10 | Observação inconclusiva que satisfaz condição de insuficiência | Avaliação conclui | Estado sem nota; sem zero, XP ou progresso; fotos e reflexão preservadas; verificação dos Conceitos aberta; novo envio liberado | CI-05, VM-03 |
| CA-11 | RF-11 | Falha do provedor, resposta inválida, incerteza sem insuficiência | Falha e Tentar novamente | Avaliação falha recuperável; retry reavalia a mesma tentativa sem novo envio; envios continuam bloqueados | CI-05, VM-03 |
| CA-12 | RF-12 | Tentativa concluída, sem nota, em andamento e falha | Abre resultado e histórico | Cada estado é distinto; sem nota nunca aparece como zero ou em andamento; fotos só do dono | CI-04, CI-07, VM-03 |
| CA-13 | RF-13 | Rascunho e tentativas com fotos; remoção de experiência, Objetivo e conta | Remove; avaliação ou upload chega depois | Dados e objetos eliminados em até 24 h; nada é recriado | CI-03, CI-06 |
| CA-14 | RF-14/15 | Desktop e mobile; falha de salvamento; sessão expirada | Usa por teclado e toque | Estados com texto e ícone, alvos ≥ 44 px, foco visível, sem promessa de outro dispositivo, restauração só após validação online | CI-07, CI-08, VM-01, VM-02, VM-04 |

## Design Contract

Arquivo Penpot **Shifu**, ID `c6f51e89-5d00-81ce-8008-e18d06c175af`, conectado e inspecionado pelo MCP em 21/11/2026. Página **🖥️ Desktop**, grupo `Culinária / Preparação prática` (11 boards de 1440 px). A página **📱 Mobile** não tem nenhum board desse grupo. O usuário aprovou explicitamente, em 21/11/2026, a dispensa dos boards mobile: o mobile é verificado por capturas em execução (ver a última linha da tabela).

| Superfície | Estado / viewport | Página / board | CA / verificação | Desvio aceito |
| --- | --- | --- | --- | --- |
| Página da Atividade | Inicial, 1440 | Desktop / `Culinária / Preparação prática / Desktop` (fotos prontas, botão Enviar Atividade) | CA-14 / VM-04 | Nenhum |
| Página da Atividade | Sem fotos, 1440 | `… / Sem fotos / Desktop` | CA-14 / VM-04 | Nenhum |
| Página da Atividade | Foto em envio, 1440 | `… / Foto em envio / Desktop` | CA-04, CA-14 / VM-04 | Nenhum |
| Página da Atividade | Falha na foto, 1440 | `… / Falha na foto / Desktop` | CA-04, CA-14 / VM-04 | Nenhum |
| Página da Atividade | Reflexão aberta, 1440 | `… / Reflexão aberta / Desktop` | CA-14 / VM-04 | Nenhum |
| Página da Atividade | Falha ao salvar rascunho, 1440 | `… / Falha ao salvar rascunho / Desktop` | CA-03, CA-14 / VM-04 | Nenhum |
| Página da Atividade | Envio, 1440 | `… / Envio da Atividade / Desktop` | CA-07 / VM-04 | Nenhum |
| Resultado | Avaliação em andamento, 1440 | `… / Avaliação em andamento / Desktop` | CA-12 / VM-04 | Nenhum |
| Resultado | Falha recuperável, 1440 | `… / Falha na avaliação / Desktop` | CA-11 / VM-04 | Nenhum |
| Resultado | Sem nota, 1440 | `… / Sem evidência avaliável / Desktop` | CA-10, CA-12 / VM-04 | Nenhum |
| Resultado | Concluída, 1440 | `… / Resultado da avaliação / Desktop` | CA-09, CA-12 / VM-04 | Nenhum |
| Todas as superfícies | 390 px | Mobile: **boards inexistentes** | CA-14 / VM-02, VM-04 | **Dispensa aprovada pelo usuário em 21/11/2026:** sem boards mobile, a verificação mobile usa capturas em execução a 390 px, avaliadas contra os boards desktop e os tokens. Layout em coluna única, sem corte, alvos ≥ 44 px. A dispensa é uma limitação registrada, não uma comparação visual passada. |

**Desvios aceitos adicionais (revisão 3):** rótulo da reflexão "Seu relato sobre a preparação (escrito por você)"; "Peso 40%" e descrição dos critérios; botão "Trocar foto"; linha "Formatos aceitos…"; linha de tamanho no lugar do nome do arquivo; sem imagem de referência, legenda e passos quando os dados não existem; breadcrumb com o título da Atividade; seta de reflexão que gira de direita para baixo; rótulos sob as miniaturas, ícones nos botões de ação e blocos "Registros a melhorar" e "Seu relato" no resultado; texto de orientação vindo do Currículo. A cor de erro usa o token semântico de texto de erro do design system.

O widget reutiliza botões primário e secundário, os papéis semânticos de superfície, texto, borda de controle e sucesso, erro e aviso definidos em `documentation/design.md` e em `apps/web/src/ui/shadcn/`. Não duplicar cores, espaços, tipografia, raios ou sombras. Preservar shell e demais formatos. Os valores exatos de tokens são confirmados na implementação contra o código e o Penpot.

# Technical Contract

## Architecture Mapping

Owner: Learning (rascunho, fotos, tentativa, avaliação, resultado), com Curriculum como autoridade da rubrica, Shared como contrato tipado e porta, Intelligence como adaptador de visão. Rules: Python, Core, Database, Provision, REST, Server App, Messaging, Jobs Testing, AI Layer, Controllers Testing, Use Case Testing, TypeScript, UI Layer, Web Routing (sem rota nova), Widget Testing, Validation Package, Commit Rules.

| Ação | Limite | Elemento / caminho | Alteração necessária |
| --- | --- | --- | --- |
| Criar | Curriculum Core | `PracticalPreparationQuestion` e estruturas de registro, critério, nível, condição de insuficiência em `curriculum/core/domain/structures/` | Variante da união `ActivityQuestion`, exportada em `__init__.py`. |
| Modificar | Curriculum Core/DB | `entities/activity.py`, `activity_mapper.py` | Regra de exatamente uma questão e de rubrica obrigatória; exclusão do diagnóstico; `_KIND_QUESTION_TYPES`, `_question_from_data`, `_part_from_data` e anotações. JSON existente, sem migração. |
| Modificar | Curriculum Provider | `curriculum_content_provider.py` (`_get_activity`, `has_executable_evidence`, contagem 3–5) | Contagem vira 1 quando a questão é de preparação prática; ramo do retrato; cláusula de evidência executável; revisão por hash. |
| Criar/Modificar | Shared Core | `curriculum_practical_preparation_*_snapshot.py`, `CurriculumLearningActivitySnapshot`, `__init__.py` | Retratos tipados; exceção de uma questão em `__post_init__`; `_validate_question_part`; exclusão do diagnóstico. |
| Criar | Shared Core | `PracticePhotoAssessorProvider` em `shared/core/interfaces/`, mais `PracticePhotoAssessmentInput` e `PracticePhotoDecisions` em `shared/core/domain/structures/` | Porta que recebe a rubrica e os bytes das fotos, lidos pelo workflow de Learning pelo provider de storage de Learning, e devolve decisões fechadas. O adaptador de Intelligence nunca lê o bucket de Learning. |
| Criar | Intelligence AI | agente de visão e saída estruturada em `intelligence/ai/agno/agents/`, adaptador em `intelligence/providers/` | Modelo `openai/gpt-6-luna`, ZDR, trava de prompts, `assert_inference_ready`, imagem tratada como dado não confiável; níveis 0/25/50/75/100 ou inconclusivo; composição em `IntelligenceWorkflowsRegistry` e `app.py`. |
| Modificar | Shared Providers/Settings/Pipes | `s3_file_storage_provider.py`, `shared/settings.py`, `file_storage_pipe.py`, `.env.example`, `docker-compose.yaml` | `S3FileStorageSettings` deixa de ser presa a `mentor_attachment_storage_*` e passa a ser uma configuração neutra (bucket, região, endpoint, estilo, chaves) que cada módulo preenche a partir do próprio prefixo. Learning ganha `LEARNING_PRACTICE_PHOTO_STORAGE_*` e uma fábrica no pipe que entrega ao módulo um `FileStorageProvider` próprio, montado em `app.py` e exposto por `LearningPipe`. A política de chave de objeto fica no Core de Learning. Bucket criado por `minio-init`. |
| Criar | Learning Core/DB | `PracticeDraft` e `PracticePhoto`, portas, modelos, mappers, repositórios e migração Alembic | Um rascunho ativo por experiência e Atividade com revisão; uma foto ativa por registro; FK com cascade; índices únicos parciais; marca de remoção. Migração gerada a partir da cabeça `46a3cef1cbec`. |
| Criar | Learning Core | casos de uso de ler rascunho, salvar reflexão, enviar/substituir foto, remover foto, descartar rascunho, ler foto, e `purge_practice_photos_use_case` | Gravação sob trava de linha da experiência; revisão crescente. O caso de uso de purga é a variante em lote usada pelo job de conta encerrada e pela remoção; o job de foto única apaga uma foto marcada. |
| Modificar | Learning Core | `remove_goal_use_case`, `remove_skill_from_goal_use_case`, `remove_skill_experience_from_mentor_use_case` | Antes de apagar as linhas, gravam na mesma transação um pedido de limpeza para cada foto do rascunho e das tentativas, pelo outbox. O cascade do banco só remove linhas, então sem isso os objetos ficariam órfãos. |
| Modificar | Learning Core | `SubmitChoiceActivityUseCase`, `activity_answer.py`, `normalize_answers`, `activity_attempt_mapper`, `snapshot_to_domain`, `GetChoiceActivityUseCase.is_eligible` | Resposta de preparação prática; posse das fotos passa à tentativa; encerra o rascunho; revisão do rascunho confere (Q7). |
| Modificar | Learning Core/DB | `ActivityEvaluationStatus`, `ActivityEvaluation`, `activity_evaluation_mapper`, `RetryChoiceEvaluationUseCase`, `GetChoiceAttemptUseCase`, `ChoiceAttemptDetail`, `find_unresolved…` | Estado terminal `closed_without_grade` sem migração (coluna `String(40)`); parte de avaliação com critérios, pesos, níveis e comentários; verificação de Conceitos por observação nula (Q11); leitores de status ajustados. |
| Criar | Learning AI | `evaluate_practical_preparation_activity_workflow.py` em `learning/ai/agno/workflows/` | Passo único que lê fotos por chave do storage, chama a porta, valida e conclui; fotos fora do estado de execução (`AgentOSHandoffStore` guarda só referência). |
| Modificar | Learning AI | `LearningWorkflowsRegistry` (`destination_for_event`, `_project_event`, `workflows`), `app.py`, `LearningPipe` | Destino `agentos:learning` e workflow novo para a questão; injeção do storage e da porta. |
| Criar | Learning Messaging | evento `PracticePhotoCleanupRequestedEvent`, job `PurgePracticePhotoJob`, job de conta encerrada, registro em `LearningInngestMessaging.register_jobs` | Apagar objeto fora da transação, novas tentativas, alerta em falha; marca só sai após confirmação. Telemetria dos nomes de job. O job de conta encerrada recebe o nome do evento de Identity como argumento explícito no registro, sem importar a classe de Identity, com payload próprio (conta e data) e prazo de 24 horas vindo do RP-29, como o job equivalente do Mentor. |
| Criar | Learning REST | seis controllers, um por arquivo: ler rascunho, salvar reflexão, enviar ou substituir foto, remover foto, ler foto, descartar rascunho; schemas; `activities.rest` | Registro em `learning/rest/router.py`. O schema do `kind` da resposta de envio está em `submit_choice_activity_controller.py` (`AnswerRequest`) e recebe a variante nova. |
| Criar/Modificar | Server App | `app.py`, novo middleware de corpo multipart do PUT de foto, `PrivateMentorNoStoreMiddleware` | O limite de 512 KiB só cobre POST e não é alterado. O middleware novo casa PUT nas rotas de foto, fica ao lado do limite de anexos do Mentor, e responde 413 e 400 no formato `{code, message}`. As rotas de foto recebem `Cache-Control: private, no-store`. |
| Modificar | Web | `choice-activity.ts`, `learning-service.ts`, um novo handler de API (`routes/api/learning/.../practice-photos`), `ActivityPage`, `ChoiceResultPage`, `ChoiceResultDetail` | Nenhuma página nova; um handler de API novo, no padrão do Mentor. Variantes de pergunta, resposta, resultado e status; widget novo; rascunho no servidor. |
| Modificar | Testes | fixtures de job e stub de storage de Learning | Stub em memória; variáveis de storage no subprocesso. |

Declarações públicas (Core):

```python
@structure
class PracticePhotoRecord:  # registro pedido pelo Currículo
    key: str
    label: str
    must_show: str

@structure
class PracticeCriterionLevel:
    score: int  # 0, 25, 50, 75, 100
    description: str
    comment_key: str

@structure
class PracticeCriterion:
    key: str
    name: str
    description: str
    weight: Decimal
    levels: tuple[PracticeCriterionLevel, ...]
    inconclusive_when: str

@structure
class PracticeInsufficiencyRule:
    record_key: str
    criterion_keys: tuple[str, ...]
    comment: str

@structure
class PracticalPreparationQuestion:
    key: str
    kind: Literal['practical_preparation']
    prompt: str
    guidance: tuple[str, ...]
    references: tuple[PracticeReference, ...]
    difficulty: str
    records: tuple[PracticePhotoRecord, ...]
    criteria: tuple[PracticeCriterion, ...]
    insufficiency_rules: tuple[PracticeInsufficiencyRule, ...]
    concept_criteria: tuple[ChoiceConceptCriterion, ...]

@entity
class PracticeDraft:
    id: str
    skill_experience_id: str
    activity_id: str
    reflection: str
    revision: int
    status: PracticeDraftStatus  # StrEnum: active, consumed

@entity
class PracticePhoto:
    id: str
    owner_kind: PracticePhotoOwnerKind  # StrEnum: draft, attempt
    draft_id: str | None
    attempt_id: str | None
    record_key: str
    object_key: str
    media_type: str
    size_bytes: int
    sha256: str
    state: PracticePhotoState  # StrEnum: uploading, ready, failed, removed
    upload_key: str
    removal_due_at: datetime | None

class PracticeDraftsRepository(Protocol):
    def find_active_for_update(self, skill_experience_id: str, activity_id: str) -> PracticeDraft | None: ...
    def add(self, draft: PracticeDraft) -> None: ...
    def update(self, draft: PracticeDraft) -> None: ...

class PracticePhotosRepository(Protocol):
    def list_ready_for_draft(self, draft_id: str) -> tuple[PracticePhoto, ...]: ...
    def find_by_upload_key(self, draft_id: str, upload_key: str) -> PracticePhoto | None: ...
    def add(self, photo: PracticePhoto) -> None: ...
    def update(self, photo: PracticePhoto) -> None: ...
    def reassign_to_attempt(self, draft_id: str, attempt_id: str) -> None: ...

class PracticePhotoAssessorProvider(Protocol):
    def assess(self, request: PracticePhotoAssessmentInput) -> PracticePhotoDecisions: ...
```

`PracticePhotoDecisions` traz, por critério, `level: Literal[0,25,50,75,100] | None` (nulo = inconclusivo) e `comment_key`, e por registro `sufficient: bool`. `LearningDatabaseRepositories` ganha `practice_drafts` e `practice_photos`. `ActivityEvaluationStatus` ganha `CLOSED_WITHOUT_GRADE`. Web (TypeScript): `PracticalPreparationQuestion`, `PracticalPreparationAnswer { kind, questionKey, draftRevision, reflection }`, `PracticalPreparationResultQuestion` com `criteria[{ key, name, weight, level, comment }]`, `photos[]`, `reflection`; `ChoiceAttemptStatus` ganha `'closed_without_grade'`.

Conceitos novos:

- **Rascunho e foto.** Estado privado de Learning. A foto pertence ao rascunho até o envio. Na transação de envio, `reassign_to_attempt` passa a posse à tentativa, sem copiar arquivo. O rascunho vira `consumed`. Foto tardia contra rascunho encerrado é recusada.
- **Remoção em dois tempos.** A foto removida muda para `removed` na hora (inacessível) e emite pedido de limpeza pelo outbox. O job apaga o objeto, confirma e só então limpa a marca. Sem cron nem varredura. Se uma tentativa usa a foto, o job não a apaga.
- **Estado sem nota.** Terminal, distinto de falha e de concluída. Não aplica efeito, libera `find_unresolved…` e expõe ação de nova tentativa.
- **Insuficiência.** Declarada por Learning quando o resultado validado satisfaz uma regra do Currículo (registro nomeado com os critérios indicados inconclusivos). Qualquer outra incerteza é falha recuperável.

Árvore esperada (`[N]` novo, `[M]` modificado, nomes privados e migração definidos na implementação):

```text
apps/server/
  migrations/versions/                                                    [N, nome gerado]
  rest-client/learning/activities.rest                                    [M]
  src/shifu/curriculum/core/domain/structures/practical_preparation_*.py  [N, planejados]
  src/shifu/curriculum/core/domain/structures/{activity_question,__init__}.py [M]
  src/shifu/curriculum/core/domain/entities/activity.py                   [M]
  src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py     [M]
  src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py [M]
  src/shifu/shared/core/domain/structures/curriculum_practical_preparation_*.py [N, planejados]
  src/shifu/shared/core/domain/structures/{curriculum_learning_activity_snapshot,__init__}.py [M]
  src/shifu/shared/core/interfaces/practice_photo_assessor_provider.py    [N]
  src/shifu/shared/providers/s3_file_storage_provider.py                  [M]
  src/shifu/shared/settings.py                                            [M]
  src/shifu/intelligence/ai/agno/agents/practice_photo_assessment_agent.py [N]
  src/shifu/intelligence/providers/practice_photo_assessor/*              [N]
  src/shifu/intelligence/ai/intelligence_workflows_registry.py            [M]
  src/shifu/learning/core/domain/entities/{practice_draft,practice_photo}.py [N]
  src/shifu/learning/core/domain/enums/activity_evaluation_status.py      [M]
  src/shifu/learning/core/domain/entities/activity_evaluation.py          [M]
  src/shifu/learning/core/domain/structures/{practical_preparation_answer,practice_*}.py [N]
  src/shifu/learning/core/domain/events/practice_photo_cleanup_requested_event.py [N]
  src/shifu/learning/core/interfaces/{practice_drafts_repository,practice_photos_repository}.py [N]
  src/shifu/learning/core/use_cases/{get_practice_draft,save_practice_reflection,upload_practice_photo,remove_practice_photo,discard_practice_draft,get_practice_photo,purge_practice_photos}_use_case.py [N]
  src/shifu/learning/core/use_cases/{submit_choice_activity,get_choice_activity,get_choice_attempt,retry_choice_evaluation,remove_goal,remove_skill_from_goal,remove_skill_experience_from_mentor}_use_case.py [M]
  src/shifu/learning/core/domain/enums/{practice_draft_status,practice_photo_state,practice_photo_owner_kind}.py [N]
  src/shifu/learning/database/sqlalchemy/{models,mappers,repositories}/practice_*.py [N]
  src/shifu/learning/database/sqlalchemy/mappers/{activity_attempt_mapper,activity_evaluation_mapper}.py [M]
  src/shifu/learning/ai/agno/workflows/evaluate_practical_preparation_activity_workflow.py [N]
  src/shifu/learning/ai/learning_workflows_registry.py                    [M]
  src/shifu/learning/messaging/inngest/jobs/{purge_practice_photo_job,purge_practice_data_on_account_deleted_job}.py [N]
  src/shifu/learning/messaging/inngest/learning_inngest_messaging.py      [M]
  src/shifu/learning/rest/controllers/{get_practice_draft,save_practice_reflection,upload_practice_photo,remove_practice_photo,get_practice_photo,discard_practice_draft}_controller.py [N]
  src/shifu/learning/rest/controllers/submit_choice_activity_controller.py [M]
  src/shifu/learning/rest/router.py                                       [M]
  src/shifu/learning/pipes/learning_pipe.py                               [M]
  src/shifu/app.py                                                        [M]
  tests/learning/core/use_cases/test_*practice*_use_case.py               [N, planejados]
  tests/learning/server/controllers/test_{get_practice_draft,save_practice_reflection,upload_practice_photo,remove_practice_photo,get_practice_photo,discard_practice_draft}_controller.py [N, planejados]
  tests/messaging/inngest/jobs/learning/test_purge_practice_photo_job.py  [N, planejado]
  tests/learning/ai/workflows/test_evaluate_practical_preparation_activity_workflow.py [N, planejado, em processo, agente simulado]
  apps/server/evals/practice_photo_assessment_eval.py                      [N, planejado]
  tests/learning/messaging/test_learning_inngest_messaging.py             [M, contagem de funções]
  tests/fixtures/{inngest_fixture,learning_fixture}.py                    [M]
apps/web/
  src/core/learning/choice-activity.ts                                    [M]
  src/rest/services/learning-service.ts                                   [M]
  src/routes/api/learning/**/practice-photos (handler de API BFF)         [N, planejado]
  tests/learning/practice-photo-api-handler.test.ts                       [N, planejado]
  src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts} [M]
  src/ui/learning/widgets/pages/activity-page/practical-preparation-question/{index.tsx,use-practical-preparation-question.ts} [N]
  src/ui/learning/widgets/pages/activity-page/practical-preparation-question/tests/{practical-preparation-question.test.tsx,use-practical-preparation-question.test.ts} [N]
  src/ui/learning/widgets/pages/choice-result-page/{index.tsx,use-choice-result-page.ts,choice-result-detail/index.tsx} [M]
  src/ui/learning/widgets/pages/{activity-page,choice-result-page}/tests/* [M]
  tests/learning/{activity-page,choice-result-page}.test.ts               [M]
docker-compose.yaml, apps/server/.env.example, .env.example                [M]
```

Seed e demonstração: `shared/database/seed_data.py` e fakers de Curriculum/Shared recebem só o exemplo de legumes salteados (3 registros: cortes, durante o preparo, prato final; pesos 40/40/20), como dados isolados de demonstração e teste.

Registro de decisão sobre o servidor: `ordering` (SHIFU-129) já existe no repositório e serve de modelo. Os fatos de código desta Spec vêm de leitura de 21/11/2026. Remover foto e salvar reflexão não exigem a revisão do cliente: a última gravação salva prevalece e só o envio confere a revisão (Q7). Cobertura da qualidade do agente de visão: a avaliação de respostas da IA fica em `apps/server/evals`, conforme a regra de IA, e o agente e o adaptador não têm teste direto; são exercidos indiretamente pelo teste em processo do workflow de Learning com o agente simulado.

## Runtime Flow

```mermaid
sequenceDiagram
  participant W as Web
  participant API as Learning REST
  participant DB as PostgreSQL
  participant S3 as Bucket privado
  participant OB as Outbox/Inngest
  participant AI as Workflow AgentOS + Intelligence
  W->>API: PUT foto (multipart, upload_key)
  API->>DB: trava experiência, reserva foto (uploading)
  API->>S3: put (tipo real, 10 MB, Pillow)
  API->>DB: ready, revisão do rascunho +1
  W->>API: POST envio (draftRevision)
  API->>DB: confere revisão, fotos, reflexão; tentativa+avaliação PENDING+evento; fotos→tentativa; rascunho consumed
  OB->>AI: activity-submission.requested
  AI->>S3: lê fotos por chave
  AI->>AI: porta de avaliação, validação, nota ou sem nota
  AI->>DB: conclui avaliação (idempotente por run_id)
  W->>API: GET resultado
```

1. Todas as rotas autenticam a conta e revalidam Objetivo, Habilidade, Competência, Atividade liberada e experiência do dono. Terceiros recebem recusa sem revelar existência.
2. Gravações do rascunho e das fotos rodam sob trava de linha da experiência; cada gravação incrementa a revisão. A última salva prevalece. Falha de armazenamento marca a foto como falha e emite limpeza.
3. O envio exige todos os registros com foto pronta, nenhuma em envio e a revisão do rascunho igual à do cliente (Q7). Conflito de revisão devolve o rascunho atual, sem tentativa.
4. O workflow nunca grava foto no estado de execução. Falha do provedor, resposta inválida ou incerteza viram falha recuperável; Tentar novamente cria novo `run_id` para a mesma tentativa.
5. O resultado validado alimenta a nota ponderada e a evidência por Conceito, ou a regra de insuficiência encerra sem nota e abre a verificação (Q11). Efeitos aplicam-se uma vez.
6. Remoção de experiência, Habilidade, Objetivo ou conta emite pedido de limpeza antes de apagar linhas; efeitos tardios conferem a existência da experiência antes de gravar.

# Verification Contract

## Shared setup

Contas de teste descartáveis e Atividade de preparação prática publicada por fixture isolada (exemplo 40/40/20, três registros, uma regra de insuficiência). Testes de controller usam TestClient, PostgreSQL Testcontainers e stub de storage em memória. O teste do job de limpeza usa as fixtures de `apps/server/tests/fixtures/inngest_fixture.py`, com as variáveis de storage de teste no subprocesso e um stub de storage em memória. O workflow de avaliação é testado em processo, com agente simulado e sem fixture que suba o AgentOS, como manda a regra de testes de jobs. Nenhum teste chama provedor de IA. Para os percursos reais: `docker compose ps`, saúde da API e da web, registro da função, login com `.playwright-cli/states/shifu-auth-state.json` local. Evidências só em `apps/web/.playwright-cli/`. Sem seed ou reset de banco compartilhado. Encerrar só processos iniciados pela task. Comandos de servidor seguem [Tooling](../../../tooling.md): `uv run poe test:unit`, `test:integration`, `test:jobs` e filtros pytest sobre os arquivos nomeados.

## Automated

### CI-01 — Conteúdo e projeção curricular
**Critérios:** CA-01, CA-02. **Prova:** teste de conformidade de domínio e de caso de uso de leitura (planejados em `tests/curriculum/core/domain/` e `tests/learning/core/use_cases/test_get_choice_activity_use_case.py`). Limites 0/1/5/6 registros, pesos, chaves, diagnóstico, uma questão. Passa se todos os casos executarem e a projeção pública não trouxer regras de insuficiência.

### CI-02 — Rascunho e concorrência
**Critérios:** CA-03. **Prova:** casos de uso de rascunho e controllers (planejados). Última gravação prevalece, revisão crescente, dois dispositivos, concorrência por trava. Passa com estado devolvido igual ao salvo.

### CI-03 — Upload, validação e limpeza
**Critérios:** CA-04, CA-05, CA-13. **Prova:** controller e caso de uso de foto, job de limpeza e job de conta (planejados). Classes: tipo, extensão, vazio, 10 MB e +1, não decodificável, chave repetida, objeto de tentativa preservado, nova tentativa após falha, dono apenas. Passa sem objeto remanescente após o job e sem linha recriada.

### CI-04 — Envio e idempotência
**Critérios:** CA-06, CA-07, CA-12. **Prova:** `test_submit_choice_activity_use_case.py` e controller. Passa com recusas sem efeito, uma tentativa por chave, fotos reatribuídas e rascunho encerrado, foto tardia recusada.

### CI-05 — Avaliação, nota e insuficiência
**Critérios:** CA-08–CA-11. **Prova:** casos de uso de avaliação e retry, controller de resultado e teste em processo do workflow em `tests/learning/ai/workflows/test_evaluate_practical_preparation_activity_workflow.py` (planejados). O mapeamento é provado por esses limites, sem teste direto de mapper. 40/40/20, níveis, inválidos, insuficiência sem zero e sem XP, falha e retry sobre a mesma tentativa, observação nula abrindo verificação, entrada da IA sem identificadores. Passa com os efeitos corretos e execução real dos testes.

### CI-06 — Jobs duráveis e migração
**Critérios:** CA-05, CA-13. **Prova:** `tests/messaging/inngest/jobs/learning/test_purge_practice_photo_job.py` e `tests/learning/messaging/test_learning_inngest_messaging.py`. Executar de `apps/server` com `$env:SHIFU_RUN_REAL_INNGEST_TESTS = '1'` conforme a SHIFU-129. Passa se o teste real não for pulado, a migração aplicar no contêiner e não houver efeito duplicado.

### CI-07 — Widget, páginas e handler de API
**Critérios:** CA-04, CA-12, CA-14. **Prova:** Vitest do widget novo e do hook próprio, das páginas afetadas, e o teste do handler de API de foto (`apps/web/tests/learning/practice-photo-api-handler.test.ts`, planejado), Playwright de `tests/learning/activity-page.test.ts` e `choice-result-page.test.ts` com transporte simulado. Passa com estados, teclado, foco e navegação.

### CI-08 — Tipos, lint, complexidade, arquitetura e build
**Escopo:** Python e TypeScript afetados. **Comandos:** `uv run poe check:types`, `check:lint`, `check:architecture`, `build` em `apps/server`; `pnpm --filter web check:types`, `check:lint`, `check:architecture`, `build` na raiz; `pnpm check:test-integrity` na raiz. Complexidade pelas regras configuradas do Biome e do Ruff `C90`; medição quantitativa independente não existe e fica Não aplicável. Passa com zero erros e avisos.

## Manual

### VM-01 — Atividade real em desktop
**Tipo:** Manual. **Critérios:** CA-02, CA-07, CA-14. Playwright CLI a 1440 px, login com estado local, abrir a Atividade de demonstração, enviar as três fotos, preencher reflexão, enviar e abrir o resultado. Confirmar URL, requisições, uma tentativa, console, foco e teclado.

### VM-02 — Retomada em outro dispositivo e mobile
**Tipo:** Manual. **Critérios:** CA-03, CA-14. Subir fotos, recarregar e abrir em outro contexto de navegador a 390 px. Confirmar rascunho restaurado só após validação da sessão, rolagem e alvos.

### VM-03 — Resultado real
**Tipo:** Manual. **Critérios:** CA-10–CA-12. Com avaliador de teste determinístico, conferir resultado concluído, sem nota e falha com Tentar novamente. Confirmar que "sem nota" não aparece como zero e persiste após retorno.

## Visual

### VM-04 — Comparação com Penpot
**Tipo:** Visual. **Critérios:** CA-14, CA-09–CA-12. Durante VM-01 a VM-03, comparar capturas novas do Playwright CLI com exportações novas do Penpot MCP dos 11 boards desktop e, após decisão do usuário, dos equivalentes mobile. Rodar contraste, alvos de toque, tipografia, contenção e sobreposição em todas as páginas do arquivo, corrigir e repetir até zero avisos.

# Documentation Alignment

| Documento / autoridade | Governa | Atualização ou confirmação | Estado / dependência |
| --- | --- | --- | --- |
| [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning), ID `83066881`, v35, versão confirmada em 21/11/2026 | RP-09/12/13/14/18/21/22/24/25/27/29/32; JN-07/08/26; aditivo SHIFU-98 | Trechos de RP-21/22 relidos em 21/11/2026; demais lidos por inteiro na preparação | Reconfirmar versão antes de `ready` e na conclusão. A task cita v31. |
| [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113/Shifu+PRD+Curriculum), ID `83034113`, v19 | RP-03; JN-03 | Lidos; a task cita v18 | Reconfirmar. |
| Política de Privacidade e Ciclo de Vida dos Dados, ID `100106241`, v4 | Eliminação e backups | Lida | Reconfirmar. |
| [Jira SHIFU-130](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-130) | Entrega | O "Próximo" da task equivale a "Enviar Atividade", que leva ao resultado | Sem escrita no Jira. |
| Penpot Shifu | Visual | Boards desktop existentes; mobile ausente | Decisão do usuário (Design Contract). |
| [Rule Pack](../../../rules.md), [Architecture](../../../architecture.md), [Modules](../../../modules.md), [Tooling](../../../tooling.md) | Código e testes | Rules lidas pelo escopo; reavaliar quando o escopo mudar | Revisão independente antes de `ready`. |

# Revision History

| Revisão | Data | Mudança de contrato | Motivo / fonte |
| --- | --- | --- | --- |
| 3 | 2026-11-22 | Metadados das fotos removidos (RF-15); desvios de design aceitos listados; regra de insuficiência por registro no exemplo. | Revisão independente de código e visual. |
| 2 | 2026-11-21 | RF-06: o envio na web espera a gravação pendente ou com falha da reflexão (decisão de implementação aceita pelo Orquestrador). | Relatório do construtor web. |
| 1 | 2026-11-21 | Contrato inicial, já com as correções do primeiro Spec Reviewer (caminho do teste de workflow, sem teste de mapper, removals, middleware de PUT, controllers nomeados, handler de API). | SHIFU-130, Learning v35, Curriculum v19, decisões Q1–Q11. |
