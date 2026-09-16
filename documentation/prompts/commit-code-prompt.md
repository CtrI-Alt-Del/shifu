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
Commits with suitable scopes such as `web`, `server`, or `core`. Start every
subject with the relevant Jira key in the strict `SHIFU-<number>` format, for
example `feat(core): SHIFU-71 model learning domain`. When extracting a key from
a branch name, match `\bSHIFU-\d+\b` case-insensitively and normalize it to
uppercase. Do not accept keys from another Jira project. Run applicable validation
first.

After each commit, verify status and report hash, message, files, validation, and
excluded changes. Do not push unless requested.
