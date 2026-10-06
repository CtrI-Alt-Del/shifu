---
name: resolve-pr-feedback
description: Classify and route review feedback on a Shifu pull request.
---

# Resolve pull request feedback

Read the open PR/head, conversations, diff, Jira, Spec, Evaluation, Rules,
and canonical PRD version. Classify every action:

- explanation/metadata: respond without reopening SDD;
- implementation correction: reopen Evaluation, add `ACH-*`, resume
  `implement-spec`, then conclude;
- contract change: return Spec to `draft`, reconcile read-only Confluence
  authority, revise `RF/CA`, implement, and conclude;
- new scope: route to a separate change Spec; create a Jira issue only when the
  user explicitly requests that external action.

Preserve passing checks and reviews whose contract, covered code/dependencies,
fixtures and configuration are unchanged. Corrections reopen only affected
checks and findings; the designated verification runner fixes and reruns failed
or affected integration checks until all required checks pass. Reuse this evidence
for review, conclusion and publication instead of starting another full cycle.
Keep factual progress and blockers in Evaluation; no execution Plan is required.

Do not resolve before evidence exists or change Confluence without explicit
authorization. After merge, use a bug/change Spec. Report each classification,
action, evidence, reply, and blocker.

