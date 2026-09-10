---
name: resolve-pr-feedback
description: Classify and route review feedback on a Shifu pull request.
---

# Resolve pull request feedback

Read the open PR/head, conversations, diff, Jira, Spec, Plan, Evaluation, Rules,
and canonical PRD version. Classify every action:

- explanation/metadata: respond without reopening SDD;
- implementation correction: reopen Evaluation, add `ACH-*`, resume
  `implement-spec`, then conclude;
- contract change: return Spec to `draft`, reconcile read-only Confluence
  authority, revise `RF/CA`, implement, and conclude;
- new scope: create a separate Jira issue and change Spec.

Do not resolve before evidence exists or change Confluence without explicit
authorization. After merge, use a bug/change Spec. Report each classification,
action, evidence, reply, and blocker.

