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

# Context and scope

State the outcome, current behavior, owning module, compact/complete mode,
included behavior and exclusions. Record canonical PRD URL/title/content ID,
version/retrieval time and applicable RP/JN IDs. Identify selected outcomes as
full, partial or deferred. Record material accepted decisions and assumptions.

# Implementation Contract

| ID | RP/JN coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | <actual RP and relevant JN> | <actors, rules, bounds and transitions> |

| ID | RF coverage | Given | When | Then | Proof |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | <precondition> | <action> | <observable result> | CI-01 |

Cover the applicable permissions, isolation, persistence, failures, recovery,
concurrency and accessibility guarantees. For design-backed UI, link the saved
handoff/manifest with required happy-path states, viewports and accepted deviations.

# Technical Contract

Define consequential owning boundaries, public payloads/interfaces/events,
authentication propagation, transaction ownership, persistent invariants,
migration compatibility and side-effect/failure ownership. Reference reusable
patterns and prohibited boundaries. Describe generated artifacts and real
generation commands when affected. Do not prescribe internal task or file trees.

# Validation Contract

| Checker | CA coverage | Boundary and observable proof | Command / procedure and working directory | Timing |
| --- | --- | --- | --- | --- |
| CI-01 | CA-01 | <unit/component assertions> | <installed command and selector> | During build |
| CI-02 | <CA IDs> | <real application/persistence/job assertions> | <installed integration command and selector> | After all scopes are integrated |
| VM-01 | <CA IDs> | <required happy path> | <Playwright CLI journey, services, fixture, observations and capture references> | Integrated candidate |

Give every CA concrete proof and distinguish real integration from mocked
transport. Specify expected values, intended test selection and evidence limits.
Automate negative, recovery, concurrency and unusual cases. Keep manual journeys
concise and include required UI keyboard/focus/narrow-viewport observations.

Run applicable integration suites once after all scopes are integrated. Fix
failures and rerun failed/affected checks until all applicable suites pass.
Review and conclusion reuse valid results. Later changes reopen affected proof.

# Documentation alignment and revision history

List selected Rule Pack paths and necessary authority/documentation alignment.
Record material contract revisions with their reasons. Keep actual progress and
checker results in Evaluation. Follow [SDD](../../sdd.md) and
[Create Spec](../../prompts/create-spec-prompt.md); omit irrelevant template rows.
