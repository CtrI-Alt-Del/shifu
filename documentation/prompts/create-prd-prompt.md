---
name: create-prd
description: Create or revise a canonical Shifu module PRD in Confluence.
---

# Create or revise a PRD

Use only when the user explicitly requests a Confluence write. Otherwise PRDs
are read-only. Read repository authorities, the existing page in full through
Atlassian Shifu MCP, and relevant Jira context. Preserve the Portuguese PRD
structure and Shifu terminology.

Use stable `RP-*` for Requisitos de Produto and `JN-*` for Jornadas. Define
outcomes, actors, business/experience rules, dependencies, exclusions, errors,
and alternate journeys at product level. Never renumber existing IDs. Do not add
local `RF/CA/VM/EV/ACH/CI`, implementation details, tests, or delivery
checkboxes.

After writing, read the page back and verify title, parent, content, links, ID,
and version. Update `modules.md` only if its canonical URL changed. Report all
external mutations.

