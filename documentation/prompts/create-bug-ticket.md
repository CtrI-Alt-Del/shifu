---
name: create-bug-ticket
description: Create a Jira bug ticket from verified Shifu defect evidence.
---

# Create a Jira bug ticket

When explicitly requested, check Jira for duplicates and create a `SHI-*` bug
with impact, environment, reproduction, expected/actual behavior, evidence,
severity, module, and delivery route. Link the canonical PRD and real `RP-*`,
Spec/`RF-*/CA-*`, and PR where available.

Do not mutate the PRD or assert missing delivery without evidence. Read the new
issue back and report its key and URL.

## Grilling protocol

Before drafting the issue, build a design tree of the decisions that determine
its scope. Work the tree in rounds:

- The frontier is every decision whose prerequisites are already settled.
- Ask the whole frontier in one round, numbering each question and giving a
  recommended answer.
- Return questions as normal plain chat text. Do not wrap the round in a code
  fence and do not emit Markdown syntax in the questions. Use this format:

  ❓ Q1 — <question title>: <question body, including choices when useful>

  ➡️ Recommended: <recommended answer>

  ---

  ❓ Q2 — <question title>: <question body>

  ➡️ Recommended: <recommended answer>

- Wait for the user's answers before recomputing the next frontier.
- Research repository and Jira facts directly; do not ask the user for facts
  that can be inspected. Keep decisions with the user.
- Fetch and present valid Jira options for decisions such as sprint and
  assignee. Never invent or silently select an option.
- Challenge contradictions, record resolved decisions, and do not silently
  assume material scope, ownership, permissions, dependencies, or exclusions.
- When the frontier is empty, present the shared understanding and ask for
  explicit confirmation.
- Do not draft or publish the issue until the user confirms the shared
  understanding.

After that confirmation, render and show the complete Jira draft, including
summary, project, issue type, sprint, assignee, description, fields, and links.
Ask for explicit approval of that exact draft. Do not create or update Jira
until the user approves it. After approval, publish the issue, read it back,
and report any difference from the approved draft.
