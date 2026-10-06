---
description: Lean specification-driven development for Shifu contracts, autonomous implementation and verified delivery.
---

# Specification-driven development

Shifu uses SDD for changes to product behavior. Confluence owns product intent;
the repository Spec defines a bounded delivery contract against a known PRD
version. The agent organizes implementation and proves that contract using its
checkers. Evaluation records actual progress, evidence and delivery disposition.

```text
Spec → autonomous implementation → integrated verification
                                      ↑            ↓
                                      └── fixes ───┘
                                             ↓
                                         conclusion
```

## Applicability and authority

Create or revise a Spec when changing observable product behavior, domain rules,
public contracts, persistence semantics, cross-module events or user journeys.
Formatting, tooling upkeep, behavior-preserving refactoring and repairs covered
by an unchanged Spec may use direct maintenance. A discovered behavioral
choice requires contract reconciliation before the dependent work proceeds.

Before specifying a feature or implementing a contract in a fresh context:

1. read the nearest `AGENTS.md` files and this workflow;
2. resolve module ownership through [`modules.md`](modules.md) and system
   boundaries through [`architecture.md`](architecture.md);
3. use [`rules.md`](rules.md) to select and read the applicable Rule Pack;
4. inspect relevant manifests, tooling and infrastructure for actual commands;
5. read the complete canonical Confluence PRD through Atlassian Shifu MCP;
6. read applicable Jira, feature artifacts, designs and the user request.

Record the PRD URL, content ID, version, retrieval time and selected requirement
IDs in the Spec. Search excerpts cannot establish authority. Reuse complete
reads and repository facts already current in the same context; refresh affected
sources when scope expands, facts change or authority is uncertain. At conclusion,
verify source identity/version and reread changed content when reconciliation is
needed. A changed page version requires reconciliation; mark the Spec `stale`
until reconciled, and return it to `draft` if its contract changes.

| Module | Canonical PRD | Content ID |
| --- | --- | --- |
| Identity | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDyB) | `83001345` |
| Curriculum | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB) | `83034113` |
| Learning | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB) | `83066881` |
| Gamification | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AgDxB) | `82903042` |
| Intelligence | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQD0B) | `83099649` |

A Spec selects delivery scope and testable interpretations; it does not copy the
PRD or create a second product backlog. Report conflicting sources. User-visible
behavior, permissions and scope cannot be silently changed to fit existing code
or make a test pass. Jira and Confluence writes require an explicit external
action request and follow `AGENTS.md`.

## Durable artifacts

```text
documentation/features/<module>/<feature>/
├── spec.md                 # contract and checkers
├── evaluation.md           # evidence, findings and current handoff
└── design/                 # saved references when material
    ├── handoff.md           # or an existing Spec-approved manifest.md
    └── references/
```

Use lowercase kebab-case module/feature slugs and the
[Spec](templates/sdd/spec.md) and [Evaluation](templates/sdd/evaluation.md)
templates. A materially different delivery slice gets a feature directory;
a bounded revision may live under `changes/<change-slug>/` when preserving an
original concluded contract is useful.

There is no separate `plan.md` or `create-plan` step. The agent handles execution
order, decomposition, dependencies and delegation in its working context.
Existing execution ledgers are preserved under `history/legacy-execution.md`
for audit only. Their phases, task trees and statuses are historical; they do
not gate resumed delivery. Resume from the current Spec, Evaluation and diff.

## Contract and checkers

The Spec defines:

- problem, selected product requirements, actors, scope and exclusions;
- observable functional requirements and acceptance criteria;
- module ownership, public interfaces, persistent invariants and consequential
  or difficult-to-reverse technical decisions;
- applicable design references and required happy-path states/viewports;
- a proof for every acceptance criterion, with actual commands, test selectors,
  expected values, environments and evidence limits;
- applicable static, unit/component, integration and manual/visual checkers.

Specify constraints that affect correctness. Ordinary internal file placement,
helper names, widget decomposition, task lists and execution waves belong to the
implementer following repository conventions. A contract may name an existing
boundary or required artifact without prescribing every future internal file.
A routine reversible implementation choice does not require a Spec amendment.

Use stable Shifu identifiers:

| Prefix | Meaning | Owner |
| --- | --- | --- |
| `RP-*` | Requisito de Produto | Confluence PRD |
| `JN-*` | Jornada | Confluence PRD |
| `RF-*` | Requisito Funcional | Spec |
| `CA-*` | Critério de Aceitação | Spec |
| `VM-*` | Validação Manual | Spec/Evaluation |
| `EV-*` | Evidência | Evaluation |
| `ACH-*` | Achado de revisão | Evaluation |
| `CI-*` | Quality gate automatizado | Spec/Evaluation |

Every RF maps to at least one RP; relevant JN IDs supply journey context.
Every CA maps to RF and concrete proof. Enumerated states, statuses, bounds or
transitions need explicit coverage; a sampled case proves only its sample.
Never invent product IDs, renumber existing identifiers or weaken checks to
make implementation pass. State an explicit non-applicable disposition when
appropriate. A command's exit code must be accompanied by evidence that the
intended tests actually ran; an empty selection or skipped suite is not a pass.

## Roles and lifecycle

The Orchestrator owns the Spec, Evaluation, shared decisions, integration and
official evidence. It may implement directly or delegate genuinely independent
scopes to bounded Builders. Builders change assigned code/tests and report
results without changing acceptance obligations. Ordinary planning and
coordination choices need no separate user approval or durable task ledger.

A Spec Reviewer checks material architecture/module/Rule risks before `ready`;
that role returns only for a material contract amendment. An independent
Implementation Reviewer assesses the integrated diff and acceptance proofs.
For design-backed UI, launch the Visual Reviewer in parallel on the same
candidate using existing required captures; add no third mandatory serial
review. Findings require concrete evidence and a mapped correction.

| Artifact | States |
| --- | --- |
| Spec | `draft` → `ready` → `implemented` → `completed`; `stale` during source reconciliation |
| Evaluation | `in_progress` → `ready` → `completed` |

Implementation progress lives in Evaluation while the ready contract remains
stable. `implemented` means the candidate has current accepted evidence and is
ready for conclusion. A correction reopens Evaluation; a changed contract
returns the Spec to `draft` and increments its revision after reconciliation.
Only the Orchestrator changes artifact statuses. Completion requires every
applicable criterion and checker to have an accepted disposition.

## Implementation and verification

1. Establish the ready contract; ask only about unresolved consequential
   product or technical choices. Resolve facts and routine choices directly.
2. Create/reconcile Evaluation and its current handoff. Implement within the
   contract, using focused unit/component and static checks for feedback.
   Record material findings and meaningful checkpoints, not every edit.
3. Integrate all implementation scopes and generated artifacts. Perform any
   delivery-branch synchronization already authorized for conclusion before
   final integration validation. Preserve unrelated work and Git safety.
4. Run each applicable server, browser and job integration suite once against
   the integrated candidate, using the Spec's real commands and explicit
   CI-compatible fixtures. If a suite fails, fix the failures and rerun the
   failed and affected integration checks until every applicable suite passes.
   Required unavailable infrastructure remains a recorded blocker.
5. Execute required concise happy-path manual scenarios, capturing required
   visuals during those journeys. Automated tests cover negative, recovery,
   concurrency and unusual outcomes. Mocks cannot prove real authenticated,
   persisted or server-backed behavior. Stop task-started processes afterward.
6. Review code and required visuals independently in parallel. Reviewers use
   current checker results, inspect assertion coverage and identify missing
   evidence; they do not automatically start another integration run.
7. Fix in-contract findings autonomously. Rerun only invalidated checks and
   visual comparisons. Preserve passed evidence for unaffected behavior.
8. Conclude using accepted current evidence; do not repeat green suites merely
   because a role changes, a ledger is updated or conclusion starts.

A later implementation, fixture, configuration or source-contract change
reopens the checks whose claims/dependencies it affects. Record the changed
scope and retained evidence explicitly. A new commit hash alone does not
invalidate proof of unchanged behavior. Additional broad reruns need a concrete
integration risk, affected shared dependency or discovered coverage gap.

## Evaluation and continuation

Keep one acceptance/evidence matrix, findings and a small factual handoff in
`evaluation.md`. Record checker commands/results, relevant candidate commit or
worktree identity, environment/fixtures, evidence paths, covered CA IDs and
limitations. Preserve failed attempts and historical evidence.

The current handoff names the Spec revision, branch/candidate, completed and
unfinished criteria, interrupted or uncommitted work, latest checker results,
blockers and the next concrete action. A new agent reconciles it with Git and
the diff before choosing how to continue. Evaluation describes actual state;
it does not become a replacement phase/task plan.

At conclusion, reconcile every selected RP through RF/CA to evidence, close
blocking findings, verify source metadata and record delivery disposition as
`implemented`, `partially_implemented`, `not_implemented` or `not_applicable`.
Preserve incomplete or waived evidence honestly; an explicit user waiver is
never a pass. Link Jira/PR when available without changing canonical product
requirements. Branches and commits retain the repository Jira-key convention.

## Entry points

The [workflow prompt index](prompts/README.md) lists creation, implementation,
conclusion and feedback workflows. Prompts and generated skills inherit this
contract. Historical delivery records preserve their original facts; when
resuming, apply the current execution and evidence-reuse policy without
silently lowering product acceptance or required checker coverage.
