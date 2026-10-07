---
name: create-spec
description: Create or revise a bounded Shifu Spec with product contracts and concrete acceptance checkers.
---

# Create or revise a Shifu feature Spec

Act as the SDD Orchestrator. Translate a known version of canonical product
requirements into one bounded, testable implementation contract. The agent
handles execution order, decomposition and delegation. Do not create `plan.md`
or put a task breakdown or execution ledger in the Spec. Scoped expected file
trees describe affected boundaries; ordinary helper organization remains flexible.

Direct maintenance is sufficient for formatting, tooling upkeep, mechanical
refactors and repairs covered by an unchanged contract. A change to product
behavior, public contracts, persistence semantics, cross-module events or user
journeys requires a new or amended Spec. Preserve unrelated work and keep the
work in the current task.

## 1. Establish authority and research the boundaries

Read the applicable `AGENTS.md` files and these authorities:

- [`sdd.md`](../sdd.md): lifecycle, identifiers, ownership and evidence rules;
- [`modules.md`](../modules.md) and [`architecture.md`](../architecture.md):
  business ownership, runtime boundaries and implemented versus planned capabilities;
- [`rules.md`](../rules.md) and every Rule Pack selected from the actual scope;
- [`tooling.md`](../tooling.md), relevant manifests, lockfiles and configuration:
  installed tooling and commands that exist;
- the affected module's complete canonical Confluence PRD through Atlassian Shifu
  MCP, plus the real issue, report, user request and existing feature/design artifacts.

Record the canonical page URL, title, content ID, version and retrieval time;
verify parent and update metadata when available. Search excerpts cannot establish
product authority. Missing required authority keeps the Spec `draft` with a stated
blocker. Do not copy the whole PRD into Git or change its `Implemented` checkboxes.

Research the affected entry points, module paths, existing public contracts,
consumers, persistence and side effects. Follow the repository's CodeGraph
instructions when implementation exploration is needed. Inspect manifests before
naming checkers; use current official library documentation when an API is uncertain.
Resolve inspectable facts directly. Independent research may be delegated within
bounded read-only scopes; shared authority decisions remain with the Orchestrator.

Confluence owns product intent; Architecture, Modules, Rules and Tooling own their
respective concerns. Report conflicts and resolve the affected authority explicitly.
Do not silently weaken a PRD or copy a current implementation defect into the Spec.
Jira and Confluence writes require an explicit user request, followed by readback.
Changes to repository authorities must be within the user's authorized scope.

Select `compact` for a cohesive outcome with stable boundaries and low risk;
select `complete` for material security, concurrency, migration, persistence,
cross-module or integration risk. Scale detail to that risk, not file count.
A compact Spec retains all seven sections with concise scope, only affected
consequential contracts and sufficient focused proof. Omit empty optional detail;
no minimum length, declaration count or file inventory is required. Complete mode
adds detail only for identified risks and guarantees.

## 2. Explain approaches and resolve material ambiguity

Before drafting, explain the settled design progressively: outcome/scope,
responsibilities and public interfaces, runtime flow/failures, and verification.
Scale detail to risk. For unresolved consequential architectural choices, compare
2–3 viable approaches grounded in Shifu; recommend one and explain compatibility,
ownership, consistency and recovery tradeoffs. Do not invent alternatives when
existing authority settles the choice or add speculative capabilities/refactoring.
Record the selected approach and rationale in the existing Technical Contract.

### Grilling protocol

Research inspectable facts directly. Ask only about unresolved product decisions
or consequential technical tradeoffs: actors, permissions, scope, destructive
behavior, ownership, public compatibility, irreversible persistence and required
verification. Ordinary reversible implementation choices belong to the agent.

Build a dependency-ordered set of material decisions. Ask independent currently
answerable questions together; ask dependent questions after their prerequisites
are resolved. Number questions monotonically across rounds. Ask directly in the
conversation, without a question tool:

```text
❓ Q1 — <title>: <question, evidence and consequences of materially different choices>

➡️ Recommended: <answer and its consequence>
```

Wait for the affected answers; partial answers settle only answered questions and
silence never approves a recommendation. Continue independent research while
waiting. Challenge contradictions respectfully and resolve consequential ambiguity
before authoring a new contract/design manifest. An existing amendment remains
`draft` while decisions are pending. Summarize accepted decisions in the contract,
without an interview transcript or separate decision-tree artifact.

If authority and authorization already settle material choices, proceed without
inventing questions or asking for generic confirmation. Honor an explicit user
request to approve every technical decision when present.

Screenshots establish visual intent, not new permissions/actions/workflows.
Resolve design-derived behavioral ambiguity against the canonical PRD. Visual
choices consistent with the PRD and UI Rules may proceed directly. A product
amendment requires an explicitly authorized Confluence update and a complete
reread before Spec reconciliation; preparing a Spec never authorizes that write.

## 3. Author the contract

Read the complete canonical template at
[`documentation/templates/sdd/spec.md`](../templates/sdd/spec.md) before authoring
or reconciling a Spec. Use its content as the starting structure and replace its
placeholders with the actual delivery contract. The templates directory
`documentation/templates/sdd/` is part of this workflow's required context;
the abbreviated examples below do not replace the complete template.

Use `documentation/features/<module>/<feature>/spec.md` with lowercase kebab-case
slugs. A distinct change to a concluded feature may use
`changes/<change-name>/spec.md` beneath that feature. Use the contract structure below and omit empty optional fields.

```yaml
---
title: <feature title>
status: draft
revision: 1
source:
  type: <prd|issue|report|direct-request>
  ref: <actual URL, repository path or task reference>
scope:
  - <owning module or boundary>
last_updated_at: YYYY-MM-DD
---
```

States are `draft` → `ready` → `implemented` → `completed`; use `stale` when
source reconciliation is pending. `implemented` means the candidate has accepted
current evidence and is ready for conclusion; delivery gates are required for `completed`.

Use the canonical [Spec template](../templates/sdd/spec.md) and exactly seven
sections: Objective; Scope; Behavior Contract; Technical Contract; Verification
Contract; Documentation Alignment; Revision History.
State each fact once and reference its identifier elsewhere. Create `evaluation.md`
at implementation kickoff, not during Spec authoring. Save feature-local design
references only when needed for the contract. No separate planning artifact exists.

### Objective and Scope

State the desired outcome, current behavior, owning module, source/mode,
included behavior and explicit exclusions. Canonical authority metadata belongs
in Documentation Alignment: PRD URL/title/content ID/version/retrieval time and
selected RP/JN IDs, with parent/update metadata when available.
Classify selected product outcomes as `full`, `partial` or `deferred` for the
bounded delivery slice without weakening their canonical meaning.

Use stable Shifu identifiers: canonical `RP-*` and `JN-*`; local `RF-*`, `CA-*`,
`VM-*`, `EV-*`, `ACH-*` and `CI-*`. Never invent or renumber canonical IDs or
write local IDs into the PRD. Product dependency graphs describe capability and
authoritative facts; they do not prescribe implementation order.

### Behavior Contract

Define observable requirements and consume the complete applicable PRD outcome:
actors, authoritative inputs/outputs, rules, limits, transitions and exceptions.
Every `RF-*` maps to at least one actual `RP-*`; relevant `JN-*` and precise
issue/report/request statements supply context without inventing product IDs.
Every `RF-*` has acceptance coverage; every `CA-*` maps back to `RF-*`.

```md
| ID | RP/JN/source coverage | Required behavior |
| --- | --- | --- |
| RF-01 | <real source IDs or anchor> | <observable outcome and restrictions> |

| ID | RF coverage | Given | When | Then | Proof |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | <precondition> | <action> | <observable result> | CI-01 / VM-01 |
```

Cover applicable authorization, account isolation, persistence, concurrency,
provider failure, recovery, accessibility and secret boundaries. Specify results
and guarantees; do not prescribe incidental algorithms or helper classes.

For design-backed UI, reference one feature-local design inventory with required
happy-path states, routes/surfaces, viewports, saved images, criteria mapping and
allowed deviations. Reuse an existing `design/manifest.md` or `design/handoff.md`
convention rather than duplicating it. Inspect saved references visually. Use Pencil
skills/MCP for `.pen` inspection and exports; never read its contents with shell tools.
Map affected widgets to source-verified semantic tokens and actual shared primitive
variants in the handoff, including typography, spacing, surfaces, borders, focus
and pending/error states where material. Identify preserved UI outside the change.
Required references must be available before `ready`, or carry an explicitly
accepted visual assumption. Negative, loading, error and recovery behavior belongs
in automated acceptance coverage; it does not create additional manual journeys.

### Technical Contract

Use two subsections: **Architecture Mapping** and **Runtime Flow**.

Architecture Mapping identifies the owning module and applicable Rules with:

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create / Modify / Delete | <actual affected Shifu layer> | <symbol and consequential path> | <resulting contract, consumers, exports and registration> |

Inspect consequential paths and classify actions honestly. The mapping is
sufficient when it establishes ownership and consumer impact. Add a scoped
expected file tree only when it clarifies a consequential boundary, registration
or generated output; show new `[N]` and modified `[M]` files and necessary parents.
Keep deletions/unchanged consumers in the mapping. Mark planned/conditional paths
and identify generated inputs and actual commands; never invent migration names.
Routine helper names and internal organization may evolve under the Rules without
a Spec amendment when contracted behavior and guarantees remain unchanged.

Describe named affected elements beneath the mapping without empty mandatory
subsections. Include expected Python declarations for backend domain objects,
ports, use-case inputs/results and execution signatures; expected TypeScript/Zod
declarations for affected Web contracts. Creates show complete public declarations;
modifies show complete results or explicitly scoped excerpts with unchanged
members identified; deletes account for replacements, consumers and compatibility.
Reference source declarations for unchanged contracts instead of duplicating
them. Include snippets only where a changed public shape/signature or guarantee
needs to be fixed for consumers; leave private helpers and implementation bodies
out. Keep infrastructure/framework types out of Core.

Specify affected REST method/path/request/response/error contracts and matching
non-secret `apps/server/rest-client/<module>/<route-group>.rest` examples;
SQLAlchemy mapping, constraints/indexes and Alembic migration/backfill/compatibility
and transaction guarantees; widget responsibilities/props/composition and state
ownership; query/action hooks and cache invalidation at their owning boundaries;
provider configuration/lifecycle and composition; event/job triggers, typed payloads,
publishers/consumers, retries, idempotency/concurrency and registration. Use the
installed Shifu stack and commands verified in its manifests and Tooling.

Runtime Flow explains actual entry points, trusted account context, validation,
domain decisions, transactions, persistence, effects and visible/cache results.
Include relevant rejection, failure, retry/recovery and concurrency guarantees.
Use Mermaid sequence/flowchart diagrams where useful, with separate paths when
needed for readability. Audit mapping and flow together for complete consumers,
exports, registrations and producer/consumer responsibilities. Business ownership
remains with the module; Shared contains technical infrastructure.

### Verification Contract

Use **Automated**, **Manual** and **Visual** categories with individually named
check blocks, rather than long command/procedure tables. Preserve Shifu IDs:
`CI-*` for automated checks, `VM-*` for manual/visual checks with explicit Type,
unique VM IDs across both categories, and `EV-*` for actual results in Evaluation.
Keep existing IDs/mappings on continuation; split old groups only with explicit
mapping and fresh proof where the historical result is insufficient.

Every CA maps to sufficient concrete proof; it need not use every category.
Each check names CA coverage, expected outcome, actual tool/command and working
directory, exact test file and boundary where applicable, setup/input selection
or concise procedure, pass condition and limitations. Give distinct observable
outcomes separate check blocks; complementary use-case/controller/widget/job
proof may support the same outcome. Keep baseline gates separate and reference
the applicable Tooling/Rule checks, including affected consumers. Define separate
type, lint and complexity obligations/dispositions using
[scoped static-check guidance](../tooling.md#scoped-type-lint-and-complexity-checks).
Use exact paths for lint and affected configured projects for types. Complexity
must identify its checker and actual limits; no dedicated metrics command is
currently configured. A required unavailable metrics gate stays Blocked.
Mark absent
files/scenarios planned; verify test names before prescribing filters.

Share executable setup once for related checks. Inspect source-defined accounts,
fixtures, seeders, manifests and configuration before prescribing:

- environment/URLs and health, route/function registration, real/mocked/disposable services;
- actors, permissions and private credential resolution from exact source paths;
- necessary data relationships/statuses, initial-state assertions and any planned fixture corrections;
- isolation, rerun dependencies/collision avoidance, recovery and owned-resource cleanup.

Authoring setup does not require running tests or authorize resetting/reseeding
shared data. Distinguish correcting fixture/seed source from applying it; prefer
isolated/disposable setup. Missing executable setup is a contract gap.

Automated checks cover authorization, isolation, persistence, finite contracted
combinations, bounds, failure/recovery and concurrency at permitted boundaries.
For unbounded domains specify equivalence classes and boundary values. Assess
targeted mutation testing for changed business rules/correctness-critical logic:
record whether it is required and why, the concrete risk, target scope, verified
runner, mutation classes, pass condition and survivor/equivalence disposition.
It is not a universal gate for every business-rule edit. When not required,
identify the assertions that address the risk and why mutation adds insufficient
value for this slice. Tool availability alone is not a reason to omit necessary
proof; never downgrade an already-required check just to obtain readiness.
Use the application mutation scripts and scoped selection documented in
[Tooling](../tooling.md#mutation-testing): Stryker for Web and mutmut for Server.
CI explicitly uses `--all`; local verification selects affected files and tests.
Runner success does not prove all mutants were killed; define survivor handling.
A required unavailable mutation check remains Blocked and ordinary coverage cannot
satisfy it; record any deferral explicitly.

Respect test-integrity Rules: forbidden direct tests or excluded/indirect source
tests are blocking contract defects; use allowed consumer boundaries. Never
invent coverage percentages or a generic aggregate quality command. Confirm the
intended tests actually execute; skips/empty selection are not passing proof.

Use focused unit/component and static feedback during building. After integration,
run affected integration files/scenarios selected from changed behavior, consumers
and dependencies, with one Orchestrator-owned verification runner. Do not require
full local suites merely because an application was touched or implementation was
integrated. Select tests only for scoped changes and directly affected consumers;
broaden only for demonstrated dependency impact or a gap in that scope's proof.
A full local suite requires scope spanning that suite or an explicit user request.
Link to [Tooling's selection policy](../tooling.md#selecting-unit-and-integration-tests)
and record why each selected boundary is affected. Fix failures and rerun
failed/affected checks until passing.
Review/conclusion reuse current unaffected proof. When actual coverage tooling
runs tests, avoid duplicating the same unchanged full run.

Manual checks are concise agent-executable happy paths using Playwright CLI or
terminal. Define setup, a narrow action sequence and observable outcomes: final
URL/content, relevant requests/persisted effects, console classification, required
keyboard/focus/narrow viewport and cleanup. Automated tests own systematic
negative, failure/recovery and concurrency matrices. Mocks cannot prove required
real authenticated/persisted journeys.

Visual checks name the reference, state, viewport, comparison properties and
accepted deviations. Capture during linked Manual journeys where possible and
inspect images; saving a screenshot is not a visual pass. Keep runtime evidence
under ignored browser/test output or CI artifacts; record paths/results in
Evaluation, without new feature-local evidence folders. State why a category is
inapplicable instead of keeping empty placeholder blocks.

### Documentation Alignment and Revision History

Documentation Alignment records canonical source identity/version/retrieval,
selected RP/JN, Rule Pack, required updates/confirmations and external-write
dependencies. Actual performed updates and delivery results belong in Evaluation.
Revision History records meaningful behavior, technical, design or verification
contract amendments and reasons. Structural cleanup, status changes, reruns,
publication and conclusion do not increment revision.

## 4. Review and readiness

Perform an independent Spec compatibility pass before `ready`, for compact and
complete Specs, using one read-only [Spec Reviewer](../agents/spec-reviewer-agent.md)
for the selected Rule Pack. Keep the Spec `draft` until review completes and
blocking findings are resolved. Material amendments repeat affected review.
The reviewer explicitly audits applicable Rule sections and dynamic Rule selection;
listing Rules alone does not prove compliance. Compact review stays proportional
to its changed contracts and risks, without demanding an exhaustive file inventory
or pre-implementation execution. No separate review artifact is needed.

Give the reviewer the exact revision, relevant authorities, owning boundaries,
public contracts, test-integrity policy, accepted assumptions and known risks.
The reviewer is read-only and checks architecture and Rules; it does not choose
product behavior or require runtime proof before implementation. Verify findings,
correct accepted defects and recheck affected findings with the same reviewer.

Before `ready`, confirm authority/version metadata; scope and traceability;
observable criteria; resulting declarations, consumer/wiring impact and runtime
guarantees; available required design references; permitted test boundaries; real
checker commands; documentation links; reproducible setup/fixture feasibility and
safe cleanup;
and resolution of verified compatibility findings. Explicit implementation
dependencies block affected work, not readiness, unless they leave the contract
materially ambiguous. Report concrete blockers instead of a successful gate.

Report the Spec path/revision/status, bounded outcome, canonical source/version,
consequential decisions, checker coverage and review result. The next step is
`implement-spec`; the agent decides execution mechanics.

## 5. Amendments and continuation

For a material contract change, return the same Spec to `draft`, increment its
revision, reread affected authority, resolve material decisions and update the
contract/checker mapping. Preserve historical Evaluation evidence and mark only
affected results stale. Repeat affected integrity and compatibility checks before
returning to `ready`. A distinct change after conclusion may receive a new Spec.

Evaluation preserves continuity: acceptance status, current code revision and
uncommitted scope, valid checker results, failures/blockers and the immediate
unfinished work. A continuing agent reads the Spec, Evaluation and actual diff,
confirms the record and chooses how to proceed. Do not reconstruct a phase ledger
or execution plan inside either artifact.
