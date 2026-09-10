---
name: commit-code
description: Create scoped Conventional Commits for validated Shifu changes.
---

# Commit code

Read `documentation/rules/commit-rules.md`; inspect status, staged/unstaged
diffs, recent messages, and relevant Spec/Evaluation. Preserve unrelated work.
Never broadly stage, reset, checkout, stash, amend, rebase, push, or bypass hooks
without explicit authorization.

Group by coherent intent and stage exact paths/hunks. Use enforced Conventional
Commits with suitable scopes such as `web`, `server`, or `core`. Include the
relevant `SHI-*` key in body/footer. Run applicable validation first.

After each commit, verify status and report hash, message, files, validation, and
excluded changes. Do not push unless requested.

