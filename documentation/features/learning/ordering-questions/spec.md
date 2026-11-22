---
title: Questões de ordenação de etapas em Atividades de aprendizagem
status: ready
revision: 1
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-129
scope:
  - Curriculum
  - Learning
  - Shared content contract
  - Web Learning
last_updated_at: 2026-11-12
---

# Objective

Adicionar a questão de ordenação de etapas às Atividades de aprendizagem. O aprendiz reorganiza todas as etapas, verifica uma única sequência por passagem e recebe retorno provisório objetivo. A tentativa e a nota oficiais surgem apenas no envio final. Este é um contrato completo, pois atravessa conteúdo, persistência, concorrência, avaliação durável e interface. O levantamento e as decisões de SHIFU-129 estão em [diagnóstico](../../../../SHIFU-129-diagnostico.md).

# Scope

| Área / ator | Incluído | Excluído ou adiado |
| --- | --- | --- |
| Autor de Curriculum | Questão de 3 a 8 etapas distintas, uma ou mais sequências completas aceitas, explicações fixas e critérios conceituais. A ordem inicial não é aceita. | Relações de precedência e autoria pela interface. O exemplo culinário fica em dados isolados de demonstração/teste, sem publicar uma Habilidade incompleta. |
| Aprendiz em Learning | Questão em Atividade de 3 a 5 partes, inclusive mista; verificação 100/0; resposta bloqueada e retomável em somente leitura pela conta; tentativa oficial no envio final. | Ordenação no Diagnóstico, crédito parcial, correção por IA e salvamento de respostas ainda editáveis. |
| Histórico e resultado | Ordem enviada e avaliação privada, com gabarito protegido até acerto posterior da questão ou domínio da Competência. | Alterar progresso, domínio, recompensa ou revisão além da aplicação já definida para Atividades. |
| Interface desktop/mobile | Controles de subir/descer, sem arrastar; estados inicial, correto e incorreto; foco, anúncios e alvos de toque acessíveis. | Novas rotas ou redesenho dos demais formatos. |

Entrega integral de Curriculum RP-03 para o formato selecionado e de Learning RP-33. As regras gerais selecionadas de Learning RP-09/13/14/18/25/27 continuam integrais no fluxo. A tarefa não entrega todas as modalidades desses requisitos gerais.

# Behavior Contract

| ID | RP/JN/fonte | Comportamento observável |
| --- | --- | --- |
| RF-01 | Curriculum RP-03/04/06; JN-03/04 | Curriculum valida 3–8 etapas com IDs e textos distintos, ao menos uma permutação completa aceita, uma permutação incorreta possível, explicações e critérios conceituais. Só Atividades de aprendizagem aceitam o formato. |
| RF-02 | Curriculum RP-03; Learning RP-09/33; JN-07 | A leitura privada da Atividade entrega etapas e ordem inicial completa incorreta, sem sequências aceitas, posições corretas ou explicações que revelem o gabarito. A mesma revisão mantém a ordem apresentada estável durante a passagem. |
| RF-03 | Learning RP-09/33; JN-07 | A primeira verificação conclusiva de cada questão de ordenação na passagem guarda na conta a sequência, revisão e retorno provisório imutáveis. A mesma verificação retorna o mesmo resultado; outra sequência é rejeitada até o envio final. O registro não cria tentativa, progresso, nota oficial ou recompensa. |
| RF-04 | Learning RP-09/33; JN-07 | Após sair ou trocar de dispositivo, o proprietário retoma sequência verificada e retorno em somente leitura. Respostas não verificadas dos outros formatos não são sincronizadas. O envio final usa a sequência verificada. |
| RF-05 | Learning RP-09/13/14; JN-07/08 | O envio final exige todas as respostas válidas e a revisão apropriada, congela a tentativa e usa a chave idempotente. O evento durável existente segue para Inngest quando não há código ou para o fluxo AgentOS de Learning quando há código. Uma nova passagem só pode verificar outra ordem após envio final autorizado. |
| RF-06 | Learning RP-27/33; Curriculum RP-03/04 | Cada sequência aceita recebe 100; qualquer outra permutação completa recebe 0, sem IA nem crédito parcial. A evidência por Conceito segue os critérios do Curriculum e a nota final mantém os pesos da Atividade. |
| RF-07 | Learning RP-13/14/18/20/25; JN-08/13 | Falha, pendência e recuperação preservam a tentativa imutável. O resultado privado usa o retrato submetido e mostra ordem, nota e explicação; não revela gabarito protegido. Revisão de Habilidade concluída não substitui resultado oficial. |
| RF-08 | Learning RP-09/25/33; JN-07 | Desktop e mobile permitem mover etapas por botões e teclado, anunciam a nova posição e distinguem estados por texto/ícone. Após verificar, a ordem fica em somente leitura; a ação inicial se chama **Verificar**. |
| RF-09 | Learning RP-09/29; JN-07 | Registro provisório pertence somente à conta/experiência, é consumido no envio final e desaparece na remoção da experiência ou da conta. Chamadas concorrentes não conseguem registrar duas ordens para a mesma questão e passagem. |

| ID | RF | Dado | Quando | Então | Prova |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Conteúdo com 2/3/8/9 etapas, IDs ou textos repetidos, ordens ausentes, incompletas, repetidas ou que cobrem todas as permutações | Curriculum valida/publica | Apenas conteúdos com 3–8 etapas e pelo menos uma ordem incorreta possível ficam elegíveis; Diagnóstico rejeita ordenação | CI-01 |
| CA-02 | RF-02 | Atividade liberada com escolha, código e ordenação | Dono lê a Atividade | Recebe 3–5 questões na ordem curricular, ordem inicial incorreta e estável, sem regra aceita ou explicação de gabarito | CI-02, VM-01 |
| CA-03 | RF-03/09 | Resposta completa, revisão atual e chave da passagem | Dono verifica pela primeira vez, repete ou concorre com outra ordem | Há um registro privado por passagem; mesma ordem/revisão devolve mesmo retorno; outra ordem conflita, sem tentativa ou efeito oficial | CI-03 |
| CA-04 | RF-03/06 | Ordens aceitas alternativas, ordem incorreta, resposta incompleta/duplicada e revisão vencida | Verifica | Permutações completas recebem 100/0 e explicação fixa; inválidas são rejeitadas; nenhuma decisão usa IA | CI-03 |
| CA-05 | RF-04/09 | Ordenação já verificada; demais respostas ainda não enviadas | Dono recarrega ou abre outro dispositivo; terceiro tenta ler | Dono recebe só a ordem verificada e retorno em somente leitura; terceiro não recebe; outras respostas não são restauradas | CI-03, CI-04, VM-02 |
| CA-06 | RF-05/09 | Questões mistas completas, registro provisório ativo e mesma chave de submissão | Envia, repete ou concorre; uma prévia antiga chega após o envio | Uma tentativa, avaliação pendente e evento durável; ordem oficial idêntica à verificada; registro deixa de ser ativo; prévia com chave consumida conflita; nova passagem usa chave nova após envio final | CI-04, CI-05, VM-01 |
| CA-07 | RF-05/07 | Avaliação pendente, falha, reentrega ou recuperação | Job de Inngest ou fluxo de código de Learning executa | Uma avaliação e efeitos oficiais no máximo uma vez; falha não vira zero nem perde resposta; recuperação usa a mesma tentativa | CI-05, CI-06 |
| CA-08 | RF-06/07 | Tentativa com ordenação correta/incorreta e pesos desiguais | Avaliação conclui | Partes, evidência por Conceito e nota ponderada corretas; resultado histórico mostra conteúdo submetido | CI-05, CI-06, VM-03 |
| CA-09 | RF-07 | Erro de ordenação antes de acerto posterior/domínio e após liberação | Lê resultado/HTTP | Gabarito não aparece antes da liberação; depois aparece só para o dono autorizado | CI-04, CI-05, VM-03 |
| CA-10 | RF-08 | Primeira/última etapa, estados inicial/correto/incorreto, desktop e mobile | Move/verifica/navega por teclado e toque | Controles extremos desabilitam, foco se mantém, nova posição é anunciada, alvos mobile têm ≥44 px e retorno é perceptível sem cor | CI-07, VM-01, VM-02, VM-04 |
| CA-11 | RF-09 | Registro ativo e remoção da experiência/conta | Exclui pelo fluxo autorizado | Registro desaparece; leitura, verificação ou envio posterior não recria experiência removida | CI-04, CI-06 |

## Design Contract

Arquivo Penpot **Shifu**, ID `c6f51e89-5d00-81ce-8008-e18d06c175af`. A página **🖥️ Desktop** contém o grupo `Culinária / Ordenação de etapas`. Os três boards de 1440 × 980 foram inspecionados e exportados pelo MCP em 12/11/2026. A página **📱 Mobile** ainda precisa dos três estados equivalentes, com largura de 390 px. A premissa visual aprovada em Q6/Q7 é adaptar os componentes desktop para mobile, com controles de subir/descer e conteúdo rolável; esses boards serão criados antes da comparação visual. Ajustar o primeiro desktop conforme as mesmas decisões. Se os boards novos exigirem mudança de comportamento, reconciliar o contrato antes de implementar. Os boards desktop de retorno preservam seus sinais de acerto/erro e nota provisória.

| Superfície | Estado / viewport | Página / board e componentes | CA / verificação | Desvio aceito |
| --- | --- | --- | --- | --- |
| Página de Atividade | Inicial, 1440 × 980 | Desktop / `Culinária / Ordenação de etapas / Desktop`; `Ordering / Main` | CA-10 / VM-04 | Trocar **Próxima questão** por **Verificar**, remover alça/instrução de arrastar, explicar ordem inicial. |
| Página de Atividade | Correta, 1440 × 980 | Desktop / `Culinária / Ordenação — Resposta correta / Desktop` | CA-10 / VM-04 | Ajustes coerentes com resposta em somente leitura. |
| Página de Atividade | Incorreta, 1440 × 980 | Desktop / `Culinária / Ordenação — Resposta incorreta / Desktop` | CA-10 / VM-04 | Não acrescentar gabarito protegido. |
| Página de Atividade | Inicial/correta/incorreta, 390 px | Mobile / três boards de ordenação a criar com componentes existentes | CA-10 / VM-04 | Altura pode crescer e rolar; sem corte de conteúdo nem obstrução da navegação. |

O widget reutiliza o botão primário/secundário existente e os papéis semânticos `--surface`, `--raised`, `--text-primary`, `--text-secondary`, `--control-border`, `--selo-fill` e tokens de sucesso/erro definidos em `documentation/design.md`. Não duplicar cores, espaços, tipografia, raios ou sombras. Preservar shell, formatos de escolha/código e demais telas. Verificar contraste, foco e estados em todos os temas aplicáveis.

# Technical Contract

## Architecture Mapping

Curriculum é autoridade de conteúdo e gabarito. Shared transporta apenas um retrato tipado entre módulos. Learning possui autorização, registro provisório, tentativa, avaliação e histórico. A web possui apresentação e estado de interação. Regras selecionadas: Python/TypeScript, Core, casos de uso, provision, banco, REST, controllers, servidor, mensagens/jobs, UI, rotas existentes e testes de widgets, conforme `documentation/rules.md`.

| Ação | Limite | Elemento / caminho | Alteração necessária |
| --- | --- | --- | --- |
| Modificar | Curriculum Core/DB | `ActivityQuestion`, `ActivityMapper` | Variante de ordenação com IDs estáveis, ordens aceitas privadas, explicações e critérios; leitura/escrita compatível com JSON histórico; rejeição no Diagnóstico. |
| Modificar | Provider/Shared | `DatabaseCurriculumContentProvider.get_learning_activity`, `CurriculumLearningActivitySnapshot` | Retrato privado tipado e revisão estável; projeção pública sem regras aceitas. Despacho misto também quando há ordenação sem código. |
| Criar | Learning Core/DB | Passagem provisória de ordenação, porta em `LearningDatabaseRepositories`, modelo, mapper, repositório e migração Alembic | Um registro ativo por experiência e Atividade. Ele guarda as questões já verificadas, cada uma com ordem/revisão/retorno imutáveis. Chave única da passagem, índice único parcial para passagem ativa, lock transacional, FK com exclusão em cascata e estado consumido no envio. |
| Modificar | Learning Core | `GetChoiceActivityUseCase`, `PreviewActivityQuestionFeedbackUseCase`, `SubmitChoiceActivityUseCase` | Autorizar leitura/retomada, validar permutação, persistir e bloquear verificação, congelar a ordem no envio idempotente. |
| Modificar | Learning Core/DB | `EvaluateChoiceActivityUseCase`, `GetChoiceAttemptUseCase`, mappers de tentativa/avaliação | Corrigir 100/0, registrar evidência, manter histórico/revisão e proteção do gabarito. |
| Modificar | REST/composição | Controllers de leitura, prévia, envio e resultado; schemas, pipes, registro de repositórios; `activities.rest` | Ampliar uniões de request/response e erros, conectar porta transacional e documentar exemplos sem credenciais. Manter métodos e rotas existentes. |
| Confirmar/modificar | Inngest/AgentOS | `EvaluateChoiceActivityJob`, `LearningWorkflowsRegistry.destination_for_event` e fluxo de código existente | Retrato misto sem código segue para Inngest; com código segue para AgentOS de Learning. Os dois usam a correção objetiva de ordenação; não acionar IA para ordenar. Alterar registro/fluxo apenas se a nova variante exigir. |
| Criar/modificar | Web | contratos `choice-activity.ts`, `learning-service.ts`, `ActivityPage`, `ChoiceResultPage`, widget de ordenação | Mapear união discriminada; exibir/mover/bloquear/retomar ordem, detalhe histórico e cache de Atividade após verificação/envio. |

Declarações públicas planejadas, usando o estilo das estruturas de Core existentes. Cada classe abaixo ocupa seu próprio módulo:

```python
@structure
class OrderingStep:
    key: str
    text: str

@structure
class OrderingQuestion:
    key: str
    prompt: str
    steps: tuple[OrderingStep, ...]
    accepted_orders: tuple[tuple[str, ...], ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[ChoiceConceptCriterion, ...]

@structure
class CurriculumOrderingStepSnapshot:
    key: str
    text: str

@structure
class CurriculumOrderingQuestionSnapshot:
    key: str
    kind: Literal['ordering']
    prompt: str
    steps: tuple[CurriculumOrderingStepSnapshot, ...]
    accepted_orders: tuple[tuple[str, ...], ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...]

@structure
class OrderingAnswerSubmission:
    question_key: str
    ordered_step_keys: tuple[str, ...]

@structure
class VerifiedOrdering:
    question_key: str
    ordered_step_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str

@entity
class OrderingPassage:
    id: str
    skill_experience_id: str
    activity_id: str
    passage_key: str
    activity_revision: str
    grading_snapshot: CurriculumLearningActivitySnapshot
    verified_orderings: tuple[VerifiedOrdering, ...]
    status: Literal['active', 'consumed']

    @classmethod
    def create(
        cls, *, id: str, skill_experience_id: str, activity_id: str,
        passage_key: str, activity_revision: str,
        grading_snapshot: CurriculumLearningActivitySnapshot,
    ) -> 'OrderingPassage': ...

    def add_verified(self, item: VerifiedOrdering) -> None: ...
    def consume(self) -> None: ...

class OrderingPassagesRepository(Protocol):
    def find_active(self, skill_experience_id: str, activity_id: str) -> OrderingPassage | None: ...
    def find_by_key(self, skill_experience_id: str, activity_id: str, passage_key: str) -> OrderingPassage | None: ...
    def add(self, passage: OrderingPassage) -> None: ...
    def update(self, passage: OrderingPassage) -> None: ...
```

`ActivityQuestion`, `ActivityAnswer` e `CurriculumLearningActivitySnapshot.questions` incluem a nova variante. `CurriculumChoicePartSnapshot` continua a parte ponderada para questão objetiva; seus campos de peso são suficientes. `LearningDatabaseRepositories` acrescenta `ordering_passages: OrderingPassagesRepository`. A porta oferece busca da passagem ativa ou consumida por experiência/Atividade/chave, inclusão atômica de uma questão verificada e consumo transacional. `PreliminaryQuestionResult` mantém seus campos atuais e recebe a correção 100/0. A leitura da Atividade acrescenta a ordem inicial segura e o registro verificado para o dono. O POST existente de prévia aceita `{activity_revision, passage_key, answer: {kind: 'ordering', question_key, ordered_step_keys}}`; o POST de envio inclui `passage_key` e exige as mesmas ordens já verificadas. `passage_key` é um UUID novo gerado pelo cliente ao abrir a Atividade sem passagem ativa. Não é credencial nem substitui autorização. Respostas de escolha/código e seus valores `kind` existentes permanecem compatíveis. Os limites de comprimento e erros de transporte seguem os schemas atuais.

`OrderingPassage` é uma entidade de estado de Learning com ID estável. A fábrica inicia a passagem ativa, `add_verified` acrescenta apenas uma questão ainda não verificada e `consume` faz a transição irreversível para consumida. O banco impõe unicidade de `(skill_experience_id, activity_id, passage_key)` e de uma única passagem `active` por `(skill_experience_id, activity_id)`. A versão do JSON persistido é explícita para leitura futura. As respostas e resultados oficiais seguem os mappers JSON existentes, ampliados para o discriminante `ordering`; linhas históricas de escolha/código continuam legíveis. Não é necessária uma coluna nova na tentativa, mas a tabela da passagem exige migração Alembic.

No contrato TypeScript existente, as extensões públicas são:

```ts
type OrderingQuestion = {
  key: string
  kind: 'ordering'
  prompt: string
  steps: readonly { key: string; text: string }[]
  initialOrderedStepKeys: readonly string[]
  verified: null | {
    orderedStepKeys: readonly string[]
    score: number
    isCorrect: boolean
    explanation: string
  }
}
type OrderingAnswer = {
  kind: 'ordering'
  questionKey: string
  orderedStepKeys: readonly string[]
}
type OrderingResultQuestion = {
  kind: 'ordering'
  key: string
  prompt: string
  steps: readonly { key: string; text: string }[]
  submittedStepKeys: readonly string[]
  score: number
  isCorrect: boolean
  explanation: string
  acceptedOrders?: readonly (readonly string[])[]
}
```

`ActivityQuestion`, `ActivityAnswer` e `ActivityResultQuestion` incluem essas variantes. `ChoiceActivityDetail` acrescenta `orderingPassageKey: string | null` para uma passagem ativa; sem passagem ativa, o cliente cria a chave UUID em memória. `ChoiceSubmission` acrescenta `passageKey?: string` apenas quando há ordenação. O mapper REST converte `ordered_step_keys` e os campos de retomada do GET para esses nomes; `acceptedOrders` contém todas as sequências aceitas somente após a liberação autorizada. Nenhum hook de infraestrutura novo é necessário.

A passagem provisória pertence a Learning. Seu registro guarda somente respostas de ordenação já verificadas, retornos, revisão e o retrato curricular necessário para retomada e envio. Não guarda respostas ainda editáveis. A primeira verificação cria a passagem; outras questões de ordenação usam a mesma `passage_key`. A verificação e sua repetição são serializadas por bloqueio da experiência na mesma transação; índices únicos protegem concorrência. Uma chave diferente enquanto existe passagem ativa conflita e leva o cliente a reler a passagem. O envio final usa o mesmo bloqueio, confirma resposta/revisão, cria tentativa/avaliação/outbox na transação existente e marca a passagem como consumida. O marcador consumido permanece para rejeitar uma prévia atrasada com a mesma chave; uma nova chave é aceita somente após envio final e ausência de avaliação bloqueadora. A exclusão da experiência/conta remove ambos os estados por cascata. Uma revisão curricular nova não altera silenciosamente uma passagem em andamento: a retomada e o envio usam o retrato privado congelado na primeira verificação. Sem passagem ativa, a leitura usa a revisão atual do Curriculum. A ordem inicial é calculada no servidor e nunca é uma ordem aceita.

Árvore esperada, limitada aos contratos e testes afetados. `[N]` indica arquivo novo e `[M]` arquivo existente. Nomes privados e arquivo gerado da migração serão definidos na implementação.

```text
apps/server/
  migrations/versions/                                             [N, arquivo com nome gerado pelo Alembic]
  rest-client/learning/activities.rest                                [M]
  src/shifu/curriculum/core/domain/structures/activity_question.py   [M]
  src/shifu/curriculum/core/domain/structures/ordering_step.py       [N, planejado]
  src/shifu/curriculum/core/domain/structures/ordering_question.py   [N, planejado]
  src/shifu/curriculum/core/domain/structures/__init__.py            [M]
  src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py [M]
  src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py [M]
  src/shifu/shared/core/domain/structures/curriculum_learning_activity_snapshot.py [M]
  src/shifu/shared/core/domain/structures/curriculum_ordering_step_snapshot.py [N, planejado]
  src/shifu/shared/core/domain/structures/curriculum_ordering_question_snapshot.py [N, planejado]
  src/shifu/shared/core/domain/structures/__init__.py                [M]
  src/shifu/learning/core/domain/structures/ordering_answer.py        [N, nome planejado]
  src/shifu/learning/core/domain/structures/activity_answer.py       [M]
  src/shifu/learning/core/domain/structures/__init__.py              [M]
  src/shifu/learning/core/domain/structures/verified_ordering.py      [N, planejado]
  src/shifu/learning/core/domain/entities/ordering_passage.py        [N, planejado]
  src/shifu/learning/core/interfaces/ordering_passages_repository.py [N, nome planejado]
  src/shifu/learning/core/interfaces/learning_database.py             [M]
  src/shifu/learning/core/interfaces/__init__.py                     [M]
  src/shifu/learning/core/use_cases/{get_choice_activity_use_case,preview_activity_question_feedback_use_case,submit_choice_activity_use_case,evaluate_choice_activity_use_case,get_choice_attempt_use_case}.py [M]
  src/shifu/learning/database/sqlalchemy/{models,mappers,repositories}/ordering_passage_*.py [N, nomes planejados]
  src/shifu/learning/database/sqlalchemy/learning_database.py          [M]
  src/shifu/learning/database/sqlalchemy/models/__init__.py           [M, registro para Alembic]
  src/shifu/learning/rest/controllers/{get_choice_activity_controller,preview_activity_question_feedback_controller,submit_choice_activity_controller,get_choice_attempt_controller}.py [M]
  src/shifu/learning/messaging/inngest/jobs/evaluate_choice_activity_job.py [M se necessário]
  src/shifu/learning/ai/learning_workflows_registry.py                [M se necessário]
  tests/curriculum/core/domain/test_ordering_question.py               [N, planejado]
  tests/learning/core/use_cases/test_{get_choice_activity,preview_activity_question_feedback,submit_choice_activity,evaluate_choice_activity,get_choice_attempt}_use_case.py [M]
  tests/learning/server/controllers/test_{get_choice_activity,preview_activity_question_feedback,submit_choice_activity,get_choice_attempt}_controller.py [M]
  tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py [M]
apps/web/
  src/core/learning/choice-activity.ts                              [M]
  src/rest/services/learning-service.ts                             [M]
  src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts} [M]
  src/ui/learning/widgets/pages/activity-page/ordering-question/{index.tsx,use-ordering-question.ts,ordering-question.css} [N, planejados]
  src/ui/learning/widgets/pages/activity-page/ordering-question/tests/{ordering-question.test.tsx,use-ordering-question.test.ts} [N, planejados]
  src/ui/learning/widgets/pages/choice-result-page/{index.tsx,use-choice-result-page.ts} [M]
  src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/index.tsx [M]
  src/ui/learning/widgets/pages/{activity-page,choice-result-page}/tests/* [M, seleções afetadas]
  tests/learning/{activity-page,choice-result-page}.test.ts          [M]
documentation/design.md                                              [M, alinhado ao PRD v33]
```

Os arquivos de registro/composição de modelos, repositórios, schemas e pipes já existentes serão modificados onde a inspeção da implementação mostrar os pontos de montagem. Isso não cria um novo provedor de UI. O `RestContextProvider` e o serviço Learning existentes continuam a direção das dependências. `use-activity-page.ts` é dono da resposta, verificação e retomada compartilhadas pela página; o hook colocalizado do widget possui apenas movimento, foco e anúncio. O resultado recebe dados já autorizados e não decide liberação do gabarito. Não se criam suites diretas de mapper, repository, provider, serviço REST ou hook de query/action.

## Runtime Flow

1. Curriculum valida e persiste o conteúdo. O provider entrega o retrato privado para Learning; a leitura de Learning autoriza conta, objetivo, Habilidade, Competência e Atividade liberada e projeta apenas etapas e ordem inicial segura.
2. O aprendiz move etapas na web. A prévia recebe IDs ordenados, revisão e chave da passagem. Learning rejeita resposta parcial/duplicada, revisão incompatível e acesso indevido. Na primeira verificação válida, bloqueia a experiência e grava passagem, sequência e retorno 100/0. Uma repetição idêntica lê o mesmo resultado; outra ordem conflita.
3. Após recarga, Learning lê a passagem ativa pela conta. A página usa a chave da passagem, reinicia respostas não salvas dos outros formatos, conserva a ordenação verificada e permite prosseguir sem editá-la. Não publica gabarito.
4. O envio final valida 3–5 respostas e as ordenações congeladas da mesma passagem. A transação cria tentativa imutável, avaliação pendente e evento de outbox, marca a passagem consumida. Repetição da chave de submissão devolve a tentativa existente sem novo efeito. Prévia tardia com a chave consumida conflita; nova passagem usa outra chave após envio autorizado.
5. O destino existente escolhe Inngest para a Atividade sem código e o fluxo AgentOS de Learning para a Atividade com código. Ambos aplicam a correção objetiva de ordenação pela lógica de Learning, sem IA para esse formato. A avaliação aplica efeitos oficiais uma vez e mantém recuperação para falha ou pendência. A leitura do resultado usa o retrato submetido, filtra gabarito e apresenta ordem e explicação autorizadas. Remoção da experiência/conta impede recriação por evento tardio.

# Verification Contract

## Shared setup

Usar contas de teste descartáveis e Atividade publicada por fixture isolada com três a cinco questões, inclusive escolha + ordenação e código + ordenação, pesos desiguais, duas ordens aceitas e uma errada. Verificar vínculo Objetivo–Habilidade–Competência, liberação, revisão e estado inicial antes da execução. Testes de controller usam TestClient registrado e PostgreSQL Testcontainers. Teste de job usa Inngest e PostgreSQL descartáveis de `apps/server/tests/fixtures/inngest_fixture.py`. Não aplicar seed/reset no banco compartilhado. Para percurso real, verificar `docker compose ps`, saúde da API/web, registro da função, autenticação visível e estado local de Playwright; guardar evidência só em `apps/web/.playwright-cli/`. Encerrar apenas processos iniciados pela task.

## Automated

### CI-01 — Conteúdo e projeção curricular

**Critérios:** CA-01/02. **Prova planejada:** `apps/server/tests/curriculum/core/domain/test_ordering_question.py` (novo) e `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py`. Selecionar limites 2/3/8/9, IDs/textos, ordens alternativas, ordem inicial incorreta e ausência de gabarito. Executar `uv run pytest tests/curriculum/core/domain/test_ordering_question.py tests/learning/core/use_cases/test_get_choice_activity_use_case.py` de `apps/server`. Passa se todos os casos executarem e não houver conteúdo inválido publicado nem regra privada no transporte.

### CI-02 — Leitura privada e Atividade mista

**Critérios:** CA-02. **Prova planejada:** `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py` e `apps/web/tests/learning/activity-page.test.ts`. Executar `uv run pytest tests/learning/server/controllers/test_get_choice_activity_controller.py` de `apps/server` e `pnpm --filter web exec playwright test tests/learning/activity-page.test.ts` da raiz. Passa com acesso do dono, rejeição segura de terceiros, 3–5 questões e despacho de ordenação sem código.

### CI-03 — Prévia, bloqueio e concorrência

**Critérios:** CA-03/04/05. **Prova planejada:** `apps/server/tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py` e `apps/server/tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py`. Executar `uv run pytest tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py` de `apps/server`. Passa com 100/0, validação, repetição idempotente, concorrência, retomada entre contas/dispositivos e nenhum efeito oficial.

### CI-04 — Envio, histórico e exclusão

**Critérios:** CA-05/06/09/11. **Prova planejada:** testes focados de `test_submit_choice_activity_use_case.py`, `test_get_choice_attempt_use_case.py` e controllers correspondentes. Executar `uv run pytest tests/learning/core/use_cases/test_submit_choice_activity_use_case.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py tests/learning/server/controllers/test_submit_choice_activity_controller.py tests/learning/server/controllers/test_get_choice_attempt_controller.py` de `apps/server`. Passa com uma tentativa por chave, mesma ordem verificada, prévia antiga rejeitada após envio, histórico congelado, proteção do gabarito, exclusão em cascata e sem recriação.

### CI-05 — Correção oficial e evidência

**Critérios:** CA-06/08/09. **Prova planejada:** `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` e `test_get_choice_attempt_use_case.py`. Executar `uv run pytest tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py` de `apps/server`. Passa com ordens aceitas alternativas, zero incorreto, critérios de Conceito, pesos, revisão e proteção de resposta.

### CI-06 — Job durável e migração

**Critérios:** CA-07/08/11. **Prova planejada:** `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` com evento real registrado e Testcontainers. Executar de `apps/server`, em PowerShell, `$env:SHIFU_RUN_REAL_INNGEST_TESTS = '1'; uv run pytest tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`. As fixtures `apps/server/tests/fixtures/postgres_fixture.py` e `inngest_fixture.py` criam PostgreSQL descartável e executam `python -m alembic upgrade head` em subprocesso com `DATABASE_URL` injetada do contêiner. Os testes de controller afetados verificam unicidade, cascata e leitura de linhas históricas nesse banco. Não usar `poe db:upgrade`, que carrega `.env.local`. O fluxo com código é verificado pelos casos de uso/controllers e no percurso manual real, conforme a regra de AI para discriminantes sem mudança do workflow. Passa se o teste real não for pulado, a migração for aplicada no contêiner e não houver efeitos duplicados ou perda de linhas históricas.

### CI-07 — Widget, páginas e rotas existentes

**Critérios:** CA-05/10. **Prova planejada:** `apps/web/src/ui/learning/widgets/pages/activity-page/ordering-question/tests/{ordering-question.test.tsx,use-ordering-question.test.ts}` (novos), testes de página afetados e `apps/web/tests/learning/{activity-page,choice-result-page}.test.ts`. Da raiz, executar `pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/ordering-question/tests/ordering-question.test.tsx src/ui/learning/widgets/pages/activity-page/ordering-question/tests/use-ordering-question.test.ts src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts src/ui/learning/widgets/pages/choice-result-page/tests/choice-result-page.test.tsx` e `pnpm --filter web exec playwright test tests/learning/activity-page.test.ts tests/learning/choice-result-page.test.ts`. Passa com movimentos, limites, foco, anúncio, bloqueio, retomada, avanço, histórico e navegação. Os cenários Playwright automatizados usam transporte simulado; não substituem VM-01/03.

### CI-08 — Tipos do Web e consumidores

**Escopo:** contratos e widgets web afetados. **Comando:** `pnpm --filter web check:types` da raiz. Passa com o projeto configurado inteiro sem erro ou aviso de tipos; não usar `tsc` sobre arquivos avulsos.

### CI-09 — Tipos do Server e consumidores

**Escopo:** Curriculum, Shared, Learning e composição afetados. **Comando:** `uv run poe check:types` de `apps/server`. Passa sem erro ou aviso de basedpyright.

### CI-10 — Lint e formato

**Escopo:** fontes/testes alterados nas duas aplicações. **Comandos após integração:** `pnpm --filter web check:lint` da raiz e `uv run poe check:lint` de `apps/server`. Durante construção, executar `pnpm exec biome check` nos caminhos web alterados, `uv run ruff check --no-fix` e `uv run ruff format --check` nos caminhos Python alterados, com a seleção real registrada em Evaluation. Passa com zero erros e avisos sem correção automática nem afrouxar regras.

### CI-11 — Complexidade configurada

**Escopo:** lógica nova de validação, prévia, envio, avaliação e widget. **Verificadores:** regras de complexidade do Biome pelo comando web de CI-10 e `C90` do Ruff pelo comando server de CI-10; registrar seus diagnósticos e limites efetivos separadamente de lint. Passa com zero avisos/erros de complexidade. Não existe medidor quantitativo independente configurado e este contrato não exige pontuação quantitativa; registrar **não aplicável** para essa medição, sem inventar resultado.

### CI-12 — Arquitetura e build

**Escopo:** ambas as aplicações e consumidores afetados. **Comandos:** `pnpm --filter web check:architecture` e `pnpm --filter web build` da raiz; `uv run poe check:architecture` e `uv run poe build` de `apps/server`. Passa sem violação, erro ou aviso. Se uma rota passar a mudar, executar `pnpm --filter web generate-routes` antes do build e ampliar os testes de rota afetados.

## Manual

### VM-01 — Atividade real em desktop

**Tipo:** Manual. **Critérios:** CA-02/06/10. Abrir Atividade liberada como dono no Playwright CLI a 1440 px. Mover etapas por teclado, verificar, navegar e enviar todas as partes. Confirmar URL, requisições reais, uma tentativa/avaliação/outbox no servidor, retorno provisório antes e nota oficial depois; inspecionar console e foco. Repetir o percurso com código + ordenação para confirmar o destino de avaliação existente. Capturar estados inicial/correto/incorreto com fixtures isoladas.

### VM-02 — Retomada real em mobile

**Tipo:** Manual. **Critérios:** CA-05/10. Após verificar uma ordem, sair e reabrir a 390 px em outra sessão autenticada da mesma conta. Confirmar mesma ordem e retorno em somente leitura, demais respostas não restauradas, rolagem e ausência de corte. Inspecionar requisições, console, foco e alvos de toque. Não inserir credenciais ou estado de sessão na evidência.

### VM-03 — Resultado real e privacidade

**Tipo:** Manual. **Critérios:** CA-08/09. Abrir resultado de tentativa incorreta e posterior acerto ou domínio. Confirmar ordem enviada, nota, explicação, progresso, gabarito oculto/liberado conforme regra, URL e persistência após retorno. Inspecionar HTTP, DOM, console e foco em desktop/mobile.

## Visual

### VM-04 — Comparação com Penpot

**Tipo:** Visual. **Critério:** CA-10. Durante VM-01/02, comparar capturas novas do Playwright CLI com exportações novas pelo Penpot MCP dos três estados desktop e três mobile. Conferir layout, tokens, tipografia, estados, contenção, foco e alvos de toque; aceitar somente desvios anotados no Design Contract. Ler shapes e rodar checagens de toque, contraste, tipografia, contenção e sobreposição em **todas as páginas** do arquivo Shifu, corrigindo avisos e verificando novamente. Evidência e achados pertencem a `evaluation.md`, sem bundle visual no diretório da feature.

# Documentation Alignment

| Documento / autoridade | Governa | Atualização ou confirmação | Estado / dependência |
| --- | --- | --- | --- |
| [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning), ID `83066881`, v33, parent `82804737`, atualizado 13/11/2026 01:18:41 UTC | RP-09/13/14/18/20/25/27/29/33; JN-07/08/13 | Página completa relida após emenda; contrato de registro provisório confirmado | Reconfirmar versão antes de `ready` e na conclusão. |
| [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113/Shifu+PRD+Curriculum), ID `83034113`, v19, parent `82804737`, atualizado 02/11/2026 17:48:59 UTC | RP-03/04/06; JN-03/04 | Página completa lida e reconfirmada em 12/11/2026 | Reconfirmar versão antes de `ready`. |
| [Jira SHIFU-129](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-129), ID `12671` | Entrega e rastreio | Escopo reconciliado com PRDs atuais | Sem transição ou comentário autorizado. |
| [Diagnóstico](../../../../SHIFU-129-diagnostico.md), [Design](../../../design.md), [SDD](../../../sdd.md), [Architecture](../../../architecture.md), [Modules](../../../modules.md), [Tooling](../../../tooling.md) | Decisões locais, limites e validação | Design alinhado a Learning v33; artefatos de implementação e `evaluation.md` após aprovação da Spec | O diagnóstico não substitui Spec/Evaluation. |
| [Rule Pack](../../../rules.md) | Código e testes selecionados na Architecture Mapping, inclusive regra AI do fluxo misto com código | Ler regras correspondentes antes de cada novo escopo; reavaliar se rotas, geração ou outros módulos mudarem | Revisão independente da Spec antes de `ready`. |

# Revision History

| Revisão | Data | Mudança de contrato | Motivo / fonte |
| --- | --- | --- | --- |
| 1 | 2026-11-12 | Contrato inicial de ordenação, registro provisório privado, fluxo oficial, design e provas. | SHIFU-129, Learning v33, Curriculum v19 e decisões Q1–Q8. |
