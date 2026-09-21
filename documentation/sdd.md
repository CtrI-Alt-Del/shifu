---
description: Canonical specification-driven development workflow for Shifu feature delivery.
---

# Specification-driven development

Shifu uses specification-driven development (SDD) for changes to product
behavior. Product requirements remain canonical in Confluence. The repository
stores the bounded implementation contract, execution decisions, evidence, and
delivery disposition needed to implement a known version of those requirements.

SDD does not copy an entire PRD into Git and does not make repository artifacts
a second product backlog.

## When SDD applies

Create or update a feature artifact set when work adds or changes observable
product behavior, domain rules, public contracts, persistence semantics,
cross-module events, or user journeys.

Direct maintenance is allowed for formatting, typo-only documentation changes,
dependency/tooling upkeep, mechanical refactors with no behavior change, and
repairs already covered by an unchanged Spec. If investigation reveals a
behavioral decision, stop and create or revise the Spec.

## Authority preflight

Before drafting a Spec or changing implementation, read in this order:

1. the nearest `AGENTS.md` files;
2. [`modules.md`](modules.md) for ownership and module boundaries;
3. [`architecture.md`](architecture.md);
4. [`rules.md`](rules.md) and every Rule Pack selected by its routing table;
5. relevant package manifests, development documentation, and infrastructure
   configuration for commands that actually exist;
6. the complete canonical Confluence PRD page through the Atlassian Shifu MCP;
7. relevant Jira issues, existing feature artifacts, designs, and the user request.

Do not infer requirements from a Confluence search excerpt. Record the page
content ID, page version, retrieval time, and cited requirement IDs in `spec.md`.
If the version changes before conclusion, reconcile the new page and return the
Spec to `draft` when the contract is affected.

## Product authorities

| Module | Canonical PRD | Content ID |
| --- | --- | --- |
| Identity | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDyB) | `83001345` |
| Curriculum | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB) | `83034113` |
| Learning | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB) | `83066881` |
| Gamification | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AgDxB) | `82903042` |
| Intelligence | [Confluence](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQD0B) | `83099649` |

Confluence owns product intent and requirement wording. A local Spec owns the
selected delivery slice and its testable interpretation. An Evaluation owns the
evidence and delivery disposition for that slice. Implementation and tests own
runtime behavior. Conflicts must be reported; they must not be silently resolved
by changing the PRD or acceptance contract.

External product documents are not mutated as a side effect of implementation.
Updating a PRD, adding delivery status to Confluence, or changing Jira requires
an explicit request and follows the Atlassian safety rules in `AGENTS.md`.

## Shifu artifact abbreviations

Keep the Portuguese identifiers already used by Shifu:

| Prefix | Meaning | Authority |
| --- | --- | --- |
| `RP-*` | Requisito de Produto | Confluence PRD |
| `JN-*` | Jornada | Confluence PRD |
| `RF-*` | Requisito Funcional | Local Spec |
| `CA-*` | Critério de Aceitação | Local Spec |
| `VM-*` | Validação Manual | Spec/Evaluation |
| `EV-*` | Evidência | Evaluation |
| `ACH-*` | Achado de revisão | Evaluation |
| `CI-*` | Quality gate automatizado | Spec/Evaluation |

Identifiers are stable. Never renumber an existing identifier to make a table
look contiguous. Every `RF-*` maps to at least one `RP-*`; relevant `JN-*` IDs
provide journey context. Every `CA-*` maps to one or more `RF-*`, and every
concluded criterion maps to `EV-*`, `VM-*`, or a documented automated check.

## Durable artifact layout

Use a lowercase kebab-case module and feature slug:

```text
documentation/features/<module>/<feature>/
├── spec.md
├── plan.md                 # optional execution ledger
├── evaluation.md
└── design/                 # only when visual references are material
    ├── manifest.md
    └── references/
```

Use the templates under [`templates/sdd`](templates/sdd). A materially different
delivery slice gets its own feature directory. A bounded revision may be kept
under `changes/<change-slug>/` inside the feature directory when preserving the
original concluded contract is useful.

## Roles and edit ownership

- **Orchestrator** performs the preflight, owns all SDD artifacts, resolves
  ambiguity, delegates implementation/review, records evidence, and concludes.
- **Builder** changes code and tests only within the approved Spec. It reports
  evidence and discrepancies but does not edit the acceptance contract.
- **Spec Reviewer** checks the Spec against the cited Confluence version,
  architecture, module boundaries, and rules before implementation.
- **Implementation Reviewer** checks code and evidence against each `CA-*` and
  records findings for the Orchestrator. It does not broaden scope.

One person or agent may perform several roles sequentially, but review must
remain a distinct pass. Only the Orchestrator changes artifact status.

## Artifact states

- `spec.md`: `draft` → `ready` → `implemented` → `completed`; `stale` is used
  when its source version changed and reconciliation is pending.
- `plan.md`: `draft` → `in_progress` → `completed`.
- `evaluation.md`: `in_progress` → `ready` → `completed`.

`implemented` means implementation is available for final review, not that the
feature is delivered. `completed` requires accepted evidence and successful
applicable quality gates.

`open` is not a Spec artifact status. After Spec creation, the Orchestrator keeps the
artifact `draft` through authority, integrity, and independent Spec review, then changes
it to `ready` when those gates pass. Explicit implementation dependencies may be recorded
in a ready Spec; they block only the affected execution or integration step unless they
leave the implementation contract materially ambiguous.

## Workflow

The reusable entry-point instructions are indexed in
[`prompts/README.md`](prompts/README.md). Each prompt inherits this document and
cannot override its authority, ownership, or external-write rules.

### 1. Create the Spec

Create `spec.md` from the template. Select explicit `RP-*` and `JN-*` IDs, define
scope and exclusions, translate the slice into `RF-*` and observable `CA-*`, and
list real validation commands. A criterion must be decidable from evidence.
Mark the Spec `ready` only after the authority and testability review passes.

### 2. Plan only when useful

Use `plan.md` for multi-layer, cross-module, migration-heavy, or coordination-
heavy work. It is an execution ledger, not a place to invent requirements.
Record dependencies, sequence, ownership, risks, and checks by `RF-*`/`CA-*`.

### 3. Implement the approved contract

The Builder follows the selected Rule Pack and changes only the approved scope.
Tests should name or otherwise trace to their criteria where practical. New
ambiguity, conflicting authority, or a required scope expansion returns to the
Orchestrator; it is not silently solved in code.

### 4. Evaluate independently

Create `evaluation.md` at implementation start. Maintain an acceptance matrix
covering every `CA-*`, with commands, results, manual checks, and evidence. Record
review findings as `ACH-*` with severity, status, and resolution evidence.

### 5. Conclude

The Orchestrator:

1. confirms the Confluence content ID and page version still match the Spec;
2. confirms every `RF-*` and `CA-*` has an accepted disposition and evidence;
3. runs all applicable `CI-*` gates using commands present in the repository;
4. resolves or explicitly accepts all findings;
5. records the final delivery disposition in `evaluation.md`;
6. marks the artifacts `completed` and links the Jira issue/PR when available.

Use `implemented`, `partially_implemented`, `not_implemented`, or `not_applicable`
for each selected `RP-*`. This local disposition is evidence about delivery; it
does not alter or reinterpret the canonical PRD.

Branches and commits continue to follow the repository convention and include
the relevant `SHI-*` Jira key. SDD artifact IDs complement Jira; they do not
replace it.
