---
title: <feature title> evaluation
status: in_progress
spec: ./spec.md
spec_revision: <revision>
last_updated_at: YYYY-MM-DD
---

# Current handoff

- Spec revision and branch/candidate: <revision, commit and worktree identity>
- Completed and unfinished criteria: <CA IDs and factual state>
- Interrupted/uncommitted work: <actual paths, partial changes and safety facts>
- Current checker results: <valid EV IDs and stale/missing/failed proof>
- Blockers and unresolved decisions: <specific dependency or none>
- Next action: <immediate concrete unfinished action>

Reconcile this record with the actual diff on continuation. Keep it factual and
small; do not create phases, task trees or an execution plan here.

# Acceptance and evidence

| CA | RF coverage | Automated evidence | Manual/visual evidence | Status and limits |
| --- | --- | --- | --- | --- |
| CA-01 | RF-01 | <EV ID or pending> | <VM/EV IDs or not applicable> | <pending/passed/failed/blocked/waived with reason> |

# Evidence log

| EV | Checker / CA coverage | Candidate and relevant environment/fixtures | Exact command or procedure / working directory | Result, artifacts and limits |
| --- | --- | --- | --- | --- |
| EV-01 | <CI/VM and CA IDs> | <commit/worktree, configuration, fixtures> | <command, intended tests and actual count or runtime observations> | <observed result and artifact paths> |

Preserve failed attempts. Record evidence reuse and its unchanged covered scope;
invalidate only affected results when behavior, dependencies, fixtures,
configuration or the source contract changes. A skipped or unavailable checker
is not a pass. Integration runs after all implementation scopes are integrated;
fix and rerun failed/affected checks until all applicable suites pass.

# Findings and review

| ACH | Evidence and affected CA | Severity | Status / correction / verification |
| --- | --- | --- | --- |
| ACH-01 | <observed defect, reviewer, candidate and EV IDs> | <severity> | <open/resolved with evidence> |

Record independent implementation and applicable parallel visual review of the
same candidate. Reuse current proof; do not start another green integration run.

# Delivery disposition

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| <actual IDs> | <RF/CA IDs> | <EV IDs> | <implemented/partially_implemented/not_implemented/not_applicable> |

Record authorized publication links, applicable current-head CI, source-version
verification and required documentation alignment when concluding. Preserve
waivers and limitations honestly. Follow [SDD](../../sdd.md) and
[Conclude Spec](../../prompts/conclude-spec-prompt.md). Replace these template
instructions with actual delivery facts; no Plan is required.
