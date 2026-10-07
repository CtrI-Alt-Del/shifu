---
title: <feature title> evaluation
status: in_progress
spec: ./spec.md
last_updated_at: YYYY-MM-DD
---

# Current State

| Field | State |
| --- | --- |
| Implementation | <pending/partial/complete; affected criteria> |
| Automated checks | <passed/required count; failed, blocked or stale checks> |
| Type / lint / complexity | <separate statuses and CI/EV references; scope and unavailable-tooling limits> |
| Manual checks | <passed/required count; outstanding journeys> |
| Visual checks | <passed/required count; outstanding comparisons or Not applicable> |
| Independent review | <pending/current/affected recheck; report reference> |
| Blockers | <specific finding/check IDs or none> |
| Candidate | <branch, relevant commit, worktree and evaluated dirty scope> |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Pending | Pending | CI-01 / VM-01; EV references | <concrete unmet obligation> |

One row per criterion. Implementation: Pending, Partial, Complete. Verification:
Pending, Partial, Passed, Failed, Blocked, Stale. Code completion is not verified
acceptance. Reconcile against the current Spec and actual diff on resume.

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01 | Pending | <candidate/date/configuration/fixture> | <command and selection> | <actual test count, result, artifacts> |
| EV-02 | VM-01 / Manual / CA-01 | Pending | <candidate/date/runtime/actor> | <CLI/terminal procedure> | <expected vs observed URL/content/persistence/network/console> |
| EV-03 | VM-02 / Visual / CA-01 | Pending | <candidate/date/state/viewport> | <capture and image inspection> | <reference/capture paths, differences and deviations> |

Record exact scoped files/scenarios, actual test counts and command wall time;
keep unit, REST/persistence, real-job and browser results distinct.
Statuses: Pending, Passed, Failed, Blocked, Stale, Not applicable. Include applicable
baseline gates even without a CA. Give type, lint and complexity separate result
entries; a shared lint/complexity command may reuse an EV reference with its
actual scope/limits. Missing required metrics tooling is Blocked; configured
complexity lint is not a quantitative score. Preserve failed/interrupted attempts and history;
materially different results get new EV IDs. Explain retained proof; invalidate
only affected claims/dependencies. Focused corrections do not rewrite a historical
full-suite failure or coverage measurement. Waivers are limitations, never passes.
Do not duplicate spec_revision metadata; identify the evaluated contract revision
in result details where material.

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | <observed defect, authority, reviewer and candidate> | <severity> | <CI/VM IDs and EV references> | <Open/Resolved; correction and proof> |

Record independent implementation and applicable parallel visual review of the
same candidate. Reports inform the Orchestrator's official verdict.

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| <reusable guidance> | <ACH/EV/source> | <updated authority, pending proposal or reason no change is needed> |

State none when no reusable lesson exists. Keep feature-specific details local.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | <branch, commit, worktree and relevant dirty scope> |
| Completed | <implemented criteria and valid verification/review references> |
| Unfinished | <criteria, failed/blocked/stale checks and open findings> |
| Uncommitted work | <exact paths, purpose, ownership and unrelated work to preserve> |
| Active processes | <task-started session/PID, command, port, state/cleanup or none> |
| Blockers | <actual decision/service/tool unavailable after diagnosis or none> |
| Next action | <immediate concrete continuation action> |

Refresh meaningful checkpoints and before interruption. Keep factual state rather
than phases/task trees. Handoff does not replace actionable authorized work.

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| <actual IDs> | <RF/CA IDs> | <EV IDs> | <implemented/partially_implemented/not_implemented/not_applicable> |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| <authorized delivery PR URL> | <actual checked head> | <Pending/Passed/Failed; blocking conversations> | <applicable run URLs/results> |

| Field | Result |
| --- | --- |
| Publication | <not requested/local-only/published/blocked; actual state> |
| Source verification | <canonical identity/version; reconciliation if changed> |
| Documentation Alignment | <each required update/confirmation and disposition> |
| Revision History | <material amendments in Spec or no contract change> |
| Limitations | <waivers, partial scope, outstanding obligations or none> |

Populate PR rows only when applicable; preserve superseded heads and failed runs.
Published delivery completes after required current-head CI and blocking review
conversations are resolved. Local closure records publication/CI as not requested
or not applicable, with its reason. Follow [SDD](../../sdd.md) and
[Conclude Spec](../../prompts/conclude-spec-prompt.md).
