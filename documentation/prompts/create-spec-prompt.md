---
name: create-spec
description: Create or revise a Shifu feature Spec from canonical Confluence requirements.
---

# Create or revise a Shifu feature Spec

Act as the SDD Orchestrator. Create or materially revise one bounded feature
Spec in the current task. The Spec is Shifu's local implementation Contract: it
translates a known version of product authority into observable behavior,
repository-grounded technical boundaries and executable validation. It is not a
copy of the PRD, a second Jira backlog, an implementation log or a Plan.

Use a direct maintenance workflow for formatting, typo-only documentation,
dependency/tooling upkeep, behavior-preserving refactors, or repairs already
covered by an unchanged Spec. If investigation reveals a product behavior,
domain rule, public contract, persistence semantic, cross-module event or user
journey change, stop maintenance and create or revise the Spec.

Do not create another user-owned task. Preserve unrelated work in the worktree.
Do not create a Plan, Evaluation, design bundle or implementation change until
the clarification and authority gates permit it.

## 1. Establish authority and classify the request

Read the following in order before authoring or modifying `spec.md`:

1. the nearest root and nested `AGENTS.md` files;
2. [`documentation/sdd.md`](../sdd.md) for SDD lifecycle, identifiers,
   authority and artifact ownership;
3. [`documentation/modules.md`](../modules.md) for module ownership and
   product-capability boundaries;
4. [`documentation/architecture.md`](../architecture.md) for runtime layers,
   applications, integrations and planned capabilities;
5. [`documentation/rules.md`](../rules.md), followed by every Rule Pack file
   selected from the affected paths and behavior;
6. [`documentation/tooling.md`](../tooling.md), the relevant manifests,
   lockfiles, development configuration and existing tests for real commands;
7. the complete canonical Confluence PRD page through Atlassian Shifu MCP;
8. the real Jira issue, report, design references, existing feature artifacts
   and the user's request when applicable.

Resolve the owning business module before defining scope. Business modules own
their domain rules, use cases, persistence adapters, application endpoints and
user-facing experience. Shared infrastructure may provide neutral contracts or
composition, but it must not absorb another module's business authority.

For the canonical PRD, verify and record the complete page URL, content ID,
version and retrieval time. Search results or excerpts are not sufficient
authority. If the complete PRD or required authority cannot be read, keep the
Spec `draft` and report the blocker; never mark it `ready` from an excerpt.

Use Shifu's stable identifiers only:

- `RP-*` — Requisito de Produto from the canonical Confluence PRD;
- `JN-*` — Jornada from the canonical product authority;
- `RF-*` — Requisito Funcional owned by the local Spec;
- `CA-*` — Critério de Aceitação owned by the local Spec;
- `VM-*` — Validação Manual owned by the Spec/Evaluation;
- `EV-*` — Evidência recorded in Evaluation;
- `ACH-*` — accepted or rejected review finding recorded in Evaluation;
- `CI-*` — an executable quality gate or automated validation check.

Never invent `RP-*` or `JN-*` identifiers, renumber existing identifiers, copy
the whole PRD into Git, or add local `RF/CA/VM/EV/ACH/CI` identifiers to the
Confluence PRD. The PRD's `Implemented` state is conclusion data; this workflow
does not check or uncheck it.

When a PRD requirement has a product dependency, use the dependency graph as
product capability and authoritative-fact context only. Do not convert the PRD
graph into implementation order, foundation work, execution waves or Plan
sequencing.

Classify the real source as one of `prd`, `issue`, `report` or
`direct-request`. Choose a delivery depth from risk rather than file count:

| Mode | Use when |
| --- | --- |
| `compact` | One cohesive outcome, stable dependencies, limited ownership and low delivery risk. |
| `complete` | Multiple applications/layers, persistence or integration changes, several UI states, or material security, concurrency, migration or operational risk. |

Every complete Spec requires the independent Spec Reviewer described below. A
compact Spec uses that Reviewer when the Orchestrator identifies architecture,
module-boundary, dependency-direction, generated-artifact or Rule-conformance
risk.

## 2. Research the repository directly

The Orchestrator performs repository research. Do not delegate repository fact
finding and do not ask the user for facts that can be inspected.

Inspect every affected boundary for:

- current paths, declarations, exports, registration, configuration and
  generated files;
- current control/data flow, reusable contracts and the exact technical gap;
- contracts crossing business modules, applications, packages, providers or
  persistence;
- existing implementation and test patterns that the Spec must preserve;
- installed versions and current official library documentation when an API or
  CLI may have evolved;
- authentication, authorization, privacy, tenant/account scope, concurrency,
  transactions, side effects, failure and rollout risk; and
- supplied design files, screenshots, viewports, states and the current
  `documentation/design.md` system.

Use repository files and manifests as evidence for paths and commands. When
documentation and code disagree, surface the discrepancy and state which
authority governs the Contract. Do not silently copy an implementation defect
into the Spec. Do not invent migrations, endpoints, tests, packages, ports,
environment variables, check commands or framework conventions.

When a current canonical PRD conflicts with repository documentation, report the
conflict. Product intent remains in Confluence; Architecture, Modules, Rules and
Tooling remain their respective authorities. Resolve an authority conflict
through the explicit amendment workflow, not by silently changing either source.

## 3. Clarify before writing the Spec

After research and the verification pass, identify every unresolved choice that
could materially alter product behavior, architecture, ownership, operability,
security, validation or the Builder Contract. Writing or modifying `spec.md`
before this gate is prohibited.

Repository-fixed facts and one-safe-answer conventions are resolved directly.
Product, technical, design and validation choices remain with the user unless
the cited authority already fixes them.

### Grilling protocol

Model unresolved choices as a dependency tree. Work in rounds:

- the frontier is every decision whose prerequisites are settled;
- keep one monotonically increasing question sequence across all rounds;
- ask the whole frontier in one round;
- include repository evidence, materially different choices, a recommendation
  and the consequence of accepting it;
- defer choices that depend on an unanswered earlier decision; and
- maintain a decision ledger after every answer round.

Use this format:

```yaml
❓ **Q1** - **<question title>**: <question, evidence and choices>

➡️ <recommended answer and consequence>

---

❓ **Q2** - **<question title>**: <question, evidence and choices>

➡️ <recommended answer and consequence>
```

Wait for the user's answers before recomputing the next frontier. Do not
silently treat a partial answer as acceptance of every recommendation. Record
accepted recommendations, explicit alternatives, contradictions, dependencies
and assumptions. Challenge contradictions and risks.

When the frontier is empty, present one consolidated shared-understanding
summary covering product, technical, design and validation decisions and request
explicit confirmation before authoring or amending the Spec.

Do not create a draft artifact to encode an unanswered material choice and then
ask the user to approve it. An existing Spec may remain `draft` during an
active amendment, but `draft` is not a substitute for clarification.

### Exhaustive questionnaire mode

If the user asks to decide, question or approve **every technical decision**, do
not collapse choices into a generic architecture question. Continue
dependency-ordered rounds until every consequential implementation-shaping
alternative is settled. Cover each applicable branch:

- owning module, application, layer, declaration and composition boundary;
- technology, protocol, dependency and provider/client abstraction;
- API route, method, authentication, authorization lifetime, payload,
  serialization, validation, compatibility and versioning;
- source of truth, transaction/commit boundary, persistence, migration,
  indexing, account/tenant scope and historical-value behavior;
- synchronous/asynchronous flow, publication timing, delivery guarantee,
  idempotency, deduplication, ordering, concurrency, buffering, backpressure
  and capacity limits;
- connection/subscription lifecycle, retries, timeouts, heartbeat, reconnect,
  offline/hidden behavior, replay and cleanup;
- multi-process, multi-tab, multi-device or multi-tenant coordination and safe
  degraded behavior;
- UI state ownership, widget boundaries, interaction semantics, exact copy and
  timing, focus, keyboard, announcements, responsive behavior, stacking and
  design-reference gaps;
- error translation, user-visible failure behavior, observability, privacy and
  secret handling; and
- automated test ownership, indirect versus direct boundaries, manual
  fixtures/services, viewports, screenshots and evidence targets.

Ask for exact operational values when they affect the Contract, such as a
duration, retry schedule, heartbeat, connection cap, queue size, viewport or
concurrency limit. Continue from broad prerequisites to dependent choices.

Before declaring the exhaustive frontier empty:

1. replay the decision ledger against every affected runtime boundary and
   selected Rule;
2. inspect the combination for newly exposed decisions and contradictions;
3. state any authority correction or design artifact needed before authoring;
4. present the consolidated shared understanding; and
5. request explicit confirmation. `confirmed` or an equally unambiguous
   confirmation passes this gate.

Do not create or modify the Spec before confirmation. After confirmation, apply
approved authority changes first, then author, run integrity checks and perform
the independent Spec review. If authoring or review exposes a genuinely
material unasked choice, return to the questionnaire with the next question
number. Resolve only repository-fixed compatibility corrections directly.

### Screenshot-derived clarification

When a screenshot reveals a feature, state or behavior not explicit in the
request, PRD or existing authority, ask before writing the Spec. This includes
inferred actions, permission boundaries, editable versus read-only fields,
session/device controls, deletion or destructive actions, badges, workflow
transitions, empty/loading/error behavior and role-specific differences.

Each question must include:

- screenshot path and exact visible element/state;
- current request/PRD statement, or an explicit note that none exists;
- proposed interpretation and a materially different alternative;
- recommendation and impact on scope, permissions, technical boundaries and
  validation; and
- classification as required behavior, visual-only treatment, excluded scope
  or unresolved ambiguity.

Do not silently promote a screenshot detail into an `RF-*`, `CA-*`, API, route
or implementation path. If the user cannot resolve a material screenshot
question, stop and return the evidence and question without writing the Spec.

### Authority changes

If the requested Contract requires a PRD, Architecture, Modules, Design,
Tooling or Rule change:

1. identify the current statement, evidence, proposed change and affected
   scope;
2. obtain explicit user approval for the normative change;
3. update the authoritative document first, using the applicable external-write
   workflow for Confluence; and
4. reread the updated authority and recompute the selected Rule Pack before
   writing the Spec.

Feature-specific behavior belongs in the Spec. Reusable conventions belong in
their authority. Do not update Confluence, Jira or global repository guidance
as an implementation side effect.

## 4. Create the feature artifacts

Create a short lowercase kebab-case path:

```text
documentation/features/<module>/<feature>/spec.md
```

For a distinct change to a concluded feature, create:

```text
documentation/features/<module>/<feature>/changes/<change-name>/spec.md
```

Use this metadata and omit empty optional fields:

```yaml
---
title: <feature title>
status: draft
revision: 1
source:
  type: <prd|issue|report|direct-request>
  ref: <actual URL, repository path or codex task>
scope:
  - <workspace, directory or file boundary>
last_updated_at: YYYY-MM-DD
---
```

Shifu Spec statuses are:

| Status | Meaning |
| --- | --- |
| `draft` | Contract authoring, authority alignment, review or amendment is active. |
| `ready` | Authority, clarification, integrity and applicable Spec review passed; implementation may begin. |
| `in_progress` | Implementation or conclusion is active. |
| `completed` | Accepted evidence and applicable delivery gates are complete. |
| `stale` | The recorded authority/source revision changed and reconciliation is pending. |

`open` is not a valid Shifu Spec artifact status. An explicit implementation
dependency does not by itself prevent `ready`; record the dependency and the
execution or integration step it blocks. Keep the Spec `draft` only when the
dependency leaves the implementation Contract materially ambiguous or another
readiness gate is incomplete.

Create only the artifacts appropriate to the stage:

| Artifact | Creation point | Purpose |
| --- | --- | --- |
| `spec.md` | This workflow | Product, technical and validation Contract. |
| `design/manifest.md`, `design/handoff.md` or the current feature-local design convention plus saved references | During authoring when UI is design-backed | File-backed implementation and visual-validation authority. Use one current convention; do not create duplicate inventories. |
| `plan.md` | Optional, after a ready Spec when Plan-backed execution is useful | Phases, dependencies, ownership and recovery ledger. |
| `evaluation.md` | At implementation kickoff | Actual validation evidence, findings and lessons. |

Do not create `evaluation.md` or record passing evidence during Spec authoring.
Do not create `plan.md` before the Spec is ready and Plan-backed execution has
been confirmed.

## 5. Required Spec structure

Write exactly these five top-level sections:

1. `# 1. Context and scope`
2. `# 2. Implementation Contract`
3. `# 3. Technical Contract`
4. `# 4. Validation Contract`
5. `# 5. Documentation alignment and revision history`

Keep the Spec compact when the selected mode is `compact`; omit conditional
subsections instead of writing empty sections or “not applicable” prose. State
each fact once and reference its identifier, Contract, authority or path
elsewhere. The Spec owns expected behavior and Contracts; the Plan owns
execution; `evaluation.md` owns actual evidence and findings.

Use tables for repeated fields and exact mappings. Tables are required for:

- scope/product alignment when more than one item exists;
- `RP/JN` to `RF` and `CA` traceability;
- design-frame inventory;
- affected paths grouped by application and layer;
- consequential technical decisions;
- validation coverage, Rule Pack and documentation alignment; and
- revision history.

Keep table cells concise. Use prose for rationale and constraints, numbered
steps for manual flows, compact JSON/signatures only when a boundary remains
ambiguous, and Mermaid only when a flow or state relationship is materially
clearer as a diagram. Quote Mermaid labels containing path or delimiter
punctuation.

### 5.1 Context and scope

Include:

- **Objective and source:** desired outcome, real source, owning module and
  selected `compact` or `complete` mode;
- **Current behavior and product gap:** user-visible baseline and missing or
  incorrect behavior;
- **Scope and product alignment:** included and excluded behavior, with each
  selected `RP-*`/`JN-*` outcome classified as `full`, `partial` or `deferred`
  for this delivery slice without weakening the PRD; and
- **Product decisions and assumptions:** resolved product choices and explicitly
  accepted premises, not an interview transcript.

Use these tables when applicable:

```md
| Area | In scope | Out of scope |
| --- | --- | --- |
| <area> | <included behavior> | <excluded adjacent behavior> |
```

```md
| Source requirement | Delivery | Notes |
| --- | --- | --- |
| <real RP-* or request anchor> | full | <bounded delivery note> |
```

Do not put repository implementation evidence, file plans or technical
decisions in this section.

### 5.2 Implementation Contract

Define observable requirements as `RF-*`. Keep internal paths, algorithms and
implementation attempts out of them. Every `RF-*` maps to at least one real
`RP-*` or the actual non-PRD source statement. Every `CA-*` maps to one or more
`RF-*`, and every `RF-*` maps to one or more `CA-*`.

Consume the complete applicable PRD requirement, not a single bullet. Use its
outcome, actors, authoritative inputs/outputs, capabilities, business rules,
limits, transitions, exceptions and experience requirements when deriving the
local Contract. Use `JN-*` as cross-requirement journey context; do not create a
second user-story or acceptance system in the Spec.

Use this requirements table when there is more than one requirement:

```md
| ID | RP/JN/source coverage | Required behavior |
| --- | --- | --- |
| RF-01 | RP-01, JN-01 | <observable behavior and restrictions> |
```

Every acceptance criterion must use the required mapping:

```md
| ID | RF coverage | Requirement | Given | When | Then | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | <observable criterion> | <precondition> | <action> | <result> | <test boundary and/or VM-01> |
```

Cover applicable success, rejection, authorization, account/tenant isolation,
concurrency, provider failure, persistence effects, session/hydration
restoration, accessibility, performance and secret boundaries. Do not put
implementation algorithms in behavioral criteria. Add a Cross-cutting
restrictions table only when several restrictions apply.

#### Design Contract — conditional

For design-backed UI, link the feature-local saved design authority and define
required frames/states, exact viewports, responsive behavior, implementation
surfaces, accessibility expectations and allowed deviations. Keep the detailed
inventory in the design artifact, not duplicated throughout `spec.md`.

The design authority must use the current Shifu convention. If the feature uses
`design/handoff.md`, do not create a parallel `manifest.md`; if it uses
`design/manifest.md`, keep that manifest canonical. Every saved reference must
have a route/surface/state, viewport, visible inventory, implementation surface,
criteria mapping and validation target.

When `.pen` files are involved, use the Pencil design skills/MCP. Never inspect
or modify encrypted `.pen` files with shell or generic filesystem tools. Before
the Spec becomes `ready`:

1. inspect the relevant editor state, frames, states, components, variables,
   viewports and nodes;
2. save one shared-workspace screenshot per required frame/state;
3. inspect every screenshot visually, not only by filename, dimensions or OCR;
4. verify each saved file is non-empty, a valid image, and matches its declared
   viewport or records its deliberate export scale;
5. record layout/clipping inspection and the implementation-facing inventory;
6. map every reference to an `RF-*`/`CA-*`/`VM-*` target; and
7. decide whether supplemental screenshots are required, recommended or not
   needed, with the rationale recorded.

Use this inventory:

```md
| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <name> | <file/node or supplied path> | <route/state> | <width × height> | <relative link> | <elements and hierarchy> | <controls/states> | <explicit notes> | <CA/MV target> |
```

Ask about a material gap before authoring. A required supplemental screenshot
must be captured and saved before `ready`, or the user must explicitly accept a
documented visual assumption. A recommended capture may be deferred only when
the design artifact records the deferral, rationale and planned runtime
validation. Builders and the Orchestrator use the saved bundle and do not
depend on live Pencil during implementation.

### 5.3 Technical Contract

Translate the behavioral Contract into one repository-grounded implementation
delta. A Builder must be able to identify each owning boundary, declaration,
dependency and runtime guarantee without choosing new product behavior or
architecture. Specify required declarations and semantics, not task order,
implementation attempts or incidental algorithms.

#### Current technical state

Record only relevant existing evidence: exact paths/declarations, current flow,
reusable contracts, generated artifacts, material versions, documentation/code
discrepancies and the exact gap.

```md
| Evidence | Current responsibility | Gap |
| --- | --- | --- |
| <path/declaration/authority> | <current fact> | <missing or incorrect behavior> |
```

Distinguish absent, incomplete and incorrectly wired capabilities. Every claim
must be inspectable in the repository or cited authority.

#### Solution and runtime flow

Explain the end-to-end runtime behavior without turning the section into a task
list:

- authoritative owner and entry point;
- synchronous/asynchronous boundary crossings;
- data/state transformations and serialization boundaries;
- authentication, authorization and account/tenant propagation;
- transaction start/commit boundaries, concurrency and idempotency;
- side-effect timing, event publication and retry ownership; and
- failure translation, recovery and partial-failure prevention.

Add one compact Mermaid flow only when three or more layers, state transitions
or failure branches make prose insufficient.

When a typed payload, event, persisted state or provider result crosses two or
more runtime boundaries, map it once:

```md
| Boundary | Producer | Consumer | Canonical contract | Mapping/guarantees | Failure ownership |
| --- | --- | --- | --- | --- | --- |
| <HTTP/event/repository/provider> | <declaration> | <declaration> | <type/schema and owner> | <serialization/consistency> | <translator and failure> |
```

#### Affected layer contracts

Use only affected Shifu layers: **Domain**, **Use cases**, **Interfaces**,
**Validation**, **REST**, **Provision**, **Database**, **Messaging**, **UI** and
**Composition**. Create one subsection per affected application/layer and omit
unaffected layers.

Every affected path appears exactly once with `Create`, `Modify`, `Generate` or
`Remove`, verified against the filesystem. Use repository-relative exact paths.
Name exact declarations, exports, registrations, generated outputs, side-effect
timing and runtime guarantees. Group declarations from one file in one row.
Tests and generated artifacts remain in their owning boundary. Root registries,
exports and cross-layer wiring belong in Composition.

Use this common path table:

```md
| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| <exact repository path> | Create/Modify/Generate/Remove | <exact symbol> | <runtime semantics and restrictions> | <producer/consumer> | <source command, registration or test boundary> |
```

Apply these layer constraints:

- **Domain:** module-owned Entities, Structures, Errors and Events; no
  framework, persistence, HTTP, provider or environment types. Include complete
  resulting field schemas and declarations for every changed Entity/Structure.
- **Use cases:** one authoritative action per use case; own business decisions,
  authorization and orchestration; define inputs, outputs, named failures,
  transaction/concurrency/idempotency and side-effect timing.
- **Interfaces:** core-owned ports with exact methods, implementers, consumers,
  semantic guarantees and failures; no SDK, database, HTTP or framework types.
- **Validation:** reusable Zod or boundary schemas only where the repository
  uses them; define shape, composition, exports and consumers without moving
  business authorization or domain rules into schemas.
- **REST:** one end-to-end operation from route/controller through core action
  to browser adapter where applicable; define method/path, status, request and
  response shapes, auth source, errors, registration and transport mapping.
  Controllers remain thin HTTP adapters.
- **Provision:** replaceable adapters for external SDKs, environment, clocks,
  IDs, auth, storage or other providers; define configuration, secrets,
  lifecycle, timeout, retry and safe-error ownership.
- **Database:** module-owned models/types/mappers/repositories, tenant/account
  filters, constraints, indexes, transaction owner, migration ordering,
  backfill/rollback and historical-value behavior. For each migration, specify
  Columns, Indexes, Constraints, database-specific notes and delivery
  constraints; do not embed SQL unless authority explicitly requires it.
- **Messaging:** authoritative event owner, stable name/payload, publisher,
  broker/job registration, retries, idempotency, ordering/concurrency,
  outbox/direct-delivery guarantee and durable side-effect ownership.
- **UI:** feature widgets under the module, shared widgets under `ui/shared`,
  thin routes, state ownership, props/callbacks, loading/empty/error/recovery
  states, responsive behavior, pt-BR copy, focus/keyboard/accessibility,
  reduced motion and design-token usage. Stateful widgets follow the required
  `index.tsx` plus colocated hook convention.
- **Composition:** application/module roots, providers, tokens, router or job
  registration, exports, lifecycle/order and generated composition artifacts.

For UI changes, define the widget hierarchy before the affected path map:

```md
| Widget | Kind | Parent/entry | Direct children | Public contract | Behavior owner |
| --- | --- | --- | --- | --- | --- |
| <exported widget> | Page/Layout/Component | <route or parent> | <direct children> | <props and visible responsibility> | <colocated hook or pure renderer> |
```

Also include an exact expected widget file tree when widgets are created,
moved, removed or structurally changed. Every tree entry must map to exactly
one affected UI path row. Include required `index.tsx`, colocated behavior
hooks, nested widget directories and permitted test paths. Do not invent files
merely because a framework commonly uses them; inspect the repository rules.

Audit the complete technical graph: every consumer has a producer or registered
implementation; interface changes identify all callers/implementers; every
declaration is exported/registered where required; schema and event changes have
compatible producers/consumers; every state mutation has transaction and
account/tenant ownership; every external side effect has timing/failure
ownership; generated artifacts name their source and command; and Core does not
depend inward on framework or feature-owned infrastructure.

#### Technical decisions

Record only consequential choices with a credible alternative:

```md
| Decision | Chosen approach | Alternative considered | Reason | Accepted trade-off |
| --- | --- | --- | --- | --- |
| <decision> | <choice> | <alternative> | <reason> | <cost/limitation> |
```

Do not restate standard repository conventions as decisions. An unresolved
choice keeps the Spec `draft` and returns to clarification.

### 5.4 Validation Contract

Testing is part of the Contract. Derive every boundary from the repository's
actual test taxonomy and name real test paths/suites and the `CA-*` IDs they
prove. Keep mocked transport, real application integration and manual
Playwright CLI evidence distinct. Do not invent test functions, arbitrary
coverage percentages, commands or evidence identifiers.

When multiple test boundaries exist, use:

```md
| Test file | Test type | Target | Coverage goal |
| --- | --- | --- | --- |
| <real path> | unit/component/integration/route/manual | <symbol or boundary> | <behavioral goal> |
```

```md
| Test file | Test case | Description | Assertions |
| --- | --- | --- | --- |
| <real path> | <real or descriptive case> | <scenario> | <observable result and side effects> |
```

Respect the selected Rules' test-integrity policy. A direct test for an
indirect/excluded source, forbidden directory or unapproved location is a
blocking Spec defect. Query/action hooks and web REST services do not receive
dedicated tests when the Rules assign their behavior to the consuming widget,
route or handler boundary.

Use this required acceptance coverage table:

```md
| Acceptance | Automated boundary | Manual scenario | Evidence target |
| --- | --- | --- | --- |
| CA-01 | <real test path/suite or reason none> | VM-01 or — | <evaluation section/artifact> |
```

For every `VM-*`, specify:

- mapped `CA-*` IDs, services/health checks, accounts/fixtures and preconditions;
- starting route/state, exact viewport and saved design reference when relevant;
- numbered actions, including keyboard interaction when applicable;
- expected visible result, final URL, network request and persistence/provider
  effect;
- accessibility/DOM/layout, focus, console and failed-request checks;
- evidence target; and
- cleanup or reset requirements.

List applicable commands in a real command table. Use only commands present in
current manifests and `documentation/tooling.md`, such as the applicable subset
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

Do not invent a repository-wide `check:spec-implementation` or
`test:coverage` command. If a required gate is not currently implemented,
record the limitation and the authority needed before declaring the Spec ready.
Do not call a skipped, mocked or unavailable check passed.

When HTTP routes are affected, require a matching
`apps/server/rest-client/<module>/<route-group>.rest` artifact. Declare it as
`Create` when absent or `Modify` when present. The Spec must require one
labeled request for every controller route in the group, current methods,
paths, parameters, headers, representative bodies, reusable non-secret
variables and no credentials. REST-client parity is artifact evidence, not a
substitute for real HTTP integration.

For UI/browser behavior, require exact design-state comparisons, applicable
keyboard and narrow-viewport checks, console and failed-request inspection, and
fresh Playwright CLI screenshots for each acceptance-relevant state. For
server-backed behavior, require the real application boundary plus persistence,
authorization and side-effect evidence; mocked transport alone is insufficient.

### 5.5 Documentation alignment and revision history

Use these tables:

```md
| Document | Authority for | State | Required change/confirmation |
| --- | --- | --- | --- |
| <PRD, Architecture, Modules, Design, Tooling or path> | <concern> | changed/confirmed | <result> |
```

```md
| Rule | Applies to | Evaluated revision |
| --- | --- | --- |
| <exact Rule path> | <affected boundary> | <repository revision/date> |
```

```md
| Revision | Date | Material change | Reason |
| --- | --- | --- | --- |
| 1 | YYYY-MM-DD | <created or amended Contract> | <source decision/change> |
```

Revision history records Contract changes, not implementation attempts, test
results or verdicts. Those belong in Evaluation.

## 6. Independent Spec Reviewer

After the Orchestrator authors the draft and completes Spec-definition integrity
checks, activate exactly one read-only
[`Spec Reviewer`](../agents/spec-reviewer-agent.md) before changing the Spec to
`ready` and before invoking optional `create-plan`.

The review is mandatory for every `complete` Spec and every material amendment.
For a `compact` Spec, activate it when the Orchestrator identifies architecture,
module-boundary, dependency-direction, generated-artifact or Rule risk.

Give the Reviewer the exact draft revision, source/mode, Architecture, Modules,
selected Rule Pack, relevant paths/declarations, `Create/Modify/Generate/Remove`
classifications, accepted technical assumptions, exclusions, prohibited paths,
test-integrity policy and known risks.

The Reviewer checks only Architecture, Modules ownership, dependency direction,
cross-layer boundaries, path placement, generated artifacts, migrations, test
placement and applicable Rules. It does not judge product completeness, design
fidelity, validation evidence, implementation code or PR readiness. It does not
edit files, ask the user questions, resolve product ambiguity or decide status.

Do not create Reviewers per application, package, layer, Rule, screenshot or
research lane. After a correction, resume the same Reviewer for the affected
compatibility check.

Verify every finding against authority. Apply accepted corrections to the draft,
rerun deterministic integrity checks and resume the same Reviewer. A material
product or technical ambiguity returns to the clarification gate. A forbidden
test path or incompatible layer contract is a blocking finding; replace it with
an allowed boundary before readiness.

## 7. Integrity gate and handoff

Keep the Spec `draft` while clarification, authority alignment, integrity work
or applicable review remains. Before changing it to `ready`, verify:

- source, PRD URL/content ID/version/retrieval time and Spec metadata agree;
- the owning module and all `RP-*`/`JN-*` identifiers are real and current;
- every applicable PRD requirement was consumed through its full product
  contract, not a selected bullet;
- every `RF-*` maps to a real source requirement and every `CA-*` maps to an
  `RF-*`, with both directions complete;
- no Product Dependency Graph edge was treated as implementation sequencing;
- no PRD `Implemented` checkbox was changed by this workflow;
- scope, exclusions, actors, permissions, states, error behavior and deferred
  adjacent work are explicit;
- technical paths are filesystem-valid, each appears once, and change
  classifications are correct;
- every affected Entity/Structure has a complete resulting schema;
- every cross-boundary producer/consumer, auth, persistence, event and failure
  relationship is explicit;
- migrations, generated files, routes, exports, registrations and lockfile
  implications are accounted for;
- the Design Contract and saved screenshot inventory are complete when UI is
  affected, including supplemental-screenshot decisions;
- every `CA-*`, `VM-*`, test boundary and real command has executable coverage;
- every affected HTTP route group has complete REST-client parity;
- the selected Rule Pack and documentation links are valid;
- Markdown tables, links, Mermaid and artifact structure are valid; and
- the applicable Spec Reviewer inspected the current revision, every verified
  finding is resolved, and the same Reviewer rechecked affected corrections.

The handoff must be executable rather than interpretive. Include exact
repository-relative file/widget trees for changed UI surfaces, allowed and
prohibited paths, owning layer/module, generated-file treatment, Builder exits,
design/state mappings, required loading/empty/success/error/recovery/disabled/
selected/focus/keyboard/responsive behavior and explicit exclusions. An
incomplete tree, ambiguous widget boundary, missing state, missing screenshot
mapping or non-executable validation command keeps the Spec `draft`.

After the gate passes, update only the Spec metadata to `status: ready` and
report:

- clickable Spec path, revision and status;
- objective, user-visible outcome, scope and important exclusions;
- canonical PRD URL/content ID/version and Jira/source traceability;
- key product and technical decisions;
- affected applications, modules/layers and technical approach;
- design screenshot count and state/viewport coverage, when applicable;
- automated boundaries and `VM-*` coverage;
- accepted assumptions, risks and blockers;
- Spec Reviewer result; and
- recommended execution strategy: direct `implement-spec`, or `create-plan`
  followed by Plan-backed `implement-spec`, with the evidence-based rationale.

Recommend direct implementation for a small cohesive change with stable
dependencies, limited ownership and no meaningful execution waves. Recommend a
Plan for dependent phases, multiple applications/shared ownership,
migration/provider/concurrency/security risk, multiple design-backed surfaces
or manual environments, useful parallel lanes or a recovery ledger. Do not
choose by file count alone.

Do not claim the Spec is ready if an authority, review, design artifact,
filesystem path, command, traceability mapping or validation boundary is
missing.

## 8. Material amendments

For a material amendment before conclusion:

1. set the existing Spec to `draft`;
2. increment `revision`;
3. repeat authority preflight and clarification;
4. refresh affected Contracts, design references, paths and validation coverage;
5. preserve prior Evaluation evidence as historical and mark affected evidence
   stale rather than erasing failed attempts;
6. rerun the integrity gate and applicable Spec Reviewer against the amended
   revision;
7. return the Spec to `ready` only after verified findings are resolved; and
8. re-evaluate direct versus Plan-backed implementation.

Amend the same Spec. Create a new Spec only when the original feature is
concluded and the request is a distinct change.
