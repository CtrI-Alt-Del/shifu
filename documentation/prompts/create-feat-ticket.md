---
name: create-feat-ticket
description: Create a Shifu Jira feature-delivery ticket traced to the canonical PRD.
---

# Create a Jira feature ticket

When explicitly requested, create a `SHIFU` Jira `Story` or `Task` for
application-code feature delivery derived from a canonical PRD. The PRD is the
defining source of a feature ticket. This is not a Logical Task, bug,
refactor-only, management, PRD-authoring, or business-rules ticket.

## Authority and scope checks

1. Describe the concrete feature outcome and code delivery boundary.
2. Resolve the owning module and read the complete canonical Confluence PRD
   through Atlassian Shifu MCP. Record its exact page URL, content ID/version
   when available, and real `RP-*`/`JN-*` identifiers. The exact page URL is
   required for Jira's `Requisito` field. Search excerpts are insufficient.
3. Do not copy the PRD into Jira or invent requirement identifiers.
4. If no applicable canonical PRD page URL exists, do not silently create a
   feature ticket; explain that PRD/product-authority work is needed or route
   the work to the appropriate non-feature workflow.
5. Search Jira for an equivalent `SHIFU` Story or Task matching the PRD/feature
   first. Report a match instead of creating a duplicate. A product-facing
   Story and a technical Dev Task are not duplicates merely because they cover
   the same feature outcome when the Dev Task has a concrete code-delivery
   boundary and is explicitly linked as blocking the Story. In that case,
   preserve the Story as the user-outcome authority and create the Dev Task as
   its implementation dependency.
6. Do not create a Logical Task, Bug, Refactor ticket, Management Task, Epic,
   or child task as an implicit side effect.

## Grilling protocol

Before drafting the issue, build a dependency-ordered design tree. Ask the
whole currently unblocked frontier in each round, number questions
monotonically, recommend an answer for each, and wait for the user's answers
before recomputing the next frontier. Research repository, complete PRD, and
Jira facts directly; do not ask the user for inspectable facts.

Ask questions in normal plain chat text using this exact shape:

❓ Q1 — <question title>: <question body>

➡️ Recommended: <recommended answer>

---

Do not silently assume scope, ownership, permissions, dependencies, issue-link
direction, or exclusions. Fetch and present valid Jira options for issue type
and sprint. Fetch assignee options when the user wants the ticket assigned or
has not decided whether to assign it. The issue type must be a valid `Story` or
`Task` for `SHIFU`, explicitly selected by the user. Assignee is optional: the
user may explicitly choose to leave the ticket unassigned, in which case omit
the assignee field during creation. When a Dev Task implements an existing user
Story, link the issues using Jira's `blocks` relationship with the Dev Task as
the blocker and the Story as the blocked issue; do not represent this delivery
relationship as duplication.

When no decisions remain, present the shared understanding and ask for explicit
confirmation. Do not draft or publish before that confirmation.

Then show the complete draft—summary, project, issue type, sprint, assignee or
explicitly unassigned status, description, fields, PRD URL/IDs, and every
planned Jira issue link with its exact direction—and ask for explicit approval
of that exact draft. Only after approval create the issue, add the approved
Jira issue links, read the issue back, and report any difference.

## Ticket contract

Use this description structure:

```markdown
## 🎯 Objetivo

Descreva o resultado da funcionalidade conforme o PRD canônico.

## 📦 Escopo da Entrega

Descreva os módulos, contratos, jornadas e limites da mudança.

## ✅ Critérios de Aceitação

- Critério observável e verificável 1, rastreado ao PRD
- Critério observável e verificável 2, rastreado ao PRD

## 🧪 Validação

Descreva de forma concisa as categorias de testes, verificações manuais e
evidências esperadas. Não liste comandos de lint, typecheck, testes, geração ou
outras rotinas de CLI no ticket; os comandos executáveis pertencem à Spec,
ao plano e à avaliação da entrega.

## 🔗 Rastreabilidade

- PRD: <URL canônica, content ID/version, and RP/JN IDs>
- Jira: <issue relacionada, tipo do vínculo e direção, ou "N/A">

## 🚫 Fora de Escopo

Liste as exclusões e trabalhos posteriores.

## ✅ DoR Checklist

- [ ] PRD canônico e requisitos/jornadas aplicáveis identificados
- [ ] Campo `Requisito` preenchido com o link da página PRD no Confluence
- [ ] Objetivo descrito
- [ ] Escopo e exclusões definidos
- [ ] Critérios de aceitação verificáveis definidos
- [ ] Validação e evidências esperadas definidas
- [ ] Dependências Jira e direção dos vínculos definidas
- [ ] Sprint selecionada
- [ ] Responsável atribuído ou decisão explícita de deixar sem atribuição
```

Set `project=SHIFU`, the explicitly selected valid `Story` or `Task`, the
explicitly selected sprint, and, when requested, the explicitly selected
assignable account. Omit `assignee` when the user explicitly chooses to leave
the ticket unassigned.
Keep Jira validation outcome-oriented: name the relevant test boundaries and
manual evidence, but do not expand them into repository command lists.
Set `Requisito` (`customfield_10452`) as a required field containing the exact
URL of the canonical PRD page on Confluence. This field is the PRD-page link;
do not substitute a Spec, technical design, operational reference, or another
URL. Do not create the feature ticket without it.

After creation, verify issue type, description, sprint, assignee or unassigned
status, PRD URL/IDs, every approved Jira issue link and its direction, and that
`Requisito` contains the exact canonical Confluence PRD URL. Report the
`SHIFU-*` key and URL. Creating the ticket must not change product requirements
or local SDD state.
