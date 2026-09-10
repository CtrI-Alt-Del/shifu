---
name: create-spec
description: Create or revise a Shifu feature Spec from canonical Confluence requirements.
---

# Create a feature Spec

Act as SDD Orchestrator. Perform the authority preflight in
`documentation/sdd.md` and read the selected Rule Pack. Resolve the owning
module, then read the complete canonical PRD through Atlassian Shifu MCP. Search
snippets are insufficient. Record URL, content ID, version, retrieval timestamp,
selected `RP-*`, and relevant `JN-*`. If unavailable, do not mark the Spec
`ready`.

Create `documentation/features/<module>/<feature>/spec.md` from the canonical
template.

- Define bounded scope and exclusions.
- Derive stable `RF-*` from real `RP-*`, then observable `CA-*`.
- Add applicable `VM-*` and real `CI-*` commands found in the repository.
- Record module, contract, persistence, security, privacy, accessibility,
  observability, and design constraints.
- Never invent PRD IDs, copy the whole PRD, or mutate Confluence.
- Keep implementation algorithms out of behavioral criteria.

Perform a separate Spec Reviewer pass for version fidelity, traceability,
testability, contradictions, and Rule compliance. Resolve findings in revision
history. Set `ready` only when no material ambiguity remains; otherwise retain
`draft` or `stale` and report the blocker.

