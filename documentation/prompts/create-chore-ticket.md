---
name: create-chore-ticket
description: Create a Shifu Jira Logical Task for non-code technical or operational work.
---

# Create a Jira chore ticket

Use Atlassian Shifu MCP only when ticket creation is explicit. In the Shifu
Jira project, create a `Logical Task` for work that does not involve writing
application code directly. A Logical Task is not a product-requirements,
PRD, or business-rules ticket.

## Duplicate and scope checks

1. Describe the concrete non-code outcome: for example, a prototype, a
   technical design decision, a CI/CD or environment configuration, or
   technical documentation.
2. Search Jira for an existing or equivalent `SHIFU` Logical Task before
   creating anything. If a matching ticket exists, report it instead of
   creating a duplicate.
3. Do not create a Story, Dev Task, Management Task, Epic, or child task as an
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
(por exemplo, Figma, wiki, ADR ou arquivo de configuração versionado).

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
the appropriate product artifacts. Keep implementation work that requires
writing application code in a `Dev Task`. Keep meetings, ceremonies, and
slides in a `Management Task`.

After creation, read the Jira ticket back and verify its issue type,
description, and `Requisito` value when one was supplied. Report the
`SHIFU-*` key and URL. Creating the ticket must not change product
requirements or local SDD delivery state.
