---
description: Integration-testing rules for Inngest jobs, module fixtures, durable execution, persistence, external services, and business invariants.
---

# Job Testing Rules

These rules apply to Inngest job tests under `apps/server/src` and to the fixture
infrastructure used by those tests.

## Job tests are integration tests

Test a job through a real Inngest Dev Server and the Nest module that owns the
job. The test must exercise the complete applicable path:

```text
domain event -> Inngest -> Nest job -> core use case -> repository/provider -> effect
```

Do not call a job handler, core use case, or `step.run` callback directly. Do not
replace a real repository with a mock. A passing direct invocation is not
evidence that event serialization, trigger validation, Inngest registration,
Nest injection, durable steps, or persistence work together.

One job test file belongs under:

```text
apps/server/src/<module>/messaging/inngest/jobs/tests/<job-name>.test.ts
```

Use one file per job. The top-level `describe` writes the job name with words
separated, such as `Generate Formalization Signature Preview Job`.

## Every job exposes a stable ID

The job class declares its function identifier once:

```ts
export class ExampleJob extends InngestJob {
  static readonly ID = "module/example";
}
```

Use `ExampleJob.ID` in `createFunction`, module fixtures, registration
assertions, and run matching. Do not repeat the identifier literal in tests or
fixture setup.

## Module fixtures own job integration setup

Each feature uses its existing `<Module>ModuleFixture` for both controller and
job tests. Do not create a separate job fixture or a function-based test context.
The module fixture composes `RestFixture` and `InngestFixture` internally while
preserving its controller-test registration API.

Register a job with this public shape:

```ts
let fixture: ExampleModuleFixture;

beforeAll(async () => {
  fixture = await ExampleModuleFixture.register({
    inngestJob: ExampleJob,
  });
});

afterAll(async () => {
  await fixture?.close();
});
```

Name the shared test variable `fixture`. Do not use redundant names such as
`exampleModuleFixture`, `jobFixture`, or `inngestFixture` in test files.

Internally, the module fixture constructs `InngestFixture` with the job's static
ID and a `createJob` callback:

```ts
const inngestFixture = new InngestFixture({
  functionId: Job.ID,
  createJob: async (client) => {
    const context = await registerModuleWithClient(client);
    return context.restFixture.get(Job);
  },
});
```

Resolve dependency-bearing jobs from the real Nest module after overriding its
`InngestClient` with the container-backed client. Do not manually construct a
job and mock its repository dependencies merely to satisfy `createJob`.

The module fixture owns startup rollback and teardown for every composed
resource. Cleanup must aggregate failures where necessary and must not leak Nest
applications, database connections, HTTP servers, containers, ports, or restored
environment variables.

## Use real infrastructure and external services

Job fixtures use Testcontainers for infrastructure that can practically run in
CI:

- `InngestFixture` owns the isolated Inngest Dev Server and SDK endpoint;
- `RestFixture` and `DatabaseFixture` own the Nest application, PostgreSQL,
  migrations, reset, and database teardown;
- a service-specific fixture owns an external service such as Supabase Storage,
  including its metadata database, gateway, initialization, and environment
  restoration.

Keep production adapters active. For example, a storage test uses the real
`SupabaseFileStorageProvider` and `SupabaseStorageProvider` against the storage
container; it does not replace either provider with an in-memory map.

Use a controlled fake only when no practical test service exists or when the
dependency is a cross-module port whose authoritative data must be supplied by
the originating module. Keep that exception local, expose it through the module
fixture, and assert the interaction when it matters to the job contract.

Do not start an unrelated service. A fan-out job with no repository or storage
dependency must prove its Inngest behavior without inventing a database or file
effect.

## Construct canonical events

Instantiate the domain event class and send its `name` and `payload`:

```ts
const event = new ExampleRequestedEvent({
  entityId: fixture.idProvider.generate(),
  occurredAt: fixture.datetimeProvider.now().toISOString(),
});

const run = await fixture.runInngest({
  name: event.name,
  data: event.payload,
});
```

Use the event class's `_NAME` when a name is needed independently. Never repeat
an event-name literal in a publisher, consumer, test, or assertion.

All test identifiers come from the module fixture's `idProvider`. Do not import
or call `randomUUID` in tests. Use the fixture's `datetimeProvider` for event and
domain timestamps instead of creating arbitrary current times.

Dates crossing the Inngest transport boundary must match the job's event schema.
Assert malformed, incomplete, duplicate, or oversized payloads when those are
meaningful transport rules.

## Execute through Inngest

Event-triggered jobs run through the module fixture:

```ts
const run = await fixture.runInngest({ name: event.name, data: event.payload });
```

Scheduled jobs use direct function invocation through the Inngest Dev Server:

```ts
const run = await fixture.invokeInngest();
```

The underlying generic fixture method is `InngestFixture.run`. Do not introduce
or use `execute` as an alias, and do not call a job's business callback directly.

Wait for a terminal Inngest state before reading effects. Assert the run status
and, when it is part of the contract, the function ID and output:

```ts
expect(run.status.toLowerCase()).toBe("completed");
expect(run.output).toEqual(expectedOutput);
```

For rejected work, assert `failed` and prove that forbidden side effects did not
occur.

## Cover business rules at the integration boundary

Core use-case unit tests own the exhaustive business-rule matrix. Job integration
tests select the critical rules that can be broken by event mapping, Nest wiring,
durable execution, provider composition, or persistence:

- the main successful transition or effect;
- an allowed retry or reprocessing path;
- idempotency when the target state is already reached;
- rejection from an incompatible or terminal state;
- compare-and-set, lease, attempt-token, or stale-worker protection;
- fan-out uniqueness, grouping, and bounded batch behavior;
- reconciler no-op and cleanup behavior;
- terminal failure mapping and preservation of successful prior work.

Every write scenario asserts the persisted result through the real repository or
production provider. A rejected scenario asserts that status, version, ownership,
files, publications, and other protected effects remain unchanged as applicable.
Do not stop at `run.status` when the job is expected to mutate state.

Known deterministic `AppError` business failures should become
`NonRetriableError` at the job boundary so Inngest does not retry work that cannot
succeed without a new event or state change. Unexpected infrastructure failures
remain retriable. Integration tests must distinguish these outcomes through the
terminal run and persisted effects.

## Isolate scenarios

When a file contains multiple database-backed scenarios, reset application tables
before each test:

```ts
beforeEach(async () => {
  await fixture.resetDatabase();
});
```

Clear mock call history and restore controlled default responses when the fixture
exposes an allowed fake. Tests must be order-independent. Seed only the state
required by the current rule and use module fixture helpers, domain fakers,
seeders, or real repositories rather than arbitrary SQL.

Do not reset the Inngest Dev Server between cases in the same file. A completed
run is the synchronization boundary before database reset.

## Keep the Dockerized suite separate and CI-enforced

Job integration tests run through:

```bash
pnpm --dir apps/server test:inngest
```

`apps/server/vitest.inngest.config.mts` includes only tests under
`src/**/messaging/inngest/jobs/tests/**/*.test.ts`, disables file parallelism,
and provides sufficient hook and test timeouts for cold container startup. The
default server Vitest configuration excludes the same directory.

Server CI must run `test:inngest` on a Docker-capable runner. Local absence of
Docker may prevent execution, but it must not turn the CI job into an optional or
silently skipped check.

Static validation remains required:

```bash
pnpm --dir apps/server check:types
pnpm --dir apps/server check:architecture
pnpm --dir apps/server exec vitest list --config vitest.inngest.config.mts
```

Test discovery proves only that files load and are selected. It does not replace
the container execution result.

## Antipatterns to avoid

- Calling `job.handle`, a step callback, or a use case directly from a job test.
- Constructing repositories as mocks for an integration scenario.
- Using `randomUUID`, hardcoded event names, hardcoded function IDs, or
  `inngestFixture.execute` in tests.
- Asserting only function options when the job has observable behavior.
- Asserting only `completed` without checking persistence, publication, fan-out,
  storage, or provider effects.
- Repeating the entire use-case unit-test matrix through containers.
- Starting Supabase Storage, Gotenberg, or another service for a job that does not
  depend on it.
- Treating Vitest discovery, TypeScript, or mocked coverage as proof that the
  Dockerized integration suite passes.
