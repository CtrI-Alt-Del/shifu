---
title: <feature title>
status: draft
revision: 1
source:
  type: <prd|issue|report|direct-request>
  ref: <actual source reference>
scope:
  - <owning module or boundary>
last_updated_at: YYYY-MM-DD
---

# Objective

State the problem and intended outcome; baseline only when useful. Name compact
or complete mode. Keep compact Specs concise across all seven sections; add only
detail warranted by the changed contracts and risks.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| <capability and actor> | <bounded delivery> | <adjacent behavior> |

Classify selected RP outcomes as full, partial or deferred without weakening the
PRD. Link the design handoff/manifest for affected UI states and viewports.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | <actual RP and relevant JN> | <actors, permissions, invariants, bounds and transitions> |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | <precondition> | <action> | <observable result> | CI-01 / VM-01 |

Cover applicable isolation, persistence, failures, recovery, concurrency and accessibility.

# Technical Contract

## Architecture Mapping

Owner: <module>. Rules: <applicable Rule Pack links>.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create / Modify / Delete | <affected Shifu layer> | <symbol and consequential repository-relative path> | <resulting declaration, consumers, exports and registration> |

Include expected Python/TypeScript declarations for changed public objects,
ports, use-case signatures and schemas. Creates show complete public declarations;
modifies show the result or explicitly scoped excerpts; deletes account for
consumers and compatibility. Define affected REST contracts and `.rest` examples,
SQLAlchemy/Alembic constraints and migration/data guarantees, widget props/state
ownership, provider wiring, and event/job payloads, retries and idempotency.

Reference existing unchanged declarations; specify only changed public contracts
and consequential guarantees. Add a scoped expected file tree only when it
clarifies ownership, registration, generated outputs or another consequential
boundary; otherwise the mapping suffices. Use new `[N]` and modified `[M]` files;
keep deletions in the mapping. Identify generated inputs/commands and planned
paths honestly. Private helpers and ordinary decomposition remain implementation
choices; changing them alone does not amend the contract.

## Runtime Flow

Explain affected runtime interactions; use Mermaid when useful. Include trusted
actor/context, validation, domain decisions, transactions, persistence, effects,
cache/visible results and relevant rejection, concurrency and recovery guarantees.

# Verification Contract

## Shared setup

Define source-backed environment/readiness, actors/authentication, data/initial
state, isolation/reruns, recovery and cleanup once for checks sharing them.
Reference actual fixture/account source paths and Tooling procedures. Resolve
credentials privately. Distinguish real, mocked and disposable dependencies;
never assume registration, account state or permission to reset shared data.

## Automated

### CI-01 — <trigger/input and observable outcome>

**Criteria:** CA-01

**Expected result:** <observable outcome, including absent effects for rejection>

**Setup / inputs:** <shared setup; finite combinations or equivalence classes/bounds>

**Proof:** <exact repository-relative test file and test boundary; planned if absent>

```bash
<actual focused command, working directory and verified selector>
```

**Passing condition:** <assertions, intended selection and evidence limits>

### CI-02 — Applicable baseline checks

**Scope:** <affected apps/packages and consumers>

**Checks:** <required Tooling/Rule checks; feature-specific exceptions>

Define separately identified `CI-*` quality checks for types, lint and complexity
on affected paths/projects and their consumers. Add a separately identified local
changed-code coverage check for affected production paths. Coverage requires
85% changed statements/functions/lines and 80% changed branches per eligible
Web/Server file under [Tooling](../../tooling.md#changed-code-coverage). Name
related tests and record Not applicable when no eligible production file changes.
Link [Tooling](../../tooling.md#scoped-type-lint-and-complexity-checks); specify actual
commands and pass conditions. Configured complexity lint may share its command
with lint but needs an explicit disposition. Record a required unavailable metrics
checker as Blocked; do not invent a command or infer a complexity score.

**Passing condition:** <required gates pass, static dispositions have actual proof,
and intended tests actually execute>

For correctness-critical Server changes, assess targeted mutation testing against a
concrete risk: required or not required, rationale, and the assertions addressing
that risk. When required, specify scope, verified runner, pass condition and
surviving-mutant disposition. Unavailable required execution is Blocked; ordinary
coverage cannot substitute and runner availability alone does not settle necessity.
Web has no mutation runner; record Web mutation checks as Not applicable and
verify correctness through applicable unit/component, browser and static checks.
During implementation, target only production Server `core/use_cases/**` files created or
modified by this Spec, with explicit application-relative `--files` paths under
[Tooling's mutation policy](../../tooling.md#mutation-testing). Select only related
use-case tests under `tests/<module>/core/use_cases/**` or legacy
`tests/core/**/use_cases/**`; core mutation runs require no Docker or containers. Whole-package, other-layer and
`--all` execution require a separate explicit user request. With no eligible
Server use-case changes, record Not applicable and its rationale; reconcile existing
required checks before changing their disposition. Record targets, command, elapsed time
and mutant outcomes in Evaluation.

## Manual

### VM-01 — <concise agent-executable happy path>

**Type:** Manual

**Criteria:** CA-01

**Tool / setup:** <Playwright CLI or terminal; shared setup and differences>

**Procedure:** <narrow ordered actions against the intended runtime boundary>

**Passing condition:** <URL, visible/persisted effects, requests, console,
keyboard/focus, required narrow viewport and cleanup as applicable>

## Visual

### VM-02 — <surface, state and viewport>

**Type:** Visual

**Criteria:** <CA IDs>

**Reference / setup:** <manifest entry, exact viewport, related Manual check>

**Capture / comparison:** <reuse current Manual capture where possible; inspect it>

**Passing condition:** <visual properties and accepted deviations>

VM IDs are unique across Manual and Visual checks. State why categories are
inapplicable; omit unused examples. Results belong in Evaluation. Integration
runs after all scopes are integrated using affected files/scenarios. Select tests
only for scoped changes and directly affected consumers. Broaden only for
demonstrated dependency impact or a concrete gap in that scope's proof, recording
why. Full local suites require scope spanning that suite or an explicit user request. Fix failures and rerun affected
checks. Review and conclusion reuse unaffected current proof.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| <canonical PRD URL/title/content ID/version/retrieval time> | <selected RP/JN> | <alignment or unchanged intent> | <external-write dependency> |
| <Rule or other authority> | <affected boundary> | <update or confirmation> | <recheck before conclusion> |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | YYYY-MM-DD | Initial contract | <delivery source and consequential decisions> |

Increment only for meaningful behavior, technical, design or verification changes.
Follow [SDD](../../sdd.md) and [Create Spec](../../prompts/create-spec-prompt.md).
