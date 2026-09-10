---
name: implement-spec
description: Implement a ready Shifu Spec and maintain Evaluation evidence.
---

# Implement a Spec

Act as Orchestrator, keeping Builder and reviewer passes distinct. Read the Spec,
optional Plan, Evaluation, authority preflight, and selected Rules. Re-read the
complete PRD and verify content ID/version. If its contract changed, mark the
Spec `stale` or `draft` and stop.

Before code changes, create/reconcile colocated `evaluation.md` from its
template, set `in_progress`, establish the baseline, and map work to
`RF-*/CA-*`.

The Builder edits only approved code/tests, follows module and widget structure,
runs focused then broader applicable checks, records exact results as `EV-*`,
and escalates ambiguity instead of changing the contract. The Orchestrator maps
every criterion, `VM-*`, and review problem (`ACH-*`) without erasing failed
attempts or substituting mocks for runtime evidence. Use only commands actually
present in Shifu.

Run an independent Implementation Reviewer pass. Resolve findings and rerun
invalidated evidence. When all criteria have current evidence, set Spec to
`implemented` and Evaluation to `ready`. Do not mutate Confluence or complete
the artifacts; conclusion owns that.

