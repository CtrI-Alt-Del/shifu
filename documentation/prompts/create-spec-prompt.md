---
name: create-spec
description: Create or revise a bounded Shifu Spec with product contracts and concrete acceptance checkers.
---

# Create or revise a Shifu feature Spec

Act as the SDD Orchestrator. Translate a known version of canonical product
requirements into one bounded, testable implementation contract. The agent
handles execution order, decomposition and delegation. Do not create `plan.md`
or put a task breakdown, exact internal file tree or execution ledger in the Spec.

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

## 2. Resolve material ambiguity

Ask the user only about unresolved product decisions or consequential tradeoffs
that existing authority and authorization do not settle. Actors, permissions,
business outcomes, destructive behavior, public compatibility and irreversible
persistence choices need explicit resolution when ambiguous. Ordinary reversible
implementation choices belong to the agent.

When questions depend on one another, ask the currently answerable decisions in
one conversational round. Include evidence, materially different choices, a
recommendation and its consequence. Follow the repository's grilling protocol
without a question tool. Record accepted decisions concisely in the Spec; do not
add an interview transcript. Partial answers do not approve other recommendations.

Proceed when material choices are already settled. Do not request another generic
confirmation of established authority or an already authorized contract. If the
user explicitly requests approval of every technical decision, honor that request.

A screenshot is visual evidence, not authority for a new permission, action or
workflow. Resolve material behavior inferred from it before including that behavior.
Visual treatment consistent with the PRD and UI rules may be decided directly.

A product amendment is a distinct external action: present the required amendment,
obtain explicit authorization to update Confluence, perform that update through the
applicable workflow and reread the complete page before reconciling the Spec.

## 3. Author the contract

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

Keep five sections: Context and scope; Implementation Contract; Technical
Contract; Validation Contract; Documentation alignment and revision history.
State each fact once and reference its identifier elsewhere. Create `evaluation.md`
at implementation kickoff, not during Spec authoring. Save feature-local design
references only when needed for the contract. No separate planning artifact exists.

### Context and scope

State the desired outcome, current behavior, owning module, source/mode,
canonical authority metadata, included behavior and explicit exclusions.
Classify selected product outcomes as `full`, `partial` or `deferred` for the
bounded delivery slice without weakening their canonical meaning.

Use stable Shifu identifiers: canonical `RP-*` and `JN-*`; local `RF-*`, `CA-*`,
`VM-*`, `EV-*`, `ACH-*` and `CI-*`. Never invent or renumber canonical IDs or
write local IDs into the PRD. Product dependency graphs describe capability and
authoritative facts; they do not prescribe implementation order.

### Implementation Contract

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
Required references must be available before `ready`, or carry an explicitly
accepted visual assumption. Negative, loading, error and recovery behavior belongs
in automated acceptance coverage; it does not create additional manual journeys.

### Technical Contract

Record the consequential constraints needed to preserve product and architectural
intent: owning modules and entry points, public APIs/events/ports, auth and account
propagation, transaction ownership, persistence compatibility, migrations,
side-effect timing, concurrency/idempotency and failure ownership where affected.
For cross-boundary payloads, describe the canonical shape and producer/consumer
responsibilities once. Specify complete boundary schemas when compatibility or
persistence depends on their fields. Define irreversible choices and accepted
tradeoffs with their rationale.

Reference existing module paths, public declarations, reusable patterns and any
prohibited boundaries needed to establish ownership. Generated artifacts identify
the source and real generation command. Public route groups require matching
non-secret `apps/server/rest-client/<module>/<route-group>.rest` requests.

Do not enumerate every internal file, widget, hook, helper, method or build task.
The agent selects internal decomposition, reuse, wiring and execution order under
the selected Rules. A widget hierarchy or flow diagram is useful only when it
clarifies an externally meaningful contract; an exact internal tree is not a
readiness requirement. Core remains independent of infrastructure; business
rules remain in their owning module.

### Validation Contract

Map every `CA-*` to a concrete automated checker and/or required manual proof.
Use existing test boundaries and commands from current manifests and Tooling.
Planned test paths may be named within permitted owning boundaries; do not present
an unimplemented command as executable. Keep unit/component, real integration,
mocked transport and manual evidence distinct.

```md
| Checker | Acceptance coverage | Boundary and observable proof | Command / procedure | Timing |
| --- | --- | --- | --- | --- |
| CI-01 | CA-01 | <focused unit/component assertions> | <real command and working directory> | During build |
| CI-02 | CA-02 | <real application, persistence or job boundary> | <real integration command and working directory> | After integration |
| VM-01 | CA-03 | <representative required happy path> | <Playwright CLI journey and reference> | Integrated candidate |
```

Respect the selected Rules' test-integrity policy: a forbidden test path or direct
coverage of an indirect/excluded source is a blocking contract defect. Cover such
behavior through its allowed consumer boundary. Do not invent arbitrary coverage
percentages or repository-wide quality commands. A skipped, mocked or unavailable
checker cannot be recorded as a passing real integration check.

Define focused unit/component and static checks for development. **Run integration
suites only after all implementation streams are integrated.** If they fail, fix
the failures and rerun until every applicable integration suite passes. Assign one
owner to that loop. Reviewers and conclusion consume passing evidence rather than
starting another integration run. Subsequent changes reopen only the checks whose
behavior or dependencies may be affected; unchanged evidence remains valid.

Required manual scenarios are concise happy paths. For each `VM-*`, identify
services/health prerequisites, fixture/account, starting route, actions, observable
result, final URL, relevant requests and persisted effect, console inspection,
cleanup and evidence target. For UI include required keyboard/focus and narrow
viewport behavior plus fresh post-change screenshots against the saved references.
Use repository Playwright CLI commands. Mocked transport cannot prove a real
authenticated or persisted flow. Negative cases, failures, recovery and concurrency
are verified with automated tests.

### Documentation alignment and revision history

List applicable Rule Pack paths and only documentation changes or confirmations
needed to keep the authorities aligned. Record material contract revisions and
their reasons. Actual code progress, checker results and review findings belong in
Evaluation, not the Spec.

## 4. Review and readiness

Perform a distinct Spec compatibility pass before `ready`. Use one independent
[`Spec Reviewer`](../agents/spec-reviewer-agent.md) for a `complete` Spec and any
compact Spec with material architecture, module, dependency, generated-artifact
or Rule risk. A low-risk compact Spec may use a distinct Orchestrator pass.
Material amendments repeat the affected review at their risk level.

Give the reviewer the exact revision, relevant authorities, owning boundaries,
public contracts, test-integrity policy, accepted assumptions and known risks.
The reviewer is read-only and checks architecture and Rules; it does not choose
product behavior or require runtime proof before implementation. Verify findings,
correct accepted defects and recheck affected findings with the same reviewer.

Before `ready`, confirm authority/version metadata; scope and traceability;
observable criteria; consequential boundary guarantees; available required design
references; permitted test boundaries; real checker commands; documentation links;
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
