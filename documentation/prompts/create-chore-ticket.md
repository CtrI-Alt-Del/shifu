---
name: create-chore-ticket
description: Create a Shifu Jira Logical Task for technical, maintenance, or operational work outside the scope of a canonical PRD, including code changes when they do not implement product requirements.
---

# Create a Jira chore ticket

Use Atlassian Shifu MCP only when ticket creation is explicit. In the Shifu
Jira project, create a `Logical Task` for technical, maintenance, or operational
work that is not governed by a canonical PRD. The work may include application
code, but it must not implement or change product requirements, user journeys,
permissions, validation, or business rules owned by a PRD.

## Duplicate and scope checks

1. Describe the concrete technical or operational outcome: for example, shared
   UI infrastructure, a prototype, a technical design decision, a CI/CD or
   environment configuration, maintenance code, or technical documentation.
2. Verify whether a canonical PRD governs the requested outcome. If it does,
   stop this workflow and use `create-feat-ticket` instead. Do not use a
   `Logical Task` to bypass product traceability merely because the work also
   contains technical implementation.
3. Search Jira for an existing or equivalent `SHIFU` Logical Task before
   creating anything. If a matching ticket exists, report it instead of
   creating a duplicate.
4. Do not create a Story, Dev Task, Management Task, Epic, or child task as an
   implicit side effect.

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
  assignee. Never invent or silently select an option. List active and future
  sprints from the `SHIFU` board and include the backlog only when Jira permits
  the issue to remain outside a sprint. List users assignable to the ticket by
  their Jira display names; do not infer that a nickname belongs to a requested
  person.
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

## Ticket contract

Create a `Logical Task` with this shape:

```markdown
## 🎯 Objetivo

Descreva o que precisa ser produzido ou decidido.

## 📦 Entregável Esperado

Descreva o resultado verificável e onde ele será registrado
(por exemplo, código versionado, Pencil, wiki, ADR ou configuração).

## ✅ DoR Checklist

- [ ] Objetivo da tarefa descrito
- [ ] Entregável esperado definido
- [ ] Local de registro do entregável definido
- [ ] Campo Requisito preenchido somente quando houver uma referência aplicável
- [ ] Sprint selecionada
- [ ] Responsável atribuído
```

Set the Jira fields as follows:

- project: `SHIFU`;
- issue type: `Logical Task`;
- sprint: the sprint explicitly selected by the user;
- assignee: the assignable Jira account explicitly selected by the user;
- `Requisito` (`customfield_10452`): only when an applicable source URL is
  provided, such as a technical design or operational reference; do not
  require or invent a PRD, RF, or business-rules link;
- description: the ticket contract above, with the task objective, expected
  deliverable, destination, scope, dependencies, and validation evidence.

Keep product intent, user-facing acceptance criteria, and business rules in
the appropriate product artifacts. Use a `Dev Task` for code that implements
or changes a PRD-scoped product requirement. A `Logical Task` may include code
only when the outcome is not governed by a PRD and does not introduce product
requirements or business rules. Keep meetings, ceremonies, and slides in a
`Management Task`.

After creation, read the Jira ticket back and verify its issue type,
description, and `Requisito` value when one was supplied. Report the
`SHIFU-*` key and URL. Creating the ticket must not change product
requirements or local SDD delivery state.
