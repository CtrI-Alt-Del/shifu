---
name: conclude-spec
description: Verify a Shifu delivery and complete its local SDD artifacts.
---

# Conclude a Spec

Read the implemented Spec, optional Plan, ready Evaluation, integrated diff, and
PR/Jira context. Re-read the complete PRD and verify its content ID/version. If
relevant requirements changed, return the Spec to `draft` or `stale`.

Verify every `RF-*/CA-*`, run all applicable `CI-*`, verify required `VM-*`,
and resolve or explicitly accept every `ACH-*`. Record each selected `RP-*`
as `implemented`, `partially_implemented`, `not_implemented`, or
`not_applicable`; add Jira/branch/PR references; then complete Plan,
Evaluation, and Spec.

Disposition belongs in Evaluation. Do not add Confluence status or checkboxes
unless explicitly requested. A skipped, failing, stale, or unsupported gate
prevents completion and must be reported precisely.

