---
name: resolve-pr-feedback
description: Classify and route review feedback on a Shifu pull request.
---

# Resolve pull request feedback

Read the open PR/head, conversations, diff, Jira, Spec, Evaluation, Rules,
and canonical PRD version. Classify every action:

- explanation/metadata: respond without reopening SDD;
- implementation correction: retain the Spec revision; reopen a completed,
  unmerged Spec to `ready`, set Evaluation `in_progress`, add `ACH-*`, mark affected
  checks Stale and update per-CA implementation/verification Progress. Resume
  `implement-spec`, then conclude and verify the current delivery PR head;
- contract change: return Spec to `draft`, reconcile complete Confluence authority
  without unauthorized writes, resolve decisions, increment revision for the
  adopted contract, update RF/CA/checks and repeat affected Spec review before
  `ready`. Implement, verify and conclude the existing delivery;
- new scope: route to a separate change Spec; create a Jira issue only when the
  user explicitly requests that external action.

Preserve passing checks and reviews whose contract, covered code/dependencies,
fixtures and configuration are unchanged. Corrections reopen only affected
checks and findings; the designated verification runner fixes and reruns failed
or affected integration checks until all required checks pass. Reuse this evidence
for review, conclusion and publication instead of starting another full cycle.
Keep factual progress and blockers in Evaluation; no execution Plan is required.

Record reusable lessons and their documentation action/no-change reason in Lessons
Learned; keep comment links, affected checks and verified resolutions in Findings.
Verify old-head feedback is actually superseded before classifying it stale.
Update Delivery with publication, current-head CI and blocking review state;
completion follows `conclude-spec`, not just a focused correction pass.

Do not resolve before evidence exists or change Confluence without explicit
authorization. After merge, use a bug/change Spec. Report each classification,
action, evidence, reply, and blocker.

