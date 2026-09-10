---
name: create-release-pr
description: Create a Shifu release pull request from main to production.
---

# Create a release pull request

Follow the branch strategy. Inspect remote state, open release PRs, and merged
deliveries since the last production release. Use `gh` only when explicitly
requested.

Create/update one PR from `main` to `production`. Summarize visible features,
fixes, migrations, operations, risks, rollback notes, and linked `SHI-*`
issues/PRs. Use only the established release/version mechanism.

Do not merge, tag, deploy, or delete branches without separate authorization.
Read the PR back and report URL, checks, approvals, and blockers.

