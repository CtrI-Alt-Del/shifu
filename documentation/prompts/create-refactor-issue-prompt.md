---
name: create-refactor-issue
description: Create a Jira task for behavior-preserving Shifu refactoring.
---

# Create a refactor issue

When explicitly requested, verify the problem, check Jira duplicates, and create
a `SHI-*` task describing affected paths, maintenance impact, preserved
behavior, scope/exclusions, compatibility risks, and validation. Reference
architecture/rules and link PRD/Spec only for traceability.

If observable behavior, public contracts, persistence semantics, or module
ownership changes, route through feature SDD rather than refactor. Read the
issue back and report its key and URL.

