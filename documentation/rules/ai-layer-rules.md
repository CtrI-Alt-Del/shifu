---
description: Mastra module, workflow, tool, agent, model resolution, and AI boundary rules for the server.
---

# AI Layer Rules

These rules apply to shared AI infrastructure and feature-owned AI orchestration
under `apps/server/src/<module>/ai`.

## AI orchestration is owned by the consuming module

AI is a technical layer inside a feature module, not a separate business module.
Each feature owns its agents, tools, schemas, prompts, and workflows:

```text
apps/server/src/<module>/ai/
├── mastra/
│   ├── agents/
│   ├── schemas/
│   ├── tools/
│   └── workflows/
└── <module>-ai.module.ts
```

Shared provider selection and reusable Mastra infrastructure belong under
`apps/server/src/shared/ai`; feature prompts and business-specific orchestration
must not move there.

## Agents extend the shared `MastraAgent`

A feature agent is an injectable class that extends the HMS `MastraAgent`, which
in turn extends Mastra's native `Agent`. Configure the agent through `super` in
its constructor:

```ts
@Injectable()
export class ExampleAgent extends MastraAgent<'example-agent'> {
  constructor(envProvider: EnvProvider) {
    super(
      {
        id: 'example-agent',
        name: 'Example Agent',
        model: 'deepseek/<model>',
        instructions: `...`,
      },
      envProvider,
    )
  }
}
```

Keep instructions in the agent configuration unless they are genuinely shared
by multiple agents. Do not introduce a separate instruction constant merely to
move the text out of the class. Internal prompts, reasoning, system instructions,
and agent-to-agent messages must never be exposed to the user; expose only the
final domain result or comprehensible review findings.

Do not wrap agents in another `this.agent` property. Inheritance preserves the
native agent API and its type parameters directly.

## Model resolution belongs to the shared base agent

Each agent chooses the OpenRouter model appropriate to its task. Do not force all
agents to use one production model and do not create one environment variable per
agent by default.

The shared `MastraAgent` resolves the runtime provider:

- local development uses Ollama and the single `OLLAMA_AI_MODEL` environment
  value so the team can select a model compatible with each machine;
- staging and production use OpenRouter with the model declared by the agent;
- agent model names use the provider catalog identifier such as
  `deepseek/deepseek-v4-pro`, without an additional `openrouter/` prefix;
- a missing production OpenRouter credential raises `AppError`, never native
  `Error`.

Local execution exists to validate workflow composition and integration. It is
not expected to reproduce the production model's reasoning quality.

## Tools are injectable use-case adapters

Use one injectable class per Mastra tool. A tool assigns `this.function` directly
from `createTool` in its constructor and preserves its schemas in the generic
return type:

```ts
@Injectable()
export class ExampleTool {
  readonly function: ReturnType<
    typeof createTool<'example-tool', typeof inputSchema, typeof outputSchema>
  >

  constructor(dependency: Dependency) {
    const useCase = new ExampleUseCase(dependency)
    this.function = createTool(/* ... */)
  }
}
```

Input and output schemas stay in the tool file when only that tool uses them. A
schema may move to `schemas` when a workflow, job, agent, or multiple tools share
the same transport shape.

Tools may receive repositories and providers through NestJS injection, then
instantiate and execute core use cases with those dependencies. Business rules
belong to the use case, not to `execute`. Do not add toolkit aggregator classes,
`MastraMcp`, or intermediate tool-handler classes whose only purpose is to call
the use case.

## Workflows contain composition, not business logic

A workflow is an injectable class. Build and commit the Mastra workflow in the
constructor; do not hide construction in a `createWorkflow()` helper method.
Workflow code may declare steps, maps needed to connect schemas, loop conditions,
and branch selection. Parsing, pending-marker collection, review-cycle behavior,
outcome resolution, persistence, and other domain work belong in tools and core
use cases.

Create Mastra steps from the injected tool function:

```ts
const step = createStep(this.exampleTool.function)
```

Do not recreate tool logic as inline workflow steps. Let workflow and agent
errors propagate to the owning job so Inngest can apply its retry behavior; do
not surround the workflow run with a catch-and-rethrow block. Known failures
raised by HMS code still use `AppError` or a module-specific subclass.

## Workflow contracts are exported through Core interfaces

Every workflow consumed outside its AI module implements a core interface owned
by the feature. Its input is a core structure; Mastra-specific schemas and output
details remain internal when callers do not need them.

Because TypeScript interfaces do not exist at runtime, the AI module binds the
concrete workflow to a feature token with `useExisting` and exports only that
token:

```ts
{
  provide: MODULE_WORKFLOWS.example,
  useExisting: MastraExampleWorkflow,
}
```

Consumers inject the token and type the dependency with the core interface. They
must not import the concrete Mastra workflow class.

```ts
@Inject(MODULE_WORKFLOWS.example)
workflow: ExampleWorkflow
```

Agents and tools remain internal providers unless another explicitly documented
module boundary requires a public contract.

## Source context comes from the originating module

An AI workflow must not access repositories owned by another business module to
assemble its prompt context. The originating module validates access, loads its
own data, and places an immutable normalized snapshot in the domain event.

Document Production receives `DocumentGenerationSource` from Consulta,
Formalização, or Caso, persists it for traceability, and passes that same snapshot
to its writing and review agents. It loads only data it owns, such as the selected
document model. Reprocessing uses the persisted/requested snapshots rather than
silently incorporating later changes from the source module.

## AI output is structured and reviewed

Agent results use Zod structured output. Never parse free-form model text as the
primary success path when a schema can express the expected result. The schema
must constrain the content that crosses from the model into application code.

AI-generated legal documents pass through a reviewer loop owned by the feature
workflow. Review findings exposed outside the AI layer use domain categories and
plain, comprehensible language. Agent instructions and hidden reasoning are not
part of the domain output.

