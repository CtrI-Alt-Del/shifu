---
title: Questões integradas React + Fastify em Atividades de aprendizagem
status: completed
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-90
scope:
  - Learning
  - Curriculum
  - Shared contracts
last_updated_at: 2026-10-25
---

# Objective

Entregar uma questão integrada React + Fastify dentro das Atividades de aprendizagem. O aluno edita uma única resposta composta pelo frontend e pela API, experimenta a comunicação no navegador e recebe avaliações por rubrica. Learning conserva a autoridade sobre a nota, as tentativas e seus efeitos.

Modo **complete**, pois a mudança envolve execução de código no navegador, isolamento, concorrência de rascunhos, snapshots persistidos e admissão assíncrona. Base pesquisada: `8ee992a7`. A implementação atual suporta escolhas, JavaScript com entrada padrão e React. Não possui discriminador integrado, processo Fastify, operação HTTP de prática ou terminal interativo integrado.

# Scope

| Área / ator | Incluído | Excluído |
| --- | --- | --- |
| Aprendiz autenticado | Questão integrada em Atividade disponível de 3–5 questões; sequência atual, prática, rascunho, rubrica pública, retorno preliminar, envio e histórico | Diagnóstico integrado; formatos independentes React/Fastify; voltar para editar questão já avançada |
| Curriculum | Projeto inicial, dois pontos de entrada, dependências fixas, comandos autorizados, exemplos HTTP e permissão opcional de arquivos adicionais | Autoria na interface, currículo dinâmico, nova política pedagógica |
| Learning | Validação autoritativa, snapshot imutável, recuperação e efeitos únicos na infraestrutura existente | Outra avaliação, nota por execução, nova regra de progresso ou recompensa |
| Navegador | Prévia isolada, terminal restrito e painel HTTP; autosave local por conta | Shell livre, pacotes escolhidos pelo aluno, configuração editável, sincronização entre dispositivos |

Todos os resultados selecionados abaixo são **partial** no PRD completo. O recorte integrado descrito nesta Spec deve ser entregue integralmente. Não se declara concluído um requisito para outros formatos ou jornadas.

| Fonte | Resultado selecionado |
| --- | --- |
| Curriculum RP-03 / JN-03 | Uma questão com frontend/API e regras curriculares completas |
| Learning RP-09 / JN-07 | Rascunho local e envio completo imutável |
| Learning RP-11 / RP-12 / JN-07 | Prática integrada e avaliação preliminar por rubrica |
| Learning RP-13 / RP-14 / JN-08 | Nota oficial completa, recuperação e efeitos únicos |
| Learning RP-18 / JN-11 / JN-13 | Resposta e resultado históricos recuperáveis |
| Learning RP-25 | Responsividade, teclado e pt-BR |
| Learning RP-24 / RP-29 | Contexto mínimo na avaliação e ciclo de vida dos arquivos pessoais |

A especificação não altera o PRD nem conclui SHIFU-112 ou SHIFU-23. O inventário visual único é [design/handoff.md](design/handoff.md).

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | Curriculum RP-03/JN-03; Learning RP-09/RP-11/JN-07 | Uma questão `react_fastify` contém frontend e API na mesma resposta. Pode coexistir com os tipos já implementados. Curriculum fornece arquivos, entradas, dependências, comandos, exemplos e rubrica. O tipo é proibido em diagnóstico. Tipos desconhecidos falham de forma explícita. |
| RF-02 | Curriculum RP-03; Learning RP-11 | Somente arquivos iniciais editáveis e adicionais autorizados podem integrar a resposta. Projeto/configuração/dependências fixos não podem ser alterados pelo aluno. A permissão adicional informa diretórios, extensões e quantidade. A ação Novo arquivo existe somente no explorador, com ícone de arquivo com +. |
| RF-03 | Learning RP-11/JN-07 | Em navegador compatível a prática inicia automaticamente, atualiza frontend/API após edições e disponibiliza prévia, terminal e painel HTTP. Estados de inicialização, atualização, pronto, erro e indisponibilidade são textuais. Não existe botão Executar. Falha de prática não bloqueia edição, avaliação ou envio e não atribui nota. |
| RF-04 | Learning RP-11; Curriculum RP-03 | React acessa a API do mesmo projeto por caminhos internos. O painel HTTP recebe método, rota e corpo aplicável e mostra status/resposta. Só envia por ação do aluno. Edições, troca de aba e reinício não repetem uma requisição do painel. O terminal só aceita comandos curriculares suportados, sem shell livre. |
| RF-05 | Learning RP-11/RP-24/RP-29 | O projeto de prática permanece separado da origem, sessão e credenciais do Shifu. HTTP de prática não pode apontar à aplicação ou a outro destino. A avaliação recebe apenas enunciado, arquivos efetivos autorizados e rubrica. Não executa código no servidor nem recebe histórico do Mentor ou dados de identificação desnecessários. |
| RF-06 | Learning RP-09/RP-29 | Arquivos editáveis iniciais e adicionais são salvos localmente por conta, experiência, Atividade, questão e revisão curricular. Logout/login no mesmo navegador preserva o rascunho. A interface confirma salvamento ou informa falha e risco de perda ao sair. Não cria tentativa ou progresso. |
| RF-07 | Learning RP-09/RP-29 | Entre abas prevalece a última gravação confirmada no armazenamento. Uma gravação antiga não sobrescreve geração mais recente. Restauração exige leitura autoritativa online da experiência/revisão. Remoção confirmada invalida o rascunho e impede sua recriação por abas antigas. Logout e sessão expirada preservam o rascunho sem permitir sua restauração por outra conta. |
| RF-08 | Curriculum RP-03; Learning RP-11/RP-12 | Antes de avaliar, Como será avaliado mostra nomes e pesos públicos reais. A avaliação preliminar congela os arquivos e mostra nota provisória, pesos, níveis e comentários curriculares, com resposta somente leitura. Inconclusão obrigatória mantém nota ausente, bloqueia avanço e permite reavaliar a mesma resposta congelada. Nenhum efeito oficial é gravado. |
| RF-09 | Learning RP-09/RP-13/RP-14/JN-07/JN-08 | Apenas o envio completo cria tentativa imutável e inicia avaliação oficial. Repetição idêntica da chave de envio recupera a mesma tentativa. Falhas/inconclusões obrigatórias preservam resposta e snapshot, sem zero artificial ou nota parcial definitiva. A recuperação usa a mesma tentativa e aplica efeitos uma única vez. Novos envios ficam bloqueados somente naquela experiência enquanto existir avaliação não resolvida. |
| RF-10 | Learning RP-18/JN-11/JN-13 | Retorno posterior mostra o resultado oficial e seus arquivos integrados somente leitura. Alteração curricular posterior não reinterpreta o snapshot histórico. Resultado não inicia prática. Remoção da experiência ou encerramento da conta impede novos efeitos tardios e acesso indevido conforme os limites afetados de RP-29. |
| RF-11 | Learning RP-25; SHIFU-90 | Editor, explorador, criação autorizada, prévia, HTTP, terminal, avaliação e histórico são utilizáveis em desktop/mobile e por teclado, em pt-BR. Mantêm foco visível, rótulos, estados anunciados e preferência de movimento reduzido. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Atividade mista e contrato integrado válido | Consultar, carregar e avançar | Questão única integrada preserva os outros tipos; diagnóstico/tipo desconhecido são recusados | CI-01, CI-02, CI-04 |
| CA-02 | RF-02 | Política ausente/presente | Criar ou enviar arquivos | Somente arquivos autorizados são aceitos; configuração, caminhos inválidos, duplicados, colisões e excesso são recusados sem tentativa | CI-01, CI-02, CI-03, VM-01 |
| CA-03 | RF-03 | Navegador compatível e projeto executável | Abrir e editar frontend/API | Inicialização automática e saída atualizada; estados independentes e descarte do ambiente anterior | CI-03, CI-04, VM-01 |
| CA-04 | RF-04 | API pronta com rotas de exemplo | Interagir na prévia, enviar HTTP e usar terminal | React comunica com API; status/corpo aparecem; só comandos permitidos; edição não repete HTTP do painel | CI-03, CI-04, VM-01 |
| CA-05 | RF-03/RF-05 | Origem insegura, prática indisponível ou falha | Tentar praticar, editar e avaliar | Destinos/credenciais indevidos são recusados; interface continua editável e avaliável; nenhuma nota é derivada da prática | CI-01, CI-03, CI-04 |
| CA-06 | RF-06 | Conta A com arquivos editados | Aguardar gravação, sair e entrar novamente | Arquivos corretos são restaurados apenas para A; falha de storage avisa risco de perda; nenhuma tentativa existe | CI-03, CI-04, VM-02 |
| CA-07 | RF-07 | Duas abas e gerações concorrentes | Gravar, invalidar ou reconectar | Última gravação confirmada prevalece; restauração não atravessa conta/experiência/revisão ou tombstone | CI-03, CI-04, VM-02 |
| CA-08 | RF-08 | Projeto com arquivos adicionais e rubrica real | Consultar critérios e avaliar | Pesos/nomes reais, retorno completo somente leitura e contagens oficiais inalteradas | CI-01, CI-02, CI-03, VM-01 |
| CA-09 | RF-08 | Resposta congelada inconclusiva | Reavaliar após mudança do rascunho em outra aba | Bytes congelados são os mesmos; avanço continua bloqueado até conclusão | CI-01, CI-02, CI-03 |
| CA-10 | RF-09 | Atividade completa e chave estável | Enviar/repetir envio | Uma tentativa, um snapshot e uma admissão para `agentos:learning`; conflito não altera a tentativa existente | CI-01, CI-02, VM-01 |
| CA-11 | RF-09/RF-10 | Avaliação pendente/com falha e resposta salva | Recuperar, repetir resultado ou remover experiência | Mesma resposta/tentativa; nota final apenas completa; efeitos únicos; remoção impede efeitos tardios | CI-01, CI-02, VM-01 |
| CA-12 | RF-10 | Tentativa avaliada | Sair, voltar e alterar currículo em fixture isolada | Histórico usa snapshot, rubrica e arquivos originais somente leitura e não inicia WebContainer | CI-01, CI-02, CI-04, VM-01 |
| CA-13 | RF-11 | Desktop 1440×900 e mobile 390×844 | Percorrer estados requeridos com teclado | Ações acessíveis, foco visível, pt-BR e ausência de overflow da página; aparência conforme handoff | CI-03, CI-04, VM-01, VM-02, VM-03, VM-04 |

# Technical Contract

## Architecture Mapping

**Dono:** Learning para experiência, avaliações e arquivos pessoais. Curriculum para conteúdo. Shared possui somente snapshots neutros. A relação completa de regras e as divergências pesquisadas constam em Documentation Alignment.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Curriculum Core | `react_fastify_question.py` e `react_fastify_http_example.py` | Uma estrutura por módulo; declaração integrada, referências a comandos e validação curricular; exportar pela união e barrel |
| Create | Shared Core | `curriculum_react_fastify_question_snapshot.py` e `curriculum_react_fastify_http_example_snapshot.py` | Uma estrutura por módulo; snapshot neutro completo para consumo sem importação entre módulos |
| Modify | Curriculum Core/Provider/Database | Activity, ActivityQuestion, CurriculumContentProvider e ActivityMapper | Reconhecer, validar, projetar, calcular revisão e desserializar o novo tipo |
| Modify | Learning Core | CodeQuestionDetail; seis casos consumidores e code_answer_validation | Expor contrato seguro, preservar discriminador, normalizar arquivos, avaliar e ler snapshots |
| Modify | Learning REST/Database | Controladores existentes e ActivityAttemptMapper | Ampliar uniões HTTP e persistir/reler o snapshot sem quebrar registros antigos; atualizar activities.rest |
| Modify | Learning AI composition | LearningWorkflowsRegistry.destination_for_event | Reconhecer a nova questão como código e selecionar o workflow Learning existente |
| Create | Web Core/Provision | ReactFastifyPracticeRunner e adapter WebContainer | Dois processos, estados separados, prévia, HTTP restrito, comandos e descarte |
| Modify | Web REST/Route/Page/Result | LearningService, rota atual, ActivityPage, QuestionFeedback e ChoiceResultDetail | União integrada e composição com factories injetadas; apresentação e histórico |
| Create | Web UI | ReactFastifyQuestion e painéis internos | Estado único de arquivos/ambiente; interações dos painéis isoladas por responsabilidade |
| Create | Test support | Fixture curricular integrada e runtime manual descartável | Preparação executável sem semear ou modificar o banco compartilhado |
| Modify | Test authorities/tooling | Core/UseCase/Database/AI/Provision/WidgetTesting/Controllers Rules, Tooling, scripts/check-test-integrity.mjs, apps/server/pyproject.toml e .github/workflows/server-app-ci.yaml | Reconciliar conformidade de domínio sem consumidor, preparação pública, capacidade NLP e contrato interno BFF. Sem exceções gerais de providers ou serviços. |
| Modify / Relocate | Maintenance tests | Limites canônicos de CI-09 | Preservar todas as invariantes, cenários de NLP/índice, telemetria e transporte dos14 caminhos herdados. Conformidade de construtores permanece apenas onde não há consumidor que possua o comportamento. |
| Create / Delete | Controller tests | Quatro módulos `test_{get_choice_activity,preview_activity_question_feedback,submit_choice_activity,get_choice_attempt}_controller.py`: de `tests/learning/rest/controllers/` para `tests/learning/server/controllers/` | Realocar os módulos existentes e ampliar os mesmos donos, sem suítes paralelas. Remover apenas as quatro cópias antigas após migração |
| Create / Delete | Test helper | `tests/learning/rest/controllers/react_controller_fixture.py` para `tests/fixtures/react_activity_fixture.py` | Preservar ReactControllerFixture e seus dados. Atualizar os quatro imports consumidores. Nenhum outro teste importa esse auxiliar na base pesquisada |
| Create | Documentation | Esta Spec e design/handoff.md com referências | Contrato e inventário visual. Evaluation somente no início da implementação |

### Árvore esperada

`[N]` significa arquivo planejado novo. `[M]` significa arquivo existente modificado. Os testes novos ainda não existem. Não há exclusão ou saída gerada de produção. Os quatro módulos HTTP e seu auxiliar React são realocados do layout legado conforme o mapeamento abaixo.

```text
apps/server/
├── src/shifu/
│   ├── curriculum/
│   │   ├── core/domain/
│   │   │   ├── entities/activity.py [M]
│   │   │   └── structures/
│   │   │       ├── react_fastify_http_example.py [N]
│   │   │       ├── react_fastify_question.py [N]
│   │   │       ├── activity_question.py [M]
│   │   │       └── __init__.py [M]
│   │   ├── providers/curriculum_content_provider/curriculum_content_provider.py [M]
│   │   └── database/sqlalchemy/mappers/activity_mapper.py [M]
│   ├── shared/core/domain/structures/
│   │   ├── curriculum_react_fastify_http_example_snapshot.py [N]
│   │   ├── curriculum_react_fastify_question_snapshot.py [N]
│   │   ├── curriculum_learning_activity_snapshot.py [M]
│   │   └── __init__.py [M]
│   └── learning/
│       ├── core/domain/structures/code_question_detail.py [M]
│       ├── core/use_cases/
│       │   ├── code_answer_validation.py [M]
│       │   ├── get_choice_activity_use_case.py [M]
│       │   ├── preview_activity_question_feedback_use_case.py [M]
│       │   ├── submit_choice_activity_use_case.py [M]
│       │   ├── prepare_code_activity_evaluation_use_case.py [M]
│       │   ├── evaluate_choice_activity_use_case.py [M]
│       │   └── get_choice_attempt_use_case.py [M]
│       ├── rest/controllers/
│       │   ├── get_choice_activity_controller.py [M]
│       │   ├── preview_activity_question_feedback_controller.py [M]
│       │   └── submit_choice_activity_controller.py [M]
│       ├── database/sqlalchemy/mappers/activity_attempt_mapper.py [M]
│       └── ai/learning_workflows_registry.py [M]
├── rest-client/learning/activities.rest [M]
└── tests/
    ├── fixtures/react_activity_fixture.py [N: auxiliar React realocado]
    ├── fixtures/react_fastify_activity_fixture.py [N]
    ├── support/react_fastify_browser_runtime.py [N]
    └── learning/
        ├── core/use_cases/
        │   ├── test_get_choice_activity_use_case.py [M]
        │   ├── test_preview_activity_question_feedback_use_case.py [M]
        │   ├── test_submit_choice_activity_use_case.py [M]
        │   ├── test_prepare_code_activity_evaluation_use_case.py [M]
        │   ├── test_evaluate_choice_activity_use_case.py [M]
        │   └── test_get_choice_attempt_use_case.py [M]
        └── server/controllers/
            ├── test_get_choice_activity_controller.py [N: realocado]
            ├── test_preview_activity_question_feedback_controller.py [N: realocado]
            ├── test_submit_choice_activity_controller.py [N: realocado]
            └── test_get_choice_attempt_controller.py [N: realocado]

apps/web/
├── src/
│   ├── core/learning/
│   │   ├── choice-activity.ts [M]
│   │   └── react-fastify-practice-runner.ts [N]
│   ├── provision/learning/react-fastify-webcontainer-practice-runner.ts [N]
│   ├── rest/services/learning-service.ts [M]
│   ├── routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/
│   │   └── activities/$activityId/index.tsx [M]
│   └── ui/learning/widgets/pages/
│       ├── activity-page/
│       │   ├── index.tsx [M]
│       │   ├── use-activity-page.ts [M]
│       │   ├── react-fastify-question/
│       │   │   ├── index.tsx [N]
│       │   │   ├── use-react-fastify-question.ts [N]
│       │   │   ├── project-panel/index.tsx [N]
│       │   │   ├── preview-panel/index.tsx [N]
│       │   │   ├── http-panel/
│       │   │   │   ├── index.tsx [N]
│       │   │   │   ├── use-http-panel.ts [N]
│       │   │   │   └── tests/use-http-panel.test.ts [N]
│       │   │   ├── terminal-panel/
│       │   │   │   ├── index.tsx [N]
│       │   │   │   ├── use-terminal-panel.ts [N]
│       │   │   │   └── tests/use-terminal-panel.test.ts [N]
│       │   │   └── tests/
│       │   │       ├── react-fastify-question.test.tsx [N]
│       │   │       └── use-react-fastify-question.test.ts [N]
│       │   ├── question-feedback/
│       │   │   ├── index.tsx [M]
│       │   │   └── use-question-feedback.ts [M]
│       │   └── tests/
│       │       ├── activity-page.test.tsx [M]
│       │       ├── use-activity-page.test.ts [M]
│       │       ├── use-activity-page-routing.test.ts [M]
│       │       └── use-activity-page-route.test.ts [M]
│       └── choice-result-page/choice-result-detail/
│           ├── index.tsx [M]
│           └── tests/choice-result-detail.test.tsx [M]
└── tests/learning/
    ├── activity-page.test.ts [M]
    └── choice-result-page.test.ts [M]
```

Os testes dos painéis ficam no diretório `tests/` do respectivo dono, conforme os caminhos da árvore.

**Consumidores e contratos preservados.** `CodeAnswer` e `CodeSubmittedFile` do Core Python já transportam arquivos e `kind: str | None`. Suas declarações permanecem. As uniões e os ramos de reconhecimento em todos os caminhos mapeados acima passam a incluir `react_fastify`. Os schemas de versões anteriores continuam decodificáveis. O `CodeRubricAssessorProvider`, `CodeRubricAssessmentInput`, o workflow `EvaluateCodeActivityWorkflow`, seus outputs e a composição do provedor Jev permanecem inalterados. Não criar agente, prompt, modelo, workflow ou integração por formato.

### Declarações públicas novas e alteradas

As declarações abaixo fixam o formato público. Cada classe nova fica no próprio módulo nomeado na árvore e é reexportada no barrel do dono. Os blocos agrupam apenas a apresentação, não autorizam várias estruturas no mesmo arquivo. Decoradores/importações seguem as convenções de cada módulo. `ReactInitialFile`, `ReactDependency`, `ReactPermittedCommand` e `ReactAdditionalFilePolicy` são os objetos já existentes em Curriculum. O uso no novo tipo não transfere regras a Shared.

```python
from typing import Literal

@structure
class ReactFastifyHttpExample:
    key: str
    title: str
    method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    path: str
    body: str | None = None

@structure
class ReactFastifyQuestion:
    key: str
    prompt: str
    initial_files: tuple[ReactInitialFile, ...]
    frontend_entrypoint: str
    api_entrypoint: str
    fixed_dependencies: tuple[ReactDependency, ...]
    permitted_commands: tuple[ReactPermittedCommand, ...]
    frontend_command_id: str
    api_command_id: str
    http_examples: tuple[ReactFastifyHttpExample, ...]
    concept_criteria: tuple[CodeConceptCriterion, ...]
    additional_file_policy: ReactAdditionalFilePolicy | None
    kind: Literal['react_fastify'] = 'react_fastify'
```

O novo conceito é uma única questão curricular com dois programas cooperantes. Sua fonte de verdade é Curriculum. As duas entradas devem existir como arquivos iniciais editáveis distintos. Os comandos de inicialização são referências a IDs únicos da lista curricular. Dependências têm versões exatas e incluem React, React DOM, Vite e Fastify. Exemplos são dados fictícios de prática, nunca testes de correção ou dados pessoais. IDs/títulos de exemplo são não vazios e únicos. Caminhos de exemplo seguem as restrições HTTP de Runtime Flow.

Shared publica estes snapshots imutáveis, sem imports de Curriculum ou Learning:

```python
@structure
class CurriculumReactFastifyHttpExampleSnapshot:
    key: str
    title: str
    method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    path: str
    body: str | None = None

@structure
class CurriculumReactFastifyQuestionSnapshot:
    key: str
    prompt: str
    initial_files: tuple[CurriculumReactInitialFileSnapshot, ...]
    frontend_entrypoint: str
    api_entrypoint: str
    fixed_dependencies: tuple[CurriculumReactDependencySnapshot, ...]
    permitted_commands: tuple[CurriculumReactPermittedCommandSnapshot, ...]
    frontend_command_id: str
    api_command_id: str
    http_examples: tuple[CurriculumReactFastifyHttpExampleSnapshot, ...]
    concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...]
    additional_file_policy: CurriculumReactAdditionalFilePolicySnapshot | None
    kind: Literal['react_fastify'] = 'react_fastify'
```

A união `CurriculumLearningActivitySnapshot.questions` inclui o novo tipo. A revisão curricular inclui todos os novos campos.

Em `CodeQuestionDetail`, preservar todos os membros atuais e acrescentar somente este trecho. `entrypoint` permanece para tipos anteriores; no integrado continua igual a `frontend_entrypoint` por compatibilidade com consumidores existentes.

```python
frontend_entrypoint: str | None = None
api_entrypoint: str | None = None
frontend_command_id: str | None = None
api_command_id: str | None = None
http_examples: tuple[CurriculumReactFastifyHttpExampleSnapshot, ...] = ()
```

As assinaturas dos casos de uso permanecem, inclusive `execute(account_id, goal_id, skill_id, competency_id, activity_id, ...)`. A identidade continua vindo de `AuthenticatedUser`. A revisão e os arquivos entram pelos contratos existentes. A validação central preserva o discriminador na resposta normalizada e mantém o limite configurado em preparação, reenvio e avaliação.

No Web, adicionar à declaração existente em `choice-activity.ts`:

```typescript
export type ReactFastifyHttpMethod =
  | 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS'

export type ReactFastifyHttpExample = {
  key: string
  title: string
  method: ReactFastifyHttpMethod
  path: string
  body: string | null
}

export type ReactFastifyQuestion = Omit<ReactQuestion, 'kind' | 'entrypoint'> & {
  kind: 'react_fastify'
  frontendEntrypoint: string
  apiEntrypoint: string
  frontendCommandId: string
  apiCommandId: string
  httpExamples: readonly ReactFastifyHttpExample[]
}
```

`ActivityQuestion` inclui esse tipo. `CodeAnswer.kind` e `CodeResultQuestion.kind` tornam-se `'javascript_stdin' | 'react' | 'react_fastify'`. Os demais membros permanecem. O serviço mapeia nomes snake_case/camelCase explicitamente e rejeita discriminadores desconhecidos.

O novo port Web não expõe clientes do SDK ou URLs de API ao widget:

```typescript
import type {
  ReactPracticeCommand, ReactPracticeFile, ReactAdditionalFilePolicy,
} from './react-practice-runner'
import type { ReactFastifyHttpMethod } from './choice-activity'

export type ReactFastifyPracticeStatus =
  | 'idle' | 'starting' | 'updating' | 'ready' | 'error' | 'unavailable'

export type ReactFastifyPracticeProject = {
  files: readonly ReactPracticeFile[]
  frontendEntrypoint: string
  apiEntrypoint: string
  fixedDependencies: readonly { name: string; version: string }[]
  permittedCommands: readonly ReactPracticeCommand[]
  frontendCommandId: string
  apiCommandId: string
  additionalFilePolicy?: ReactAdditionalFilePolicy
}

export type ReactFastifyPracticeEvent = {
  frontendStatus: ReactFastifyPracticeStatus
  apiStatus: ReactFastifyPracticeStatus
  previewUrl: string | null
  terminalText: string
}

export type ReactFastifyPracticeHttpRequest = {
  method: ReactFastifyHttpMethod
  path: string
  body?: string
}

export type ReactFastifyPracticeHttpResponse = {
  status: number
  headers: readonly { name: string; value: string }[]
  body: string
  truncated: boolean
}

export type ReactFastifyPracticeRunner = {
  start(project: ReactFastifyPracticeProject): Promise<void>
  updateFile(path: string, content: string): Promise<void>
  addFile(file: ReactPracticeFile): Promise<void>
  request(
    request: ReactFastifyPracticeHttpRequest,
    signal?: AbortSignal,
  ): Promise<ReactFastifyPracticeHttpResponse>
  runCommand(commandId: string): Promise<void>
  restart(): Promise<void>
  subscribe(listener: (event: ReactFastifyPracticeEvent) => void): () => void
  dispose(): void
}
```

O adapter exporta `ReactFastifyWebContainerPracticeRunner(): ReactFastifyPracticeRunner`. A rota o injeta como `reactFastifyRunnerFactory?: () => ReactFastifyPracticeRunner` em ActivityPage. Acrescentar a propriedade às duas variantes existentes de ActivityPageProps, mantendo seus demais membros. A propriedade atual `reactDraftStore?: ReactQuestionDraftStore` e a construção padrão em useActivityPage continuam fornecendo o armazenamento. Não há novo contexto ou duplicação do armazenamento.

`ReactFastifyQuestion` no UI recebe o contrato público abaixo, derivado de `ReactQuestionProps` já exportado pelo widget React. Isso preserva suas propriedades de escopo, progresso, disponibilidade, callbacks e draftStore:

```typescript
import type { ReactQuestionProps } from '@/ui/learning/widgets/pages/activity-page/react-question/use-react-question'
import type { ReactFastifyQuestion as ReactFastifyQuestionModel } from '@/core/learning/choice-activity'
import type { ReactFastifyPracticeRunner } from '@/core/learning/react-fastify-practice-runner'

export type ReactFastifyQuestionProps = Omit<
  ReactQuestionProps, 'question' | 'runnerFactory'
> & {
  question: ReactFastifyQuestionModel
  runnerFactory?: () => ReactFastifyPracticeRunner
}
```

O hook dono retorna arquivos, seleção, estado de gravação, política, validade, estado da prática e handlers de edição, seleção, criação e avaliação. ActivityPage possui respostas congeladas e sequência da Atividade. O hook integrado possui apenas a resposta editável atual e a assinatura do runner.

`ProjectPanel` e `PreviewPanel` são renderizadores puros. O primeiro compõe CodeFileTree/CodeEditor e recebe arquivos, seleção e callbacks. O segundo recebe status/URL já validados. `HttpPanel` recebe exemplos curriculares, prontidão e callback de requisição. Seu hook possui campos, resposta/erro e um AbortController por envio. `TerminalPanel` recebe transcript, comandos e callback por ID. Seu hook possui linha de comando e a instância xterm.js; não recebe ou expõe um shell. Esses dois hooks permanecem dentro do dono. Seus props devem ser derivados desses contratos, sem armazenar outra cópia dos arquivos ou do estado de transporte.

As operações remotas atuais `getActivityAction`, `previewActivityQuestionAction` e `submitActivityAction` continuam em ActivityPage. Consulta, avaliação/reavaliação e envio usam as mesmas ações já existentes. Não criar query/action hook novo ou teste dedicado de serviço. Preservar a política atual de leitura autoritativa e refetch. Equivalência do conteúdo/revisão não desmonta a questão nem perde arquivos congelados. Após envio aceito, invalidar somente o rascunho da Atividade e atualizar os consumidores atuais do resultado.

### Contratos HTTP, persistência e composição

O prefixo abaixo é `/learning/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/activities/{activity_id}`.

- `GET <prefixo>`: 200 com a questão integrada, campos adicionais de CodeQuestionDetail, política e critérios públicos. Não enviar comentários ocultos, níveis de referência ou gabaritos.
- `POST <prefixo>/questions/{question_key}/preliminary-evaluations`: corpo atual `{activity_revision, answer}` com `answer = {kind: 'react_fastify', question_key, files: [{path, content}]}`. 200 com o resultado preliminar existente, `criteria` e `submitted_files`.
- `POST <prefixo>/attempts`: corpo atual `{submission_key, activity_revision, answers}`, com todas as questões válidas. 201 na criação, 200 no replay idêntico. Mesma chave com outro conteúdo retorna conflito. Não aceitar campos de escolha em uma resposta integrada.
- `GET <prefixo>/attempts/{attempt_id}` e `POST <prefixo>/attempts/{attempt_id}/retry` mantêm formatos e status atuais. O resultado usa `kind: 'react_fastify'` e arquivos salvos. Exemplos de consulta/recuperação ficam em `rest-client/learning/activities.rest`.

Manter semântica existente de 401 para falta de autenticação, 404 para recurso privado ausente/alheio, 409 para conflito/revisão incompatível e 422 para formato HTTP inválido. Erros de domínio seguem o mapeamento atual de `ValidationError` e `ConflictError`. Falha de infraestrutura não se torna erro pedagógico. Todos os exemplos REST usam variáveis e dados fictícios, sem segredos.

`ActivityModel.questions` e `ActivityAttemptModel.answers/grading_snapshot` já são JSON. Os mappers devem reconhecer o discriminador sem alterar o formato antigo. Não é prevista migração Alembic nem backfill. Nenhuma resposta antiga é regravada ou reinterpretada. Transações pertencem exclusivamente ao contexto LearningDatabase. Tentativa, avaliação pendente e outbox são atômicos. A unicidade por experiência/chave e as cercas de execução/remoção atuais permanecem.

`learning/activity-submission.requested` e seu payload existente permanecem. LearningWorkflowsRegistry reconhece `CurriculumReactFastifyQuestionSnapshot` e escolhe `agentos:learning` para Atividades com código. O workflow registrado continua `learning-evaluate-code-activity`, com ticket durável contendo `attempt_id` e `run_id`. A prévia usa o handoff opaco existente. Não adicionar código submetido ao evento ou a logs. Não enviar a avaliação integrada ao job de escolhas do Inngest.

## Runtime Flow

1. A leitura Learning autentica a conta e verifica titularidade, experiência e disponibilidade. Curriculum fornece o snapshot integrado. A projeção pública omite detalhes privados da rubrica. O navegador só restaura rascunho após validação online da mesma revisão.
2. O hook integrado mantém arquivos e gravações serializadas. Reutiliza IndexedDB/BroadcastChannel por meio do port existente. Gravações usam geração esperada. Notificações entre abas são avisos, não fonte de autoridade. Durante avaliação, nenhum aviso pode substituir a resposta congelada.
3. O adapter cria um único WebContainer e dois processos autorizados. Gera manifest/configuração de prática fora dos arquivos editáveis e instala apenas as dependências fixas com scripts de instalação desativados. Os comandos suportados são `npm run dev:web` e `npm run dev:api`, identificados pelos IDs curriculares. O manifest gerado os expande para Vite e Node com observação de arquivos. Nenhum texto digitado é interpolado em shell.
4. O frontend usa porta interna fixa 5173, API 3000 e prefixo `/api`. O projeto curricular de exemplo escuta a API nessa porta. A configuração Vite gerada encaminha `/api` exclusivamente a `127.0.0.1:3000` no container. Mudanças na API podem reiniciar seu estado temporário. Não há promessa de persistência dos dados de prática. O adapter associa eventos de prontidão às portas corretas, sem usar a primeira porta recebida como prévia.
5. A prévia usa HTTPS em `*.webcontainer.io` ou `*.webcontainer-api.io`, distinta da origem Shifu, com `sandbox="allow-scripts allow-same-origin"` e `referrerPolicy="no-referrer"`. A origem continua diferente da origem Shifu e é validada antes de montar o iframe. Não acrescentar navegação superior, popups, forms ou downloads. Recursos e respostas de prática aceitam somente a origem gerada confirmada, sem credenciais Shifu. A origem da prévia pode usar seu próprio armazenamento e service worker. O teardown encerra o container/processos, mas não promete apagar todo armazenamento do fornecedor. Não guardar ali dados pessoais ou credenciais da aplicação. Não relaxar CORS/COEP da aplicação Shifu para viabilizar prática. Quando o navegador não suportar o isolamento necessário, mostrar indisponibilidade da prática mantendo o restante.
6. O painel passa método/caminho/corpo ao port. O adapter executa um cliente HTTP técnico dentro do container contra a API fixa. Não aceita origem, porta ou headers de autenticação fornecidos pelo aluno. Caminhos devem começar em `/api` ou `/api/`, sem autoridade, esquema, fragmento, barra invertida, controles ou travessia normalizada/codificada. GET/HEAD não têm corpo. Redirecionamentos não são seguidos. Retornar apenas Content-Type e corpo/status, nunca Set-Cookie ou credenciais. Uma resposta antiga/cancelada não substitui o último envio.
7. Edições atualizam os arquivos em ordem. React recarrega a saída correspondente; API reinicia quando necessário. Isso não repete a última requisição do painel. Requisições que o próprio programa React faça são comportamento do projeto. Terminal exibe inicialização/saída/erros e mapeia a linha digitada por correspondência exata com um comando permitido. Pipes, redirecionamentos, substituições, argumentos extras e instalação são recusados. Reexecutar um comando de servidor substitui o processo correspondente, sem duplicá-lo.
8. A avaliação preliminar termina as gravações pendentes, captura os arquivos e congela a resposta. Learning reconstitui arquivos fixos do snapshot e valida o projeto efetivo. A IA seleciona opções da rubrica pelo port atual, sem execução de código. Inconclusão bloqueia avanço; erro técnico permite recuperação da mesma captura. A avaliação não altera contagens oficiais.
9. O envio completo valida todas as respostas e a revisão. O commit grava tentativa/snapshot/avaliação/outbox. A admissão durável e o workflow usam IDs persistidos. A avaliação oficial valida as escolhas do provedor, calcula a nota e aplica efeitos uma única vez. Recuperação usa a mesma resposta. Remoção ou encerramento impeditivo é revalidado antes dos efeitos.
10. Sair/desmontar, mudar de questão ou reiniciar descarta listeners, timers, requests e callbacks antigos. Mata ambos os processos e encerra o container. O histórico apenas renderiza os arquivos salvos.

**Limites técnicos.** Preservar a gramática de caminhos React: relativos POSIX, máximo 240 caracteres e 64 por segmento, ASCII alfanumérico/underscore/ponto/hífen, sem segmentos vazios/ocultos/dot/traversal, NUL ou barras invertidas. Política adicional é opcional, com máximo curricular de 1–32 arquivos. Configurações, manifestos, lockfiles, `node_modules` e colisões arquivo/diretório são proibidos. Sem renomear ou excluir arquivos nesta entrega.

O navegador limita fonte efetiva/rascunho a 256 KiB UTF-8 e transcript a 1 MiB. O tamanho do projeto efetivo soma bytes de caminhos e conteúdos, incluindo arquivos iniciais fixos, como faz CodeAnswerValidation. Servidor preserva `max_code_assessment_input_bytes`: padrão 256 KiB e teto configurável 4 MiB. HTTP limita corpo a 64 KiB, resposta a 1 MiB e espera a 10 segundos. Truncamento é explícito. Instalação tem prazo de 180 segundos e cada inicialização/reinício tem prazo de 30 segundos. Servidores prontos têm vida útil ligada à questão e não são mortos pelo prazo de inicialização. Esses limites são técnicos, não números pedagógicos extraídos do desenho. CPU/memória continuam a cargo do navegador. Não inventar quotas não suportadas pelo SDK.

**Ciclo de vida do rascunho.** A chave existente contém conta, Objetivo, Habilidade, Competência, Atividade, questão e revisão. Não remover nenhum componente. O ID de experiência é resolvido pelo contexto autoritativo; remoção/recriação nunca reutiliza dados invalidados. Tombstones impedem gravações atrasadas. Uma falta de conexão ou 401 comum não prova encerramento e não elimina dados por suposição. A confirmação privada de 404/remoção invalida o escopo. Um navegador desconectado não pode ser apagado remotamente; antes de restaurar ou enviar na reconexão ele deve revalidar e purgar o escopo revogado. Esta entrega não cria um coordenador geral de eliminação de contas.

# Verification Contract

## Shared setup

Autoria da Spec não executa testes, instala dependências ou semeia dados. As seleções abaixo são obrigações da implementação. Seguir a [seleção focada](../../../tooling.md#selecting-unit-and-integration-tests). Um runner principal executa as seleções integradas depois de integrar todos os escopos. Skips e seleção vazia não passam.

**Base e ferramentas.** Usar Node/Python definidos nos arquivos de runtime, pnpm na raiz e uv em `apps/server`. O lockfile da raiz resolve `@webcontainer/api 1.6.4`, xterm 6.0.0 e Vite 8.3.0. O lockfile Web legado não substitui o lockfile da workspace. Não instalar Fastify na aplicação Shifu: é dependência fixa do projeto curricular de prática.

**Automatizados Server.** Os use cases usam mocks das portas, sem testar domínio/mapper/provider diretamente. HTTP usa `tests/conftest.py`, `tests/fixtures/postgres_fixture.py` e `redis_fixture.py` com PostgreSQL pgvector 17 e Redis descartáveis. Injetar a engine correta antes de compor a aplicação; configurar Redis descartável antes do autouse de rate limiting. Não apontar fixtures ao Redis/DB compartilhado. Autenticação e assessor são controlados na fronteira de composição, sem substituir os casos de uso. Casos em classes `Test<Subject>`.

**Conteúdo reproduzível.** Criar `tests/fixtures/react_fastify_activity_fixture.py`, seguindo a composição pública de `tests/learning/rest/controllers/react_controller_fixture.py`, sem importar esse auxiliar legado no novo teste. A fixture fornece:
- Três questões, duas escolhas e a integrada; variante com integrada intermediária e variante final.
- Um React que consulta `GET /api/tasks` e conclui item por `PATCH /api/tasks/{id}`. Dados fictícios resetáveis, sem serviços externos.
- Arquivos iniciais editáveis de frontend/API, arquivo fixo, dependências React/React DOM/Vite/Fastify em versões exatas compatíveis e dois comandos autorizados.
- Rubrica com correção obrigatória, níveis/comentários predefinidos e exemplos de erro, alternativa válida e inconclusão. Critérios/pesos vêm da fixture curricular, não dos percentuais ilustrativos do frame.
- Política ausente ou diretórios `src/components` e `routes`, extensões permitidas e máximo variável.
- Conta A ativa/confirmada, conta B sem titularidade, Objetivo e experiência em aprendizado com competência liberada. Usar as relações do `build_development_seed` e os IDs do laboratório adaptativo já usados pela fixture React. IDs novos devem ser gerados/centralizados na fixture sem colidir. Verificar estado inicial e ausência de tentativa para a nova Atividade.
- Reinício de cenário limpa apenas recursos descartáveis do teste. Snapshot posterior de currículo é alteração de fixture, jamais do banco compartilhado.

**Navegador automatizado.** Reutilizar `apps/web/tests/playwright.ts` e os consumidores atuais. `authenticatedPage`/`bff` usam autenticação/transporte controlados. Esses cenários provam UI/roteamento, não autenticação ou persistência reais. A composição da rota em Vitest controla somente o SDK/transporte externo para verificar o adapter concreto. Nenhum teste dedicado de provision, IndexedDB, REST, query/action, domínio ou mapper.

**Manual real.** Criar o suporte planejado `tests/support/react_fastify_browser_runtime.py`. Entrada executável planejada, após implementada:

```bash
# apps/server
uv run python -m tests.support.react_fastify_browser_runtime
```

Esse suporte inicia PostgreSQL/Redis descartáveis conforme as fixtures, aplica Alembic head, compõe seed somente no banco que criou e acrescenta o conteúdo integrado da fixture. Usa conta ativa do seed; resolver email/senha privadamente a partir de `shared/database/seed_data.py`. O seeder atual limpa tabelas; por isso seu uso fica restrito à engine descartável criada pelo suporte. Não executar `db:seed` contra Compose.

O suporte inicia a API em loopback na porta livre 17790, um endpoint local determinístico do assessor em 18790 e expõe configuração privada em `apps/web/.playwright-cli/logs/shifu90-runtime.env`. Falhar claramente se as portas estiverem ocupadas, sem encerrar processos alheios. Configurar URL do banco/BFF/JWKS/Redis e URLs de inferência locais pela configuração existente. Aplicar as restrições de credenciais do runtime AgentOS das migrations. Não registrar conteúdo/segredos nos logs.

A aplicação executada manualmente usa o ciclo de vida real de Learning. Confirmar registro de `learning-evaluate-code-activity` e admissão em `agentos:learning` antes do envio oficial. O dobro determinístico da inferência deve responder ao protocolo real do provider de decisão com as chaves/níveis esperados e permitir selecionar conclusão, inconclusão e falha. Não substituir o workflow ou seus casos de uso. Isso prova integração, não qualidade do modelo remoto. O suporte é uma ferramenta manual de execução, não uma fixture pytest que inicia AgentOS.

A Web é iniciada em outro terminal com as variáveis privadas desse runtime e os nomes existentes em `apps/web/.env.example`:

```bash
# raiz; porta isolada para não competir com o serviço compartilhado
pnpm --filter web dev --host 127.0.0.1 --port 17090 --strictPort
```

Antes do navegador: `docker compose ps` somente para inspecionar o ambiente; checar `http://127.0.0.1:17790/health` e `http://127.0.0.1:17090/login`. O cenário deve publicar em arquivo local ignorado o caminho da Atividade, suas relações e contagens iniciais. O navegador precisa de contexto seguro, `crossOriginIsolated` e armazenamento particionado para WebContainers. Não remover o sandbox para contornar bloqueios.

Usar Playwright CLI em `apps/web` com sessão `shifu90`. Carregar o estado local somente se pertencer ao runtime correto; caso contrário entrar pelo formulário visível e salvar estado local. Capturas em `.playwright-cli/screenshots/`, snapshots em `snapshots/`, estado em `states/` e logs em `logs/`. Parar apenas browser/processos/containers do suporte e restaurar variáveis ao terminar. Cada nova execução tem banco novo. Não exige evento Inngest manual.

## Automated

### CI-01 — Contratos curriculares, validação, avaliação e recuperação

**Criteria:** CA-01/02/05/08/09/10/11/12.

**Proof:** casos consumidores existentes, ampliados para integrada. Seus mocks de repositórios/assessor exercitam snapshots, arquivos e decisões, sem testes diretos de estruturas.

```bash
# apps/server
uv run pytest tests/learning/core/use_cases/test_get_choice_activity_use_case.py tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/core/use_cases/test_submit_choice_activity_use_case.py tests/learning/core/use_cases/test_prepare_code_activity_evaluation_use_case.py tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py
```

**Inputs / pass:** integrada intermediária/final; escolhas/JS/React legados; diagnóstico recusado; versões/discriminadores inválidos; política nula/0/exatamente máximo/máximo+1; 1/32/33 no contrato da política; caminho 240/241 e segmento 64/65; travessia, NUL, duplicados, colisões, configurações e arquivos fixos adulterados; UTF-8 exatamente limite/+1 com configuração menor/padrão/maior. Notas 0/25/50/75/100 e inconclusão obrigatória/auxiliar conforme semântica atual. Falha não produz nota/efeito. Captura do assessor inclui frontend, API, arquivos fixos e adicionais, sem credenciais ou contexto extra. Replay/conflicto, respostas fora de ordem, recuperação e remoção mantêm garantias RF-09/10. Não exigir permutações arbitrárias de código; usar soluções válidas, erro de sintaxe, erro funcional, solução alternativa e resposta impossível de avaliar.

### CI-02 — HTTP, persistência, isolamento e destino assíncrono

**Criteria:** CA-01/02/08/09/10/11/12.

**Proof:** quatro módulos existentes, realocados para `tests/learning/server/controllers` e ampliados no próprio controlador. Os caminhos de destino são planejados. Preservar todos os casos anteriores, sem deixar duplicatas executáveis no local legado. TestClient entra no app real com DB/Redis descartáveis. GET/preview/submit/history permanecem os controladores atuais.

```bash
# apps/server
uv run pytest tests/learning/server/controllers/test_get_choice_activity_controller.py tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py tests/learning/server/controllers/test_submit_choice_activity_controller.py tests/learning/server/controllers/test_get_choice_attempt_controller.py
```

**Pass:** GET seguro com revisão e rubrica pública; acesso anônimo/conta B recusado sem gravações; preview não muda contagens de tentativa/avaliação/observação/outbox; shape inválido e adulteração rejeitados; envio/replay concorrente persiste uma tentativa; sessão nova relê todos os arquivos/snapshot. Observar outbox e seu destino pela composição consumidora real, sem chamar método privado do registry. Admissão não pode cair no Inngest de escolhas. Histórico permanece após alteração curricular controlada. Rejeição ou falha transacional não deixa commit parcial.

**Lifecycle:** o client compartilhado entra em `TestClient(FastAPIApp.register(...))` e o lifespan atual inicializa os registries Intelligence e Learning. O teste não chama o workflow nem envia diretamente à fila. Destino e payload são observados pela composição/outbox. A execução durável completa pertence a VM-01. A emenda de Rules autorizada pelo usuário em 2026-10-25 permite esse lifecycle e a prova do novo discriminador pelos consumidores quando workflow, port e provedor permanecem inalterados. Nenhuma mudança de lifecycle, seam de aplicação ou fixture compartilhada é necessária.

### CI-03 — Widgets, rascunho e interações dos painéis

**Criteria:** CA-02/03/04/05/06/07/08/09/13.

**Proof:** quatro testes novos, nos donos corretos. Widget usa seu hook substituído; hooks usam ports falsos e não importam adapters concretos.

```bash
# raiz
pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/react-fastify-question/tests/react-fastify-question.test.tsx src/ui/learning/widgets/pages/activity-page/react-fastify-question/tests/use-react-fastify-question.test.ts src/ui/learning/widgets/pages/activity-page/react-fastify-question/http-panel/tests/use-http-panel.test.ts src/ui/learning/widgets/pages/activity-page/react-fastify-question/terminal-panel/tests/use-terminal-panel.test.ts
```

**Pass:** composição, labels, controle único de Novo arquivo, campos HTTP aplicáveis, estados independentes, comandos reconhecidos/recusados, ausência de autoenvio HTTP, cancelamento e resultado fora de ordem. Cobrir save pendente/salvo/falhou/corrompido/quota; conta/experiência/revisão distintas; gravações concorrentes; tombstone; desconexão/reconexão; flush antes do congelamento; retorno inconclusivo/retry com mesmos bytes; desmontagem/restart sem callbacks obsoletos. Falha de prática mantém os callbacks de avaliar/enviar utilizáveis. Não criar testes artificiais para ProjectPanel/PreviewPanel puros.

### CI-04 — Composição da rota, armazenamento concreto e regressões consumidoras

**Criteria:** CA-01/03/04/05/06/07/10/12/13.

```bash
# raiz
pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts src/ui/learning/widgets/pages/activity-page/tests/use-activity-page-routing.test.ts src/ui/learning/widgets/pages/activity-page/tests/use-activity-page-route.test.ts src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx
pnpm --filter web exec playwright test tests/learning/activity-page.test.ts tests/learning/choice-result-page.test.ts
```

**Pass:** mapeamento real LearningService snake/camel, discriminator e factories corretas pela rota, IndexedDB/BroadcastChannel concretos com ambiente de navegador controlado, dois processos/portas, configuração imutável, comandos sem shell e HTTP local. Controlar SDK/respostas externas na borda. Exercitar métodos HTTP suportados, prefixo e codificações maliciosas, redirect, GET/HEAD com corpo, tamanhos 64 KiB/1 MiB exatos/+1, timeout/cancelamento, eventos tardios e dispose. Verificar sandbox/origem e ausência de credenciais. Asserções de rede pelo browser não podem substituir a comunicação real de VM-01.

Seleção afetada: Atividade recebe novo tipo e runner; feedback lê nova rubrica/arquivos; histórico lê novo discriminador. Retenção de escolhas/JS/React e diagnóstico é verificada nesses consumidores. Playwright usa saídas configuradas em `.playwright-cli/logs`. Arquivos existentes executam sem filtros inventados e não podem passar com skip/seleção vazia.

### CI-05 — Tipos dos produtores e consumidores

**Scope:** Web e Server, pois ambos ampliam os contratos. Não há pacote novo.

```bash
# raiz
pnpm --filter web check:types
# apps/server
uv run poe check:types
```

**Pass:** zero erros nos projetos configurados. Não usar tsc por arquivos fora do tsconfig.

### CI-06 — Lint e formato dos caminhos afetados

Os arquivos novos da seleção são planejados. As listas abaixo fixam os caminhos do contrato. Acrescentar helper privado somente se efetivamente criado dentro do dono e registrar a invocação final em Evaluation.

```bash
# raiz, Bash
shifu90_web_paths=(
  'apps/web/src/core/learning/choice-activity.ts'
  'apps/web/src/core/learning/react-fastify-practice-runner.ts'
  'apps/web/src/provision/learning/react-fastify-webcontainer-practice-runner.ts'
  'apps/web/src/rest/services/learning-service.ts'
  'apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/use-activity-page.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/use-react-fastify-question.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/project-panel/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/preview-panel/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/http-panel/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/http-panel/use-http-panel.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/terminal-panel/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/terminal-panel/use-terminal-panel.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/tests/react-fastify-question.test.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/tests/use-react-fastify-question.test.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/http-panel/tests/use-http-panel.test.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/react-fastify-question/terminal-panel/tests/use-terminal-panel.test.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/question-feedback/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/question-feedback/use-question-feedback.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx'
  'apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page-routing.test.ts'
  'apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page-route.test.ts'
  'apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/index.tsx'
  'apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx'
  'apps/web/tests/learning/activity-page.test.ts'
  'apps/web/tests/learning/choice-result-page.test.ts'
)
pnpm exec biome check "${shifu90_web_paths[@]}"
```

```bash
# apps/server, Bash
shifu90_server_paths=(
  'src/shifu/curriculum/core/domain/entities/activity.py'
  'src/shifu/curriculum/core/domain/structures/react_fastify_http_example.py'
  'src/shifu/curriculum/core/domain/structures/react_fastify_question.py'
  'src/shifu/curriculum/core/domain/structures/activity_question.py'
  'src/shifu/curriculum/core/domain/structures/__init__.py'
  'src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py'
  'src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py'
  'src/shifu/shared/core/domain/structures/curriculum_react_fastify_http_example_snapshot.py'
  'src/shifu/shared/core/domain/structures/curriculum_react_fastify_question_snapshot.py'
  'src/shifu/shared/core/domain/structures/curriculum_learning_activity_snapshot.py'
  'src/shifu/shared/core/domain/structures/__init__.py'
  'src/shifu/learning/core/domain/structures/code_question_detail.py'
  'src/shifu/learning/core/use_cases/code_answer_validation.py'
  'src/shifu/learning/core/use_cases/get_choice_activity_use_case.py'
  'src/shifu/learning/core/use_cases/preview_activity_question_feedback_use_case.py'
  'src/shifu/learning/core/use_cases/submit_choice_activity_use_case.py'
  'src/shifu/learning/core/use_cases/prepare_code_activity_evaluation_use_case.py'
  'src/shifu/learning/core/use_cases/evaluate_choice_activity_use_case.py'
  'src/shifu/learning/core/use_cases/get_choice_attempt_use_case.py'
  'src/shifu/learning/rest/controllers/get_choice_activity_controller.py'
  'src/shifu/learning/rest/controllers/preview_activity_question_feedback_controller.py'
  'src/shifu/learning/rest/controllers/submit_choice_activity_controller.py'
  'src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py'
  'src/shifu/learning/ai/learning_workflows_registry.py'
  'tests/fixtures/react_activity_fixture.py'
  'tests/fixtures/react_fastify_activity_fixture.py'
  'tests/support/react_fastify_browser_runtime.py'
  'tests/learning/core/use_cases/test_get_choice_activity_use_case.py'
  'tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py'
  'tests/learning/core/use_cases/test_submit_choice_activity_use_case.py'
  'tests/learning/core/use_cases/test_prepare_code_activity_evaluation_use_case.py'
  'tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py'
  'tests/learning/core/use_cases/test_get_choice_attempt_use_case.py'
  'tests/learning/server/controllers/test_get_choice_activity_controller.py'
  'tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py'
  'tests/learning/server/controllers/test_submit_choice_activity_controller.py'
  'tests/learning/server/controllers/test_get_choice_attempt_controller.py'
)
uv run ruff check --no-fix "${shifu90_server_paths[@]}"
uv run ruff format --check "${shifu90_server_paths[@]}"
```

Referência: [Tooling](../../../tooling.md#scoped-type-lint-and-complexity-checks).

**Pass:** sem erros de lint/formato; registrar avisos separadamente. Não usar comandos com escrita para validar.

### CI-07 — Complexidade configurada

**Scope:** validação/projeção de questões e snapshots, lifecycle do runner, concorrência do rascunho e interações HTTP/terminal.

**Proof:** mesmas invocações de CI-06, com resultado separado. Ruff seleciona C90 e não sobrescreve `max-complexity`, portanto aplica o padrão 10 do checker. Biome configura avisos qualitativos em `noBannedTypes`, `useLiteralKeys` e `useOptionalChain`, sem limite quantitativo configurado.

**Pass:** nenhum C901 no Server; registrar e resolver ou justificar os avisos Biome do escopo. Não relaxar regras ou excluir novos caminhos para passar. Não existe medidor quantitativo/baseline dedicado nos manifests; tal medição é **not applicable** a esta entrega, não uma medição aprovada. Se virar obrigação explícita, permanece **Blocked** até haver ferramenta/contrato reconciliado.

### CI-08 — Arquitetura, integridade dos testes e distribuição

A manutenção autorizada nesta worktree reconcilia Core com a exceção de conformidade já existente em UseCaseTesting e define os limites públicos de preparação e integração NLP. O contrato de segurança do cliente BFF cobre apenas opções internas inalcançáveis pelo navegador. Telemetria acessível e serviços Web passam pelos controllers/jobs e páginas consumidores reais. Não remover cenários nem introduzir exceções por arquivo para ocultar falhas sem autoridade semântica. Evaluation lista origem, destino e afirmações preservadas de cada um dos14 caminhos.

Executar as seleções afetadas de controllers, use cases, preparação/capacidade, dois jobs reais e páginas Web, registradas exatamente em Evaluation após integração. A manutenção não altera produto, modelos de avaliação, proteção de branch ou dependências entre módulos.

```bash
# raiz
pnpm check:test-integrity
pnpm --filter web check:architecture
pnpm --filter web build
# apps/server
uv run poe check:architecture
uv run poe build
```

**Pass:** gates aplicáveis passam; sem dependências entre módulos de negócio, testes proibidos, export ausente ou contrato de distribuição quebrado. Executar os gates de lint de projeto exigidos pelo Tooling ao integrar, mantendo CI-06 como feedback focado. CI externo continua com suas seleções configuradas; esta Spec não altera proteção de branch ou qualidade remota. Não executar suites locais completas por padrão.

### CI-09 — Preservação dos testes herdados e limites reconciliados

**Scope:** manutenção sem mudança de produto autorizada na mesma worktree. O antigo conjunto de14 violações é evidência de baseline, não autorização para eliminar afirmações.

**Contratos preservados e destinos:**

- Curriculum: `tests/curriculum/core/domain/test_react_question.py` mantém fábricas, caminhos e imutabilidade sem usecase proprietário. O cenário de seed passa aos consumidores `tests/learning/server/controllers/test_search_skill_catalog_controller.py` e `test_start_skill_controller.py`, com catálogo completo, elegibilidade, ausência de conteúdo nos nós apenas de grafo, unicidade e referências válidas no banco descartável.
- Intelligence: invariantes de construtores sem consumidor público podem permanecer em `tests/intelligence/core/domain/test_planning_domain.py` e `test_planning_session_domain.py`. Transições de sessão pertencem aos testes dos use cases Start/Answer/Restart/Retry/Prepare/Complete/ReportProgress existentes ou criados conforme seus módulos públicos. Classificação e recuperação unitárias permanecem nos dois arquivos usecase proprietários, sem infraestrutura.
- Preparação: `tests/intelligence/preparation/test_prepare_planning_indexes.py` exerce entrada pública/CLI, corpus inválido, artefatos reproduzíveis, versões imutáveis, ativação/reativação, elegibilidade antes do limite, rejeição sem escrita e consulta com persistência real. Não criar teste por repositório.
- Capacidade NLP: `tests/intelligence/capabilities/test_planning_capabilities.py` entra pelos use cases públicos com adaptadores locais reais, PostgreSQL e transporte externo controlado. Preservar lexical/semântico, ranking RRF, contexto, elegibilidade, confiança, negação, múltiplas intenções, review, retentativas e falhas tipadas. Não substituir portas por resultado aprovado para alegar prova de adaptadores.
- Registry: indisponibilidade é observada em `tests/intelligence/server/controllers/test_start_planning_controller.py` e/ou `test_get_planning_session_controller.py` pela aplicação registrada. A composição defensiva de catálogo ausente pode ser preservada como um caso rotulado no controller proprietário: construir o registry público sem iniciar worker, consumir seu port público e afirmar erro tipado, fechando recursos. Não alegar que admissão/leitura HTTP executa retrieval. Sem classe privada ou fixture dedicada de registry.
- Telemetria HTTP: consumidores `tests/learning/server/controllers/test_remove_goal_controller.py`, `tests/shared/server/controllers/test_check_health_controller.py` e handler `tests/shared/rest/handlers/test_app_error_handler.py` preservam correlação, formato, status, sanitização/limites, falha do coletor, template de rota e lifecycle. Aplicação registrada e infraestrutura descartável. Apenas estados internos malformados inalcançáveis por HTTP usam conformidade explicitamente separada dentro do handler.
- Telemetria durável: `tests/messaging/inngest/jobs/identity/test_log_main_page_entered_job.py` e `communication/test_deliver_communication_job.py` preservam início, conclusão, falha e retentativa pelo Inngest descartável real.
- Web: cinco operações Gamification são verificadas em `tests/gamification/gamification-layout.test.ts` e `tests/learning/choice-result-page.test.ts` pelo consumidor real de recompensa no resultado, com composição real e endpoint controlado, sem interceptar serverFn como prova de transporte. Transporte público de autenticação/streaming usa seus arquivos API existentes. O contrato de opções internas BFF fica em `src/rest/security/tests/server-request-origin-contract.test.ts`, sem generalizar a exceção aos serviços.

**Proof:** executar `uv run pytest <arquivos afetados>` em apps/server, separando unitários, controllers e preparação/capacidade. Os dois jobs exigem `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest <dois arquivos de jobs>` para executar o runtime real em vez de skip. Executar `pnpm --filter web test:unit <arquivo de contrato>` na raiz e `pnpm exec playwright test <arquivos consumidores afetados>` em apps/web. Manifests/configurações atuais determinam o ambiente; Docker e endpoints externos são descartáveis/controlados. Evaluation registra seleções concretas, contagens reais e o mapa completo origem→destino/afirmações. Nenhum skip ou seleção vazia é aprovação.

Três guardas defensivas de construtor público ficam explicitamente rotuladas dentro desses mesmos módulos de preparação/capacidade: tokens de negação ausentes, catálogo lexical vazio/duplicado e thresholds fora do conjunto calibrado. São conformidade de composição inalcançável por entrada validada, não prova de travessia do usecase/CLI ou de qualidade NLP. Não permitem outros testes diretos de métodos de providers.

**Passing condition:** todas as afirmações preservadas em limites honestos e aprovadas; zero violações em `pnpm check:test-integrity`; tipos/lint/complexidade/arquitetura/build dos caminhos consumidores aprovados. As seleções permanentes de Poe/CI incluem a conformidade de domínio, o handler e os dois limites Planning. Validar a paridade dos seletores sem executar suites locais completas. Validar também que o verificador aceita os novos limites documentados e continua recusando testes diretos de providers, serviços e diretórios vizinhos não autorizados.

## Manual

### VM-01 — Projeto integrado, avaliação e resultado persistido

**Type:** Manual. **Criteria:** CA-02/03/04/08/10/11/12/13.

**Setup/tool:** suporte descartável e Playwright CLI de Shared setup. Desktop 1440×900.

1. Entrar pelo formulário real, abrir o caminho publicado da Atividade e avançar até a questão integrada. Confirmar rubrica pública e estado de salvamento.
2. Abrir Arquivos, criar um arquivo autorizado pelo único controle do explorador, editar frontend e API. Verificar a prévia real, uma mudança visível específica e a comunicação React→Fastify por efeito observável na tarefa.
3. No painel HTTP enviar GET e PATCH com corpo aplicável, comparar status/corpo com o estado da prévia. Editar código e comprovar que a última requisição do painel não foi reenviada. No terminal executar um comando permitido e observar a saída do processo.
4. Avaliar preliminarmente. Confirmar arquivos adicionais e rubrica somente leitura. Observar contagens oficiais inalteradas em sessão de inspeção do banco descartável. Avançar e enviar a Atividade completa com a chave estável.
5. Confirmar admissão Learning registrada e execução do workflow real. Sair e retornar. Verificar a URL de tentativa, nota completa, rubrica e arquivos preservados via GET e sessão nova do banco. Comprovar uma tentativa e aplicação única dos efeitos. Recuperação/falhas sistemáticas são de CI-01/02.
6. Capturar os estados do handoff. Registrar requests relevantes, console e erros esperados classificados. Navegar pelos controles essenciais com teclado e conferir foco. Encerrar os recursos próprios no fim.

**Pass:** resultado persistido com frontend/API/adicionais corretos, runtime real comunica sem credenciais Shifu e sem erro de console não explicado. SDK pronto sem conteúdo renderizado não prova prévia. Modelo determinístico não prova qualidade de inferência remota.

### VM-02 — Retomada local, abas e uso mobile

**Type:** Manual. **Criteria:** CA-06/07/13.

**Setup/tool:** mesmo runtime/conta, Playwright CLI, 390×844; usar nova Atividade sem tentativa para esta jornada.

Editar dois arquivos e aguardar confirmação local. Fazer logout/login pelo formulário e verificar restauração. Abrir a mesma questão em segunda aba; gravar alteração distinta e verificar que a última gravação aparece na outra. Confirmar campos HTTP/terminal/editor acessíveis pelas abas, teclado utilizável e nenhum overflow da página. Capturar o estado mobile com foco e retornar sem envio oficial. As matrizes negativas/remoção são automatizadas.

**Pass:** arquivos corretos após autenticação real, duas abas convergem e os controles ficam alcançáveis no mobile. Sessão e recursos pessoais descartáveis são encerrados conforme Shared setup.

## Visual

### VM-03 — Estação integrada desktop

**Type:** Visual. **Criteria:** CA-02/08/13. **Reference:** `design/handoff.md`, V-01/V-02/V-03.

Inspecionar capturas atuais de VM-01 a 1440×900: Enunciado com rubrica, Arquivos com frontend/API/adicional e as abas Prévia/HTTP/Terminal. Comparar hierarquia, largura dos painéis, tokens, tipografia, densidade, foco e controle único Novo arquivo.

**Pass:** referências preservadas com as adaptações explícitas do handoff. Uma imagem salva sem inspeção não passa.

### VM-04 — Composição mobile e resposta somente leitura

**Type:** Visual. **Criteria:** CA-08/12/13. **Reference:** handoff V-04/V-05.

Inspecionar capturas de VM-01/02 em 390×844 do editor/painéis e resultado. Mobile é adaptação aprovada das regras, não frame mobile existente. Retorno preliminar/oficial reutiliza a composição atual do código com todos os arquivos integrados.

**Pass:** sem corte de texto/ações, página sem overflow horizontal, abas e foco visíveis; modo somente leitura inequívoco. Dados e nota são provados por CI/VM Manual, não por screenshot.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Shifu — PRD — Learning](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881), conteúdo `83066881`, **v26**, atualizado 2026-10-05T02:11:45.152Z, leitura completa em 2026-10-25, identidade/versão reconfirmadas em 2026-10-25T21:37:01Z | RP-09/11/12/13/14/18/24/25/29; JN-07/08/11/13 | Confirmar identidade/versão antes de concluir. Pai `PRD's`, `82804737`, ancestral Shifu `82509992` | Leitura completa via Atlassian Shifu MCP; sem escrita ou mudança de checkboxes |
| [Shifu — PRD — Curriculum](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113), conteúdo `83034113`, **v13**, atualizado 2026-10-04T23:01:19.677Z, leitura completa em 2026-10-25, identidade/versão reconfirmadas em 2026-10-25T21:37:01Z | RP-03/JN-03 e limites de conteúdo fictício de RP-07 | Mesma confirmação de versão/pai acima | Leitura completa; sem alteração de produto |
| [SHIFU-90](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-90), ID `12600`, atualizado 2026-10-24T03:18:05.390Z, pai SHIFU-10 | Recorte de entrega e decisão única Novo arquivo | Ticket cita Learning v24/Curriculum v12; reconciliado com páginas atuais sem divergência no formato integrado | Nenhuma escrita Jira autorizada |
| [SDD](../../../sdd.md), [Modules](../../../modules.md), [Architecture](../../../architecture.md), [Tooling](../../../tooling.md), [Rules router](../../../rules.md) | Estrutura, donos, runtime e verificação | Preservar autoridades; não copiar planos ou PRD para Git | Sem atualização estrutural; emendas de AI/Jobs e reconciliação local de testes/seletores Q6 autorizadas pelo usuário em 2026-10-25 |
| Rule Pack Server: [Python](../../../rules/python-conventions-rules.md), [Core](../../../rules/core-layer-rules.md), [Use cases](../../../rules/use-case-testing-rules.md), [REST](../../../rules/rest-layer-rules.md), [Controllers](../../../rules/controllers-testing-rules.md), [Database](../../../rules/database-layer-rules.md), [Provision](../../../rules/provision-layer-rules.md), [AI](../../../rules/ai-layer-rules.md), [Messaging](../../../rules/messaging-layer-rules.md), [Jobs](../../../rules/jobs-testing-rules.md), [Server app](../../../rules/server-app-layer-rules.md) | Todos os limites Server da árvore e suporte descartável | Conferir exports, snapshots neutros, transaction owner, wiring e testes consumidores | Revisões independentes concluídas em Evaluation |
| Rule Pack Web: [TypeScript](../../../rules/typescript-conventions-rules.md), [UI](../../../rules/ui-layer-rules.md), [Routing](../../../rules/web-app-routing-rules.md), [Widget testing](../../../rules/widget-testing-rules.md), REST e Provision acima, [Design](../../../design.md) | UI/hooks, ports/adapters, rota, tokens, testes e acessibilidade | Nenhuma query/action suite ou teste direto de provider. Route tree gerada não muda | Review independente obrigatório |
| Design `design/shifu.pen`, frames `pcDeY`/`tDF6r`/`xeppf` | Aparência desktop e critérios públicos | Referências exportadas/inspecionadas em handoff. Retirar duplicação visual de Novo arquivo conforme ticket | Mobile por adaptação explicitamente aprovada no desenho |
| React existente: [spec](../react-code-question/spec.md), [evaluation](../react-code-question/evaluation.md) | Evidência histórica de contratos/limitações da base | Reutilizar padrões, não copiar árvore desatualizada ou declarar evidência antiga atual | Spec React ainda draft e possui trechos legados sobre Inngest; runtime verificado no source prevalece como fato implementado, Rules como intenção |

**Emenda de autoridade autorizada e aplicada.** Em 2026-10-25, o usuário aprovou corrigir as duas regras de verificação. A seção de testes de AI Layer agora permite verificar um novo formato curricular por consumidores de use case e HTTP quando workflow, port de avaliação e provedor permanecem inalterados. A jornada manual mantém a prova de execução registrada. Job Testing agora permite o início de registries pelo lifespan normal do TestClient compartilhado e continua proibindo fixtures dedicadas e testes que enviem diretamente à fila para verificar workflow.

A exceção da revisão 2 é limitada a esse reaproveitamento. Não autoriza novos testes diretos de providers, outro avaliador ou alteração pedagógica. Mudanças no próprio workflow continuam no limite em processo de Job Testing. As demais capacidades de IA permanecem sob suas autoridades existentes. A emenda local não altera PRD, aplicação, fixtures ou serviços.

Na revisão2 foram modificados AI Layer e Job Testing. A revisão3 também reconcilia Core, Use Case Testing, Database, Provision, Controller Testing e Widget Testing, além de Tooling e seletores permanentes Poe/CI. Todas as alterações estão limitadas à manutenção autorizada e preservam a execução dos cenários. CI-02 descreve o lifecycle real e cobre apenas os efeitos observáveis de HTTP/persistência/destino. VM-01 verifica o percurso registrado real. O Spec Reviewer releu o diff das duas regras e o contrato afetado na revisão 2. Confirmou a resolução dos dois achados anteriores e não identificou bloqueios de compatibilidade. As conclusões anteriores não afetadas permanecem válidas. Não há evidência de implementação ou sucesso de runtime nesta autoria.

Os quatro módulos HTTP afetados saem de `tests/learning/rest/controllers` e passam ao destino espelhado permitido `tests/learning/server/controllers`. O auxiliar React também é realocado e seus quatro imports são atualizados. A revisão 3 inclui a manutenção dos14 caminhos preexistentes apontados por CI-08, autorizada pelo usuário na mesma worktree. O inventário e as substituições preservadas ficam em Evaluation. Sem mudança de comportamento de produto nos módulos consumidores. Não criar outro módulo por formato para o mesmo controlador. O teste legado do hook React importa provision concreto e usa extensão inconsistente; novos testes seguem o limite do dono e `.test.ts` para hooks. Validation Package contém exemplos `@scoops/*` sem pacote correspondente nesta base. Nenhum pacote/schema reutilizável novo é necessário, portanto essa regra não é ativada artificialmente.

**Pesquisa e decisões.** Worktree separada `codex/shifu-90-spec` em `/home/petros/.codex/worktrees/shifu-90-spec/shifu`, criada de `8ee992a7` sem copiar mudanças locais. `.codegraph/` está ausente nesta worktree; inspeção local foi usada sem criar/reconstruir índice. O índice da checkout original não foi usado para inferir source desta worktree. Pesquisas Server/Web foram independentes e somente leitura. Context7 consultou `/stackblitz/webcontainer-docs` sobre spawn, eventos por porta e descarte e `/vitejs/vite/v8.0.0` sobre proxy/CORS. A revisão 2 falhou em VM-01 por service worker indisponível em origem opaca. O usuário autorizou Q5=A: origem própria validada com allow-same-origin. A revisão 3 deve provar a renderização e React→API e repetir os checks de destino, permissões, credenciais e descarte. Documentação não é prova de runtime.

O usuário aprovou o recorte integrado e o desenho de dois processos internos, armazenamento reutilizado, endpoints atuais e verificação focada. Depois autorizou Q5=A e determinou resolver as14 falhas preexistentes nesta mesma worktree. Essa autorização inclui a emenda de isolamento e manutenção local necessária, preservando cenários e sem escritas externas. Também autorizou a emenda local de AI/Jobs descrita acima. A revisão escrita 2 foi aprovada explicitamente pelo usuário em 2026-10-25. A revisão 3 registra exatamente as decisões Q5=A e Q6 na mesma worktree autorizadas na resposta anotada, mantendo a autorização de implementação. O Spec Reviewer auditou a emenda e confirmou PASS após corrigir nomes de testes e a seleção real dos jobs. A revisão 3 foi declarada ready para continuar e posteriormente implementada/verificada, conforme Evaluation. A implementação foi posteriormente autorizada pela invocação implement-spec. Evaluation preserva resultados atuais, falhas e provas invalidadas pela revisão 3.

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-25 | Contrato inicial integrado com dois processos, arquivos/rubrica únicos, rascunho local e verificação por consumidores | SHIFU-90, Learning v26, Curriculum v13 e desenho recomendado aprovado pelo usuário |
| 2 | 2026-10-25 | Reconciliar o contrato de verificação com a emenda autorizada de AI/Jobs; declarar o início real dos registries em CI-02 | Emenda autorizada pelo usuário; achados de compatibilidade sobre prova assíncrona e lifecycle do TestClient |
| 3 | 2026-10-25 | Permitir origem própria validada da prévia com allow-same-origin e incluir correção preservadora das14 falhas de integridade na mesma worktree | Q5=A e instrução explícita do usuário para Q6; achados ACH-04/09 de runtime e baseline |

Sincronização da entrega com main0f1ee09a em2026-10-25: preservados perfil/segurança/autenticação de SHIFU-97 e a união dos cenários de manutenção. O usuário confirmou mínimoRecall89%, já aprovado no commitba45dc9c de main e aplicado somente ao gate existente de recuperação. O contrato RF/CA desta questão integrada permanece na revisão3. Evaluation preserva a falha histórica sob90%, a aceitação de89% e a verificação do candidato integrado.

Conclusão: revisão3 comprovada após main0f1ee09a e candidato4bea0918. CI23/23Passed e nenhuma conversa bloqueante no PR45. Estado final e provas em evaluation.md. Esta atualização não altera o contrato.
