---
name: create-plan
description: Create an optional execution ledger for a ready Shifu Spec.
---

# Create an implementation Plan

Create a colocated `plan.md` only when a ready Shifu Spec needs explicit
coordination for cross-layer or cross-module work, migration and integration
risk, multiple ownership boundaries, meaningful parallelism, complex manual
validation, or recovery state. Use direct implementation for a small cohesive
Spec. The Plan is consumed by `implement-spec` and concludes through
`conclude-spec`.

The Plan is an execution ledger, not a second Spec. It must preserve the
current Spec's contract and revision, must not add product requirements or
technical obligations, and must route every implementation change through
`implement-spec`. The Orchestrator owns the Plan. Builders report against it
but never edit it.

## Preconditions and authority

Read and reconcile the following before writing the Plan:

1. the nearest `AGENTS.md` files;
2. the current `spec.md`, including its revision, status, source traceability,
   scope, exclusions, Functional Requirements (`RF-*`), Acceptance Criteria
   (`CA-*`), Design Contract, Technical Contract, Validation Contract, and
   dependencies;
3. [`documentation/sdd.md`](../sdd.md),
   [`documentation/modules.md`](../modules.md),
   [`documentation/architecture.md`](../architecture.md),
   [`documentation/tooling.md`](../tooling.md), and
   [`documentation/rules.md`](../rules.md);
4. every Rule Pack selected by the Rule router, including each applicable
   `Antipatterns to Avoid` subsection;
5. the complete canonical Confluence PRD page through Atlassian Shifu MCP,
   verifying the content ID and version recorded in the Spec;
6. the real Jira issue, design manifest and saved references, package
   manifests, lockfiles, infrastructure configuration, and existing feature
   artifacts that the Spec cites.

Confirm all of the following:

- the Spec status is `ready` and its revision is current;
- the Technical and Validation Contracts contain enough detail to sequence
  work without inventing a requirement or decision;
- every affected path, owning layer/module, command, service, fixture and
  generated-artifact boundary can be identified;
- every affected HTTP route group has a matching
  `apps/server/rest-client/<module>/<route-group>.rest` artifact, or the Plan
  explicitly assigns its creation to the same task that changes the routes;
- each declared REST-client artifact will cover every route in its group with
  current methods, paths, parameters, headers, representative bodies and
  reusable non-secret variables;
- every supplied design screenshot has a completed visual inventory in the
  Spec/design manifest, and every required supplemental state is either
  scheduled or recorded as an accepted assumption with no acceptance gap;
- Plan-backed execution is still warranted; and
- no material product, authority, ownership, contract or validation ambiguity
  remains.

If a planning decision would change product behavior, a module boundary,
architecture, a Rule, the Technical Contract, or the Validation Contract, stop
and route it through the applicable Spec/authority amendment workflow. Do not
silently resolve it in `plan.md`. Do not mutate Confluence or Jira as a side
effect of planning.

## Planning decisions and grilling protocol

Research repository facts directly; do not ask the user for facts that can be
inspected. Keep execution decisions with the user when they affect phase
boundaries, ownership, concurrency, dependencies, recovery, or validation
trade-offs.

Before creating or materially revising the Plan, model unresolved execution
choices as a dependency tree. The frontier is every decision whose
prerequisites are settled. Ask the whole frontier in one numbered round and
recommend an answer for each question:

```yaml
❓ **Q1** - **<question title>**: <question and relevant choices>

➡️ <recommended answer>

---

❓ **Q2** - **<question title>**: <question and relevant choices>

➡️ <recommended answer>
```

Wait for the user's answers before recomputing the next frontier. Limit the
tree to execution concerns. Product or technical-contract ambiguity belongs in
the Spec workflow. When the frontier is empty, present the shared execution
understanding and obtain explicit confirmation before creating or revising the
Plan.

Do not ask permission for an in-Contract correction during implementation. If a
Builder or validation finding exposes a contract change, stop the affected
phase and route it through the authority rules instead.

## Location and metadata

Create `plan.md` beside the governing Spec:

```text
documentation/features/<module>/<feature>/plan.md
```

For a bounded revision that lives under `changes/<change-slug>/`, create the
Plan beside that revision's `spec.md`. Use this front matter:

```yaml
---
title: <feature> implementation plan
status: draft
spec: ./spec.md
spec_revision: <current Spec revision>
evaluation: ./evaluation.md
source: <real Jira issue URL or key, when available>
last_updated_at: YYYY-MM-DD
---
```

`evaluation.md` is an expected colocated path. `implement-spec` creates or
reconciles it at implementation kickoff; `create-plan` must not fabricate
validation evidence or mark the Evaluation ready.

Keep the Plan status `draft` while readiness or external dependencies block
implementation. Set it to `in_progress` when implementation starts. Set it to
`completed` only through conclusion after all planned work and accepted
evidence are complete. Use no failure status. A Plan replaced by a revised
Spec is superseded only when the repository's SDD lifecycle explicitly records
that replacement.

## Required Plan structure

Write these sections, in order:

1. **Execution status**
2. **Readiness and dependencies**
3. **Execution ledger**
4. **Validation and handoff**
5. **Execution log** — add only after a material risk, finding, failed
   attempt, dependency transition or other execution event exists.

Do not repeat the Spec's objective, scope, requirements, algorithms, schemas,
technical decisions, complete PRD, or full Rule Pack. Reference the authoritative
documents and record only the execution information needed to coordinate work.

### 1. Execution status

Maintain one compact operational snapshot containing:

- Spec path, exact revision and `ready`/implementation status;
- why Plan-backed execution is warranted;
- current Plan status and phase;
- next action;
- active blockers and external dependencies;
- active Builders and the next dependency-ready Builder; and
- shared, generated, package, lockfile, migration or root-configuration
  ownership that cannot be represented by one task.

If the Spec revision changes, record the mismatch as a blocker, stop dependent
execution, invalidate affected task assignments and evidence, and reconcile
every phase, path, criterion, design reference and validation target before
resuming.

### 2. Readiness and dependencies

Use this section only for gates that affect whether a phase may start. Record
the exact source and owner for each gate:

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Current Spec is `ready` at revision `<n>` | Orchestrator | `pending` | `<action>` |
| External dependency | `<Jira/feature/service dependency>` is available at its real contract | `<owner>` | `pending` | `<action>` |
| Environment | `<service/account/fixture>` is available | `<owner>` | `pending` | `<action>` |

Do not turn a product dependency from `documentation/modules.md` into an
execution phase automatically. Sequence only the technical dependencies and
ownership boundaries required by this Spec.

### 3. Execution ledger

Use one phase and parallelism table with exactly these columns:

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Core` | F1 | `<observable outcome>` | — | — | `pending` | `<sensor-backed exit>` |

Derive the dependency graph from the Spec's Technical Contract, affected paths,
layer boundaries and executable validation dependencies. Use stable ownership
names such as `Builder Core`, `Builder Server`, `Builder Web`, `Builder
Validation`, or `Builder Integration` only when those boundaries are actually
affected. Do not create a Builder merely because a package exists or create one
Builder per task.

The Orchestrator owns SDD artifacts, root configuration, package installation,
lockfiles, shared/generated files, migration coordination, cross-Builder
integration and final validation. Paths may not overlap between active
Builders. Default to no more than three concurrent implementation Builders;
exceed that only when the Plan records stable contracts, a concrete
parallelism benefit and non-overlapping paths that justify the integration
cost. A Builder may own multiple sequential phases within its boundary.

Below the table, group concise task cards by phase:

```md
### F1 — <phase name>

#### F1-T1 — <task outcome>

- **Status/owner:** `pending` — Builder <ownership>
- **Depends/parallel:** <technical dependencies and safe parallel work>
- **Paths:** <exact owned paths or coherent path groups>
- **Traceability:** <RP-*, JN-*, RF-* and CA-* covered>
- **Outcome:** <observable result>
- **Rules:** <exact applicable Rule paths and relevant antipattern sections>
- **Risks/controls:** <material risk and bounded control>
- **Exit:** <focused commands/sensors and required evidence>
```

Every task must identify status/owner, dependency/parallelism, exact owned
paths, SDD traceability, observable outcome, applicable Rules, material risks,
and validation/exit evidence. Reference the Spec for technical detail.

For tasks that change HTTP routes, include the matching `.rest` artifact in the
owned paths and exit. The exit must verify one labeled request for every route
in the group, current methods/paths/parameters/headers/bodies, reusable local
variables, and no credentials. Record parity in `evaluation.md`; a REST-client
example never substitutes for real HTTP integration evidence.

For tasks that change server-backed behavior, the exit must verify the real
application boundary, response/error contract, persistence or authorization
result, and relevant side effects. Mocked transport alone is insufficient.

For tasks that change UI or browser behavior, the exit must require:

- comparison with the exact Spec visual inventory and Design Contract;
- every supplied and acceptance-relevant supplemental screenshot at its exact
  viewport and state;
- keyboard, focus, accessibility and narrow-viewport behavior when applicable;
- loading, empty, error and recovery states when applicable;
- console errors, failed requests and HTTP status inspection; and
- a fresh Playwright CLI screenshot for every affected design state.

Save screenshots and transient browser artifacts only as validation evidence;
do not commit them unless the repository explicitly tracks that artifact type.
Builders use saved design references and do not depend on Pencil MCP during
implementation or validation.

A Builder may not start until the Orchestrator records the exact Spec revision,
assigned phase/task, allowed paths, criteria, Rules, design references,
dependencies and exit condition. A task is not complete from a Builder report
alone. On an error or discrepancy, keep the task `in_progress`, record the
finding, invalidate affected evidence, resume the responsible Builder through
`implement-spec`, and rerun the exit. Activate a separate Builder Fix only when
the responsible Builder cannot be resumed or the correction is genuinely
independent.

Task and phase statuses are `pending`, `in_progress`, and `completed`. Keep a
failed or blocked item `in_progress` and record its finding/blocker and next
action. Keep the final integrated phase `in_progress` while integrated
validation is active.

### 4. Validation and handoff

Use one coverage table to schedule evidence without repeating the Spec's
scenario steps:

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | `<package or boundary>` | `CA-01` | Spec Validation Contract | `evaluation.md` `EV-<n>` | `pending` |
| Runtime | `<server-backed integration>` | `CA-02` | Technical Contract | `evaluation.md` `EV-<n>` | `pending` |
| Manual | `VM-01` | `CA-03` | Spec `VM-01` | `evaluation.md` `EV-<n>` | `pending` |
| Visual | `<viewport/state>` | `CA-04` | `design/<reference>.png` | Playwright artifact path + `EV-<n>` | `pending` |
| REST client | `<route group>` | `<CA-* or technical contract>` | `apps/server/rest-client/<module>/<route-group>.rest` | parity result + `EV-<n>` | `pending` |

Include only applicable rows. Schedule every required `VM-*`, every supplied
design state used as acceptance evidence, every required supplemental screenshot,
and every affected route-group REST-client artifact independently. Do not use
one generic screenshot or one generic validation row for multiple states or
viewports. Record a decision for each supplemental-screenshot suggestion when
it affects acceptance.

Use commands that actually exist in the current manifests and
`documentation/tooling.md`. Typical Shifu checks include the applicable subset
of:

```bash
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web test:unit
pnpm --filter web test:integration
pnpm --filter web build

cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe test:unit
uv run poe test:integration
uv run poe build
```

Do not invent a repository-wide `check:spec-implementation` command or claim a
sensor that is not present in the manifests. Structural conformance is recorded
as an Orchestrator review against the Spec's exact affected-path map and
Evaluation; executable quality gates remain the commands declared by the
project.

For Plan-backed execution, schedule exactly one read-only
[`Implementation Reviewer`](../agents/implementation-reviewer-agent.md) after
all Builder diffs are integrated and the applicable automated gates and
evidence baseline pass. Do not create reviewers per Builder, phase, application,
package or specialty. The Reviewer checks the complete candidate, cross-Builder
contracts, changed paths, generated artifacts, REST-client parity, evidence
freshness and all affected UI/server surfaces. The Reviewer report is advisory;
the Orchestrator verifies findings, records accepted `ACH-*` entries in
`evaluation.md`, resumes the responsible Builder, invalidates stale evidence,
and reruns the affected exits. Resume the same Reviewer after correction; do not
replace it merely because the candidate changed.

Define the final handoff condition explicitly. It requires:

- every task and phase completed;
- the exact Spec revision and complete integrated diff reconciled;
- all applicable pnpm/uv commands passed without lowering configured floors;
- generated routes, migrations, lockfiles, REST-client examples and other
  generated artifacts reviewed when affected;
- every `CA-*` and `VM-*` has current accepted evidence;
- every required visual comparison and supplemental-screenshot decision is
  current;
- every affected REST-client artifact is present and route-complete;
- the Implementation Reviewer completed and all verified findings are resolved;
- required services, accounts and fixtures are available or their limitations
  are explicitly recorded; and
- the Evaluation is ready for `conclude-spec`.

Then route directly to `conclude-spec`. Do not claim implementation, review,
quality gates or evidence passed before they are observed and recorded.

### 5. Execution log — conditional

After implementation starts, record only material operational events:

```md
- **YYYY-MM-DD — <phase/task event>**
  - **Finding/result:** `<ACH-*>`, `<EV-*>`, or concise result
  - **Next action:** <action and owner>
```

The Plan owns phase/task status, attempts and next action. Full commands,
outputs, screenshots, evidence details and reviewer verdicts belong in
`evaluation.md`.

## Plan integrity and summary

Before saving, verify:

- the Spec is `ready` at the exact recorded revision;
- dependencies are acyclic and every active Builder has non-overlapping paths;
- every `RF-*` and `CA-*` is scheduled or explicitly out of scope;
- all `RP-*`/`JN-*` traceability is inherited from the Spec rather than invented;
- every Rule path is valid and every exit uses an executable command or an
  explicitly defined manual/runtime sensor;
- all `VM-*`, design states, REST-client groups and server-backed boundaries
  have coverage;
- concurrency is justified and shared ownership is explicit;
- the Implementation Reviewer checkpoint and final handoff are present; and
- all colocated links and metadata are valid.

After creating or materially revising `plan.md`, return a concise summary with:

- clickable Plan path, status and Spec revision;
- reason for Plan-backed execution;
- number of waves, phases and tasks;
- active Builders, reused phase assignments, parallel waves, critical
  dependencies and shared ownership;
- the scheduled Implementation Reviewer and affected surfaces;
- planned automated, manual, runtime, REST-client and visual coverage;
- active risks or blockers; and
- initial phase and next action.

Do not present a blocked or draft Plan as implementation-ready, and do not
claim unexecuted phases, commands, review, sensors or validation passed.
