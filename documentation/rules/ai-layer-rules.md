---
description: Feature-owned Agno agents, workflows, tools, model resolution, structured output, and AI boundaries.
---

# AI Layer Rules

These rules apply to AI orchestration owned by Intelligence under
`apps/server/src/shifu/intelligence/ai` and to shared model infrastructure used by
that module.

## Intelligence owns its AI orchestration

AI is a technical layer inside Intelligence, not a separate business module. Mentor
and Goal Planner own their agents, tools, output schemas, prompts, and workflows:

```text
apps/server/src/shifu/intelligence/ai/
├── classical/
│   └── sklearn/
└── generative/
    └── agno/
        ├── agents/
        ├── outputs/
        ├── tools/
        └── workflows/
```

Shared model selection, credentials, and reusable provider construction belong to the
provider or composition boundary. Feature prompts and capability-specific orchestration
remain in Intelligence and must not move into `shared`.

Other modules consume an Intelligence core contract or a documented event. They must
not import concrete Agno agents, tools, workflows, prompts, or output models.

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

Agents receive a resolved model and explicit tools through constructor injection. They
do not read environment variables, choose credentials, construct repositories, or
instantiate use cases.

Internal prompts, system instructions, hidden reasoning, agent-to-agent messages, raw
tool transcripts, and provider metadata must never be returned to the browser. Expose
only validated domain results or comprehensible review findings.

## Model resolution belongs to the provider boundary

Centralize runtime model construction behind typed settings and provider composition.
Do not create one environment variable per agent and do not force every agent to use
one model profile when their cost, latency, or reasoning needs differ.

Agent definitions select a named model profile or receive a resolved model. The model
provider maps that choice to the environment-specific implementation and owns:

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
to the controller or Inngest job so the owning boundary can map or retry them. Do not
catch and rethrow without adding a meaningful recovery or error translation.

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

Every AI workflow consumed outside the AI package implements a `Protocol` under
`intelligence/core/interfaces`. Its inputs and outputs are domain primitives,
structures, or DTOs; Agno-specific schemas remain internal when callers do not need
them.

```python
from typing import Protocol


class PlanLearningGoalWorkflow(Protocol):
    def run(self, request: GoalPlanningRequest) -> GoalPlan: ...
```

Dependency pipes construct the concrete workflow and return the core protocol.
Controllers inject the protocol and do not import the Agno implementation. An Inngest
job may compose the concrete adapter at its outer boundary, but the use case still
receives only the protocol.

```text
intelligence/core/interfaces/                  public workflow contracts
intelligence/ai/generative/agno/               private implementations
intelligence/pipes/                            FastAPI dependency composition
intelligence/rest/controllers/                 protocol consumers
intelligence/messaging/jobs/                   durable protocol consumers
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

## FastAPI and Inngest own execution lifecycles

FastAPI owns AI work that participates in the current request or SSE stream. Disconnects
and cancellation should stop unnecessary model work when safe.

Inngest owns durable, scheduled, retryable, fan-out, or long-running AI work. Events
carry stable identifiers or immutable snapshots, and effects use idempotency keys. A
workflow does not implement its own scheduler, background task runner, or durable retry
loop.

## Privacy and observability

Record workflow identity, run identity, model profile, duration, token usage, tool name,
outcome category, and typed failure class when operationally useful. Correlate FastAPI,
Inngest, and provider runs without placing prompt content in correlation metadata.

Do not log or persist credentials, tokens, full prompts, hidden answers, chain-of-thought,
private tool arguments, unrelated learner context, or unrestricted model responses.
Evaluation datasets and traces follow the source data's access, retention, and deletion
requirements.

## Classical NLP remains reproducible

TF-IDF, cosine similarity, and scikit-learn classifiers live under
`intelligence/ai/classical/sklearn`. Persist or version the vocabulary, preprocessing,
model artifact, thresholds, and training-data identity required to reproduce results.

Training and reindexing run asynchronously. Request handlers may query a ready artifact
but never train a model or rebuild an index synchronously. Agno workflows consume
classical NLP results only through typed contracts.

## Tests follow the AI boundary

Keep focused agent, tool, output-schema, and workflow tests below the Intelligence AI
package. Use-case tests mock core workflow protocols. Tool tests mock injected use cases
or read contracts. Workflow tests use deterministic model and tool doubles to verify:

- structured input and output contracts;
- agent instructions and allowed tools;
- step order, branches, parallel joins, and review-loop limits;
- authorization-context minimization and user isolation;
- timeout, cancellation, quota, retry, and typed error behavior;
- suppression of prompts, tool traces, and hidden reasoning from public output.

Provider behavior remains covered through the consuming workflow or use-case boundary;
providers do not own dedicated test files. Real-model tests are opt-in, never the only
coverage, and never use production data.

## Review checklist

- [ ] The AI implementation is owned by Intelligence, not a generic shared feature.
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
- [ ] No AI code imports FastAPI, SQLAlchemy, REST controllers, or messaging transports.
