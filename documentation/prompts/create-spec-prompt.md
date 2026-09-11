---
name: create-spec
description: Create or revise a Shifu feature Spec from canonical Confluence requirements.
---

# Create a feature Spec

Act as SDD Orchestrator. Perform the authority preflight in
`documentation/sdd.md` and read the selected Rule Pack. Resolve the owning
module, then read the complete canonical PRD through Atlassian Shifu MCP. Search
snippets are insufficient. Record URL, content ID, version, retrieval timestamp,
selected `RP-*`, and relevant `JN-*`. If unavailable, do not mark the Spec
`ready`.

Create `documentation/features/<module>/<feature>/spec.md` from the canonical
template.

- Define bounded scope and exclusions.
- Derive stable `RF-*` from real `RP-*`, then observable `CA-*`.
- Add applicable `VM-*` and real `CI-*` commands found in the repository.
- Record module, contract, persistence, security, privacy, accessibility,
  observability, and design constraints.
- Never invent PRD IDs, copy the whole PRD, or mutate Confluence.
- Keep implementation algorithms out of behavioral criteria.

## Exhaustive questionnaire mode

When the user asks to decide, question, or approve **every technical decision**, make the
questionnaire exhaustive rather than collapsing several decisions into a generic architecture
choice. Research first, then continue dependency-ordered rounds until every consequential
implementation-shaping alternative is settled. Keep one monotonically increasing question
sequence across rounds, ask the whole currently-unblocked frontier in each round, and maintain a
decision ledger that records accepted recommendations, explicit alternatives, contradictions,
dependencies, and assumptions. Wait for the user's answers before recomputing the next frontier.

Cover each applicable branch below:

- owning module, application, layer, declaration, and composition boundary;
- technology, protocol, dependency, and provider/client abstraction;
- API route, method, authentication, authorization lifetime, payload, serialization, validation,
  versioning, and compatibility;
- source of truth, transaction/commit boundary, persistence model, migration generation,
  indexing, tenancy, and historical-value behavior;
- synchronous/asynchronous flow, publication timing, delivery guarantee, idempotency,
  deduplication, ordering, concurrency, buffering, backpressure, and capacity limits;
- connection/subscription lifecycle, retries, timeouts, heartbeat, reconnect, offline/hidden
  behavior, replay, and cleanup;
- multi-process, multi-tab, multi-device, or multi-tenant coordination and degraded fallbacks;
- UI state ownership, component/widget boundaries, interaction semantics, exact copy/timing,
  focus, keyboard, announcement, responsive behavior, stacking, and design-reference gaps;
- error translation, user-visible failure behavior, observability, privacy, and secret handling;
- automated test ownership, indirect versus direct boundaries, manual fixtures/services,
  viewports, screenshots, and evidence targets.

Ask about exact operational values when they affect the Contract—for example duration, retry
schedule, heartbeat interval, connection cap, queue size, viewport, or concurrency limit. Continue
from broad prerequisites to their dependent concrete choices: selecting SSE, for example, may
unlock route, authentication, payload, heartbeat, reconnection, authorization-lifetime,
backpressure, and browser-ownership decisions.

Exhaustive does not mean asking the user to restate repository facts or approve conventions with
only one legal answer. Resolve those directly from authority and include them in the final shared
understanding. Do not ask about incidental implementation syntax or algorithms that cannot alter
observable behavior, architecture, ownership, operability, security, validation, or the Builder's
Contract.

Before declaring the frontier empty in exhaustive mode:

1. replay the decision ledger against every affected runtime boundary and Rule-selected layer;
2. inspect the chosen combination for newly exposed decisions and contradictions;
3. state any authority correction or design artifact required before authoring;
4. present one consolidated shared-understanding summary containing the resolved product,
   technical, design, and validation decisions; and
5. request explicit confirmation. A typo-tolerant unambiguous confirmation such as `confirmed`
   or `comfirmed` passes this final gate.

Do not create or modify the Spec before that confirmation. After confirmation, apply approved
authority changes first, create the artifacts, run integrity checks, and perform the independent
Spec review. If authoring or review exposes a genuinely material unasked choice, return to the
questionnaire with the next question number; otherwise resolve repository-fixed compatibility
corrections directly and resume the same Reviewer.

| Area | Clarify when unresolved |
| --- | --- |
| Product | Actors, permissions, success/rejection behavior, states, scope, and deferrals. |
| Technical | Ownership, technologies, dependencies, APIs, transactions, concurrency, failure semantics, integrations, and runtime constraints. |
| Design | Authoritative frames/states, responsive behavior, missing references, and allowed deviations. |
| Validation | Automated boundaries, manual flows, services, accounts/data, viewports, and evidence. |

Perform a separate Spec Reviewer pass for version fidelity, traceability,
testability, contradictions, and Rule compliance. Resolve findings in revision
history. Set `ready` only when no material ambiguity remains; otherwise retain
`draft` or `stale` and report the blocker.
