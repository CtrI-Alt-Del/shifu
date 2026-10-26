---
description: Module-owned Agno workflows and typed AI decision providers, including model resolution, structured output, and module boundaries.
---

# AI Layer Rules

These rules apply to AI orchestration under active business-module AI packages
(`apps/server/src/shifu/intelligence/ai` and
`apps/server/src/shifu/learning/ai`), typed decision adapters under
`apps/server/src/shifu/intelligence/providers`, and shared model infrastructure
used by those modules.

## The originating module owns its AI orchestration

AI is a technical layer inside its business module, not a separate business module.
Intelligence owns Mentor and Goal Planner agents, tools, output schemas, prompts, and
workflows. Learning owns its official code-evaluation workflow and must not import
Intelligence implementation classes; it receives provider-neutral Shared ports from
application composition.

```text
apps/server/src/shifu/intelligence/ai/
├── agno/
│   ├── agents/                one base agent plus one class per responsibility
│   ├── outputs/
│   ├── tools/                 only when model-directed tools are required
│   └── workflows/
└── data/                      capability-owned curated corpora/manifests
```

Do not introduce `classical` or `generative` directory levels in new AI code.
Technology-specific NLP adapters belong under Intelligence `providers`, for example:

```text
intelligence/providers/
├── text_preprocessing/spacy/
├── retrieval/bm25/
├── intent_classification/embeddings/
├── embeddings/sentence_transformers/
└── mentor_review_provider/openrouter/
```

Each adapter implements a narrow Core port and translates technology-specific behavior.
Routing and application policy remain owned by Core, even when a routing provider
supplies a typed decision. Existing implementations in the previous layout remain
compatible; migrating them is a separately scoped refactor, not an incidental change.
Tools are optional: prepared authorized context may be sufficient for an agent.
Introduce tools only for an approved capability needing model-directed operations.

Shared model transport settings and credential handling belong to the owning
module's base agent and model resolver inside its AI package, not to a provider. Feature prompts and capability-specific orchestration
remain in the owning module and must not move into `shared`.

Other modules consume their own Core contracts, a genuinely shared technical port, or
a documented event. They must not import another module's concrete Agno agents, tools,
workflows, prompts, provider implementations, or output models.

The Agno-specific rules below apply to workflows that use Agno. A bounded,
single-step decision model may instead be exposed through an Intelligence-owned
provider implementing a Shared core contract over immutable, module-neutral
assessment input. In particular, Jev code-rubric assessment uses OpenRouter's Decisions
API through a server-owned HTTP client with Pydantic transport models and does
not require an Agno `Agent` or `Workflow`.
It must still obey the provider, source-context, output-validation, lifecycle,
privacy, and testing boundaries in this Rule Pack.

### Typed decision providers

Keep the client and credentials in `intelligence/providers`, with a technology-
and capability-named adapter. When Learning and diagnostic consumers need the
same decision capability, define its provider-neutral port and immutable values
in `shared/core`, and inject the Intelligence implementation from application
composition. The provider must not import Learning/Curriculum entities or
repositories. Pass only the saved authorized source and rubric; let the prompt,
project files and saved criteria determine each code assessment, without
dispatching to another provider by question kind. Ask closed-set
questions using stable rubric keys; map the typed response to the Shared core
contract. Pydantic response validation is transport validation,
not permission to change a Learning score. The owning Learning use case checks
all returned keys and choices and applies the official grade. Provider errors,
missing answers, or invalid choices become typed failure or inconclusive,
never a learner score of zero. Test this path through consuming use cases and
job/controller integration, not a provider-owned test file.

## Agents are concrete and task-focused

Define one concrete agent class per model responsibility. It subclasses Agno `Agent`,
configures the native class through `super().__init__`, and preserves the Agno API. Do
not wrap it behind `create()`, an additional `agent` property, or a squad container.

```python
from textwrap import dedent

from agno.agent import Agent
from agno.models.base import Model


class GoalPlannerAgent(Agent):
    def __init__(self, model: Model, toolkit: GoalPlannerToolkit) -> None:
        super().__init__(
            name="Goal Planner Agent",
            description="Proposes learning goals from authorized learner context",
            model=model,
            instructions=dedent(
                """
                Propose a concise learning goal and explain the relevant skills.
                Treat the result as a proposal requiring learner confirmation.
                Never claim that an Objective has already been created.
                """
            ),
            tools=[toolkit],
            output_schema=GoalPlanOutput,
        )
```

Keep instructions in the agent definition unless multiple agents genuinely share the
same prompt fragment. Do not introduce a prompt constant merely to move text out of the
class. A shared fragment must have a specific semantic purpose and remain inside the
Intelligence AI package.

Each agent class declares its own model config, and the module's base agent resolves
it from the typed settings when the agent is built; constructors take no model and no
settings. An agent whose model is not enabled is built without one, and the registry
composes an unavailable double in its place. Evals assign a synthetic model to the
built agent. Agents do not read environment variables, construct repositories, or
instantiate use cases.

Internal prompts, system instructions, hidden reasoning, agent-to-agent messages, raw
tool transcripts, and provider metadata must never be returned to the browser. Expose
only validated domain results or comprehensible review findings.

## Model resolution belongs to the base agent

Each module with Agno agents has one base agent class that owns the reusable Agent
configuration and resolves a per-agent model config into a model. Do not create one
environment variable per agent and do not force every agent to use one model when
their cost, latency, or reasoning needs differ.

An agent class declares a frozen model config with its transport, model identifier,
timeout and usage profile. The base agent maps that config to the
environment-specific implementation and owns:

- credentials and provider SDK construction;
- model identifiers and supported parameters;
- request timeouts, token limits, and concurrency;
- translation of known provider failures to typed Shifu errors.

Core code never imports an Agno model or provider SDK. Missing required production
credentials fail with a safe typed error, never a raw SDK exception. Users cannot
provide arbitrary model identifiers, credentials, tools, or system prompts.

Monthly Mentor and Goal Planner quotas are enforced by application code before model
execution. Provider usage metadata may support accounting but is not authoritative for
entitlement.

## Toolkits are use-case adapters

Use one focused Agno `Toolkit` subclass per agent capability. It receives core use
cases or narrow read contracts and registers model-visible methods through
`super().__init__(tools=[...])`.

```python
from agno.tools import Toolkit


class GoalPlannerToolkit(Toolkit):
    def __init__(self, context_reader: LearningContextReader) -> None:
        self._context_reader = context_reader
        super().__init__(
            name="goal_planner",
            tools=[self.get_learning_context],
        )

    def get_learning_context(self, learner_id: str) -> LearningContext:
        """
        Get authorized learning context for one learner.

        Args:
            learner_id: Trusted identifier for the learner being assisted.

        Returns:
            The minimum learning context authorized for goal planning.
        """
        return self._context_reader.read(learner_id)
```

Keep input and output models in the tool module when only that tool uses them. Move a
model to `outputs` when a workflow, agent, job, or several tools share the same shape.

Toolkit methods perform boundary validation, invoke injected application operations,
and map their results. Business rules remain in use cases. Each method has a precise
docstring with `Args` and `Returns` because Agno exposes that description to the model.
Do not add agent squads, generic tool handlers, or proxy layers around a toolkit.

Tools must not:

- access SQLAlchemy sessions or ORM models directly;
- import another module's private repository or adapter;
- read environment variables or provider credentials;
- bypass authorization or trust a browser-provided identity;
- expose unrestricted HTTP, filesystem, shell, database, or code execution;
- persist a model proposal as official state;
- orchestrate a workflow or implement retry policy.

State-changing tools require explicit workflow intent, use-case authorization, and an
idempotency strategy. Prefer read-only tools during model exploration.

## Workflows contain composition, not business logic

Define one concrete workflow class per core workflow capability. It subclasses Agno
`Workflow`, receives native `Agent`, `Team`, `Toolkit`, or `Step` dependencies, and
configures its stable composition through `super().__init__` in the constructor.
Avoid a generic `create_workflow()` helper that hides the composition. If Agno requires
run-specific state at construction time, keep a clearly named private builder limited
to binding that state; the step graph remains visible in the workflow class.

Workflow code may define steps, maps between structured outputs, branches, parallel
work, and bounded review loops. Parsing domain state, authorization, outcome resolution,
persistence, progress transitions, rewards, and quota decisions belong to tools and
core use cases.

Do not recreate tool behavior in anonymous inline steps. A deterministic step with
reusable application meaning should be a core operation exposed through a tool. A
purely mechanical map between workflow schemas may remain in the workflow.

Use the smallest Agno primitive that represents the flow:

- one `Agent` for one bounded model responsibility;
- a `Team` only when agents genuinely collaborate or delegate;
- a `Workflow` for explicit sequencing, branching, parallel execution, or review loops;
- ordinary Python for deterministic work that does not need a model.

Loops have an explicit maximum and terminal condition. Parallel steps must be
independent and define their merge behavior. Let workflow and agent failures propagate
to the controller or owning AgentOS boundary so the owning module can map or retry
them. Do not catch and rethrow without adding a meaningful recovery or error translation.

### Example: single-agent workflow

Use a small `Workflow` specialization when one agent is sufficient. It converts the
Agno result to a core output and does not expose Agno run types:

```python
from agno.workflow.workflow import Workflow


class AgnoPlanLearningGoalWorkflow(Workflow):
    def __init__(self, agent: GoalPlannerAgent) -> None:
        super().__init__(name="plan-learning-goal", steps=[agent])

    def run(self, request: GoalPlanningRequest) -> GoalPlan:
        response = super().run(input=request.model_dump_json())
        output = GoalPlanOutput.model_validate(response.content)
        return GoalPlan.from_output(output)
```

Converting `GoalPlanOutput` to `GoalPlan` is boundary mapping. Checking that requested
skills exist and may be attached to an Objective remains a Learning use-case rule.

### Example: writer-reviewer workflow

Use Agno `Workflow` when the capability requires explicit orchestration:

```python
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow


class AgnoAnswerMentorMessageWorkflow(Workflow):
    def __init__(self, writer: MentorWriterAgent, reviewer: MentorReviewerAgent) -> None:
        super().__init__(
            name="answer-mentor-message",
            steps=[
                Step(name="draft-answer", agent=writer),
                Step(name="review-answer", agent=reviewer),
            ],
        )

    def run(self, request: MentorMessageRequest) -> MentorAnswer:
        response = super().run(input=request.model_dump_json())
        reviewed = ReviewedMentorAnswer.model_validate(response.content)
        return MentorAnswer.from_reviewed_output(reviewed)
```

If revision is required, add an explicit loop with a documented maximum. The reviewer
does not authorize access, determine Learning state, or persist the answer.

## Workflow contracts are exported through core interfaces

Every AI workflow consumed outside its AI package implements a `Protocol` under its
owning module's `core/interfaces`. Its inputs and outputs are domain primitives,
structures, or DTOs; Agno-specific schemas remain internal when callers do not need
them.

```python
from typing import Protocol


class PlanLearningGoalWorkflow(Protocol):
    def run(self, request: GoalPlanningRequest) -> GoalPlan: ...
```

Dependency pipes or the owning module's workflow registry construct the concrete
workflow and expose the module's core protocol to consumers. Controllers inject the
protocol and do not import the Agno implementation. Registered durable workflows run
through the owning module's native AgentOS queue; tests must enter through that module
boundary rather than compose a workflow in an Inngest job.

```text
<module>/core/interfaces/                 public workflow contracts
<module>/ai/agno/                          private implementations
intelligence/ai/intelligence_workflows_registry.py  Intelligence runtime composition
learning/ai/learning_workflows_registry.py          Learning runtime composition
<module>/pipes/                            FastAPI dependency composition
<module>/rest/controllers/                 protocol consumers
<module>/messaging/jobs/                   non-AI durable consumers
```

Agents and tools remain internal implementation details unless an explicitly documented
module contract requires otherwise.

### Example: FastAPI composition pipe

The pipe is the only request-side code that sees all concrete AI dependencies:

```python
from typing import Annotated

from agno.models.base import Model
from fastapi import Depends


class IntelligencePipe:
    @staticmethod
    def get_plan_learning_goal_workflow(
        context_reader: Annotated[
            LearningContextReader,
            Depends(LearningPipe.get_context_reader),
        ],
        model: Annotated[Model, Depends(ModelPipe.get_goal_planner_model)],
    ) -> PlanLearningGoalWorkflow:
        toolkit = GoalPlannerToolkit(context_reader)
        agent = GoalPlannerAgent(model, toolkit)
        return AgnoPlanLearningGoalWorkflow(agent)
```

A controller injects `PlanLearningGoalWorkflow` from this pipe and invokes the core use
case. It does not assemble the tool, agent, or model itself.

## Source context comes from the originating module

An AI workflow must not access another business module's private repositories to build
prompt context. The originating module authenticates access, loads its own state, and
passes the minimum immutable normalized snapshot through a contract or domain event.

Do not trust browser-provided progress, Curriculum answers, grades, XP, permissions,
account state, or official answers. Reprocessing uses the persisted or requested source
snapshot rather than silently incorporating later source changes unless the product
contract explicitly requires fresh context.

Mentor obeys the Learning state supplied through the authorized contract: no prohibited
help during a diagnostic, progressively specific hints during learning, and a complete
reference solution only after Learning confirms that completion rules allow it.

Goal Planner output is a proposal. Only explicit learner confirmation followed by
Learning validation may create an Objective. AI never directly changes official
attempts, progress, mastery, Objectives, XP, streaks, achievements, account state, or
Curriculum content.

## AI output is structured and reviewed

Use Pydantic structured output for every model result consumed by application code.
Configure the Agno output schema instead of parsing free-form model text as the primary
success path. The schema constrains types, required fields, lengths, and bounded values;
the owning use case validates domain meaning and authority.
For the typed Jev provider, OpenRouter supplies structured Choice answers;
the adapter checks the complete expected key set and allowed option IDs before
returning its typed core DTO. No free-form text parser or Agno output schema is
needed on that path.

Use a reviewer loop when a capability has material quality, safety, or correctness
criteria that can be evaluated before delivery. The feature workflow owns the bounded
review cycle. Review findings crossing the AI boundary use domain categories and plain,
comprehensible language—not hidden reasoning or internal instructions.

### Example: constrained output schema

```python
from pydantic import BaseModel, Field


class SkillRationaleOutput(BaseModel):
    skill_id: str
    rationale: str = Field(min_length=1, max_length=500)


class GoalPlanOutput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1_000)
    skills: list[SkillRationaleOutput] = Field(min_length=1, max_length=10)
```

This schema constrains generated shape and size. It does not prove that a `skill_id`
exists, that the learner may use it, or that an Objective may be created. Those domain
validations happen after the workflow returns.

Reject malformed or semantically invalid output with a typed error. Streaming endpoints
emit stable user-facing Shifu events and never raw Agno or provider events.

## FastAPI, AgentOS, and Inngest own distinct execution lifecycles

FastAPI owns request and SSE transport. When an AI result must return in the same
request, the consumer adapter may invoke the registered operation through its owning
module's internal AgentOS client. Private input/results travel through a trusted,
single-use in-memory handoff; native run records contain only its opaque reference and
safe status. Disconnects and cancellation should stop unnecessary model work when safe.

The owning module's native AgentOS runtime owns durable AI workflow admission, runs,
queues, and shutdown. Intelligence and Learning each construct only their own module
registry, AgentOS, app/client, and workflow set. Shared may supply module-neutral queue
transport, destination-aware outbox admission, and sanitized observability, but never a
global workflow catalogue or business registration. Inngest remains responsible for
durable non-AI work. Queued tickets use stable source identifiers; they do not depend
on transient handoffs for restart recovery. Events and tickets carry stable identifiers
or opaque one-shot references, and effects use idempotency fences. A workflow does not
implement its own scheduler, background task runner, or durable retry loop.

## Privacy and observability

Record workflow identity, run identity, model profile, duration, token usage, tool name,
outcome category, and typed failure class when operationally useful. Correlate FastAPI,
AgentOS, Inngest, and provider runs without placing prompt content in correlation
metadata.

Do not log or persist credentials, tokens, full prompts, hidden answers, chain-of-thought,
private tool arguments, unrelated learner context, or unrestricted model responses.
Evaluation datasets and traces follow the source data's access, retention, and deletion
requirements.

## NLP and semantic indexes remain reproducible

Text preprocessing, embeddings, lexical/semantic retrieval, and intent classifiers
are technology-named providers implementing typed Core contracts. This applies to
spaCy, Sentence Transformers, BM25, TF-IDF and scikit-learn; no particular library
is mandatory for every capability. Version the corpus, preprocessing, model revision,
dimensions, vocabulary/artifact where relevant, and calibrated thresholds needed to
reproduce results. Similarity and ranking are not authorization or calibrated
probabilities by themselves.

Embedding generation belongs to a provider. Persistent embedding records and index
version queries belong to an owning Core repository port and its database adapter;
SQL/pgvector must not move into a provider or Agno workflow. A shared index capability
may use one typed repository across indexed entity kinds when operations/lifecycle
are shared. Records reference source IDs, kinds and compatible versions; source
entities remain authoritative in their own modules. Separate repositories require
distinct persistence contracts, not merely a different source entity name. Eligibility
must be enforced before ranked result limits when the capability requires it.

Training and corpus reindexing use a dedicated background or preparation path outside
request handling. Requests may generate query embeddings and search a ready index;
they never train or rebuild the corpus synchronously. Agno consumes NLP results only
through typed contracts. An incompatible index must not silently match new source
content against stale vectors.

## Tests follow the consuming execution boundary

Use-case unit tests mock Core workflow/provider/repository protocols and verify
business decisions. Provider and persistence adapters never own dedicated test files.
Workflow orchestration uses the in-process boundary defined by Job Testing
Rules: real use cases and persistence, mocked agents, and scripted routing/context
ports. These tests do not prove the concrete local NLP adapters. Registered
admission, routing and persisted HTTP effects use the composed application
boundary; a Spec requiring real registered execution retains its explicit journey.
Non-AI asynchronous effects use registered Inngest jobs. Do not create dedicated
registry fixtures or call workflow internals to duplicate these boundaries.

Offline Planning index preparation owns
`tests/intelligence/preparation/test_prepare_planning_indexes.py`. It exercises
the public preparation entrypoint and CLI against disposable storage, including
corpus validation, reproducible artifacts, immutable versions, activation and
rejection without mutation. Runtime Planning classification/retrieval integration
owns `tests/intelligence/capabilities/test_planning_capabilities.py`. Enter through
the public consuming use cases with real local adapters and PostgreSQL; control
external inference/review at the transport boundary. These are capability tests,
not provider-specific suites or infrastructure-free unit tests. They preserve
lexical/semantic quality, ranking, eligibility, versions and typed failures that
mocked workflow ports cannot establish. Do not import private adapter helpers.
Other synchronous capabilities retain their composed controller boundary.
Existing dedicated AI/provider suites require a scoped migration preserving their
assertions, rather than deletion or relabeling as workflow proof.

For a curricular question format that reuses the existing workflow, assessment
port, and provider without changing them, verify the new normalization and
destination selection through consuming use cases and HTTP integration. For this bounded change, do not require a new workflow or runtime suite
solely for a new question discriminator. Verify the integrated path's registered execution in its manual
journey. Changes to the workflow itself remain subject to Job Testing Rules'
in-process workflow boundary.

Consumer integration tests retain the relevant matrices:

- structured input/output, malformed outputs, and allowed tools;
- step order, branches, parallel joins, and bounded review loops;
- authorized context minimization and account isolation;
- timeout, cancellation, quota, retry and typed failures;
- suppression of prompts, hidden reasoning and raw tool/provider output;
- for retrieval: paraphrases, negatives, multiple/unknown intents, eligibility,
  duplicate candidates, incompatible versions and calibrated acceptance/abstention.

Use real local NLP models/indexes and database adapters where they are under test.
Control external inference/review through endpoint doubles or emulators at the
transport boundary; do not replace the workflow with a pre-approved result and claim
its behavior was verified. Observe persisted/public effects and captured external
interactions through the consumer boundary. Real remote-model checks are opt-in,
never the only proof, and never use production data.

## Review checklist

Apply Agno-specific items only to features that use Agno; the typed Jev
decision-provider path follows the Shared core-port and Intelligence provider
rules above. The first checklist item applies to AI orchestration ownership,
not the location of a provider-neutral Shared contract.

- [ ] AI implementation and workflow registration are owned by the originating business module; Shared contains transport only.
- [ ] Each agent subclasses `Agent`, has one responsibility, and configures `super()`.
- [ ] Instructions remain with the agent unless a prompt fragment is genuinely shared.
- [ ] Each toolkit subclasses `Toolkit` and wraps narrow use cases or read contracts.
- [ ] Toolkit methods have accurate `Args` and `Returns` docstrings.
- [ ] No squad, generic tool handler, or forwarding-only wrapper was introduced.
- [ ] Each workflow subclasses `Workflow` and contains composition, not business rules.
- [ ] External consumers depend on a core `Protocol`, never a concrete Agno class.
- [ ] Model resolution and credentials remain in typed provider composition.
- [ ] Source context is authorized, immutable, normalized, and minimal.
- [ ] Machine-consumed output is structured and validated.
- [ ] Review loops and retries are bounded and owned by the correct layer.
- [ ] Agent/Workflow code imports no FastAPI, SQLAlchemy, REST controller, or messaging transport; only its owning module registry composes local dependencies and Shared runtime resources.

## Defensive registry composition contract

The owning Planning controller suite may retain one labeled conformance case
for the public registry constructor with its optional Curriculum catalog absent.
Construct the registry without starting a worker, access its public Core
`planning_skill_retrieval` port and assert the typed unavailable error. Other
ports may be autospecced. Close the registry and all resources in teardown.
This proves only unavailable composition that HTTP admission/read cannot observe;
it is neither registered workflow execution nor concrete NLP adapter coverage.
Do not import the private unavailable adapter, create a registry-owned suite or
runtime fixture, or send directly to a queue. Reachable behavior continues through
registered HTTP and the Spec's real execution journey.

## Defensive Planning configuration guards

The Planning preparation/capability boundaries may preserve three explicitly
labeled public-constructor conformance guards that validated application inputs
cannot reach: missing negation tokens, an empty/duplicate lexical catalog, and
classifier thresholds outside the closed calibrated set. Keep them within the
capability-owned integration modules, not provider-owned files. They prove only
fail-closed composition before execution, not entrypoint/use-case traversal or
NLP quality. All reachable preparation and runtime scenarios retain their public
consumer boundaries and real local adapters. Close controlled HTTP clients even
when construction raises. This is not a general exception for provider methods.
