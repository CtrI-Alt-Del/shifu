---
name: implement-spec
description: Orchestrate a ready or resumed Shifu Spec through direct or Plan-backed implementation, living Evaluation evidence, corrections and integrated validation.
---

# Implement a Shifu Spec

Use this as the single implementation entry point for every ready or resumed
Shifu Spec. Select the execution strategy from the current artifacts and run it
in the current task; do not require the user to choose another implementation
prompt or create another user-owned task:

```text
implement-spec
├── no current Plan → Builder Direct in the current context
└── current Plan    → stable ownership Builders by dependency wave
                       ↓
                 integrated candidate
                       ↓
             conformance record + sensors
                       ↓
             single Implementation Reviewer
                       ↓
                 conclude-spec
```

Keep Orchestrator, Builder and Implementation Reviewer passes distinct. The
Orchestrator may perform direct implementation only when the current strategy
explicitly assigns Builder Direct to the current context.

The current Spec is the implementation Contract. Existing code, a screenshot, a
passing test or a new request cannot silently override its behavior, paths,
architecture, exclusions or validation obligations. If the Contract must change,
route through create-spec.

## Strategy selection

Read documentation/sdd.md and its mandatory authorities:

- the exact Spec and selected source/PRD;
- documentation/modules.md;
- documentation/architecture.md;
- documentation/rules.md and every selected Rule;
- documentation/tooling.md;
- the current Plan, when present;
- the complete canonical Confluence PRD and recorded content ID/version;
- relevant Jira, design references and existing Evaluation.

Select the strategy from current artifacts:

| Condition | Strategy |
| --- | --- |
| Current Plan references the exact Spec revision | Plan-backed execution |
| No Plan and the Spec is small, cohesive and low risk | Builder Direct in the current task |
| No Plan but dependencies, ownership boundaries, risk or recovery state require one | Invoke create-plan, then continue here |
| Plan is stale after a Spec amendment | Reconcile or recreate it before dependent implementation |
| Revised Spec no longer needs its Plan | Mark the Plan superseded according to SDD, then use direct execution |

A completed Plan may be reopened for an in-Contract correction after conclusion or
PR feedback; reopen only affected phases/tasks. Never derive execution order,
waves or Builder dependencies from the PRD Product Dependency Graph. Derive
them from the Spec Technical Contract, affected paths, runtime dependencies and
ownership boundaries.

## Spec Reviewer boundary

The Spec Reviewer belongs exclusively to create-spec. It is a pre-implementation
Architecture, Modules and Rules compatibility gate. It does not review code,
Plan execution, Evaluation evidence, product completeness or design fidelity.

Do not activate or resume the Spec Reviewer during implementation. Plan-backed
quality uses the single read-only Implementation Reviewer described below. A
material Spec amendment returns to create-spec for clarification and the same
pre-plan compatibility review before implementation resumes.

If implementation discovers a test path, layer boundary or generated artifact
that conflicts with the selected Rules or test-integrity policy, stop before
weakening the checker or editing the invalid test contract. Record the conflict,
route a material amendment through create-spec, then rerun the applicable Spec
Reviewer before resuming.

## Fail-closed implementation invariants

Stop before editing feature source when any invariant cannot be verified:

- the Spec is ready for initial implementation or in_progress for a resumed
  correction, and its revision is current;
- a direct assignment or scoped ownership Builder is active before feature
  source, test, migration or generated-artifact edits begin;
- Evaluation is materialized or reconciled before the first implementation
  change, with the baseline and current revision recorded;
- Plan-backed work has exact phase/task assignments, non-overlapping paths,
  dependencies, Rule Pack and exits;
- the Builder receives the exact RF-*/CA-* mapping, allowed/prohibited paths,
  design references and validation exits;
- the delivery preserves the canonical PRD, Jira and external authority state;
- a route-group change includes its matching REST-client artifact in scope;
- an affected UI has its saved design authority and reference inventory;
- any UI geometry or styling change has a current visual evidence row and a
  fresh comparison requirement;
- required manual, runtime, persistence or authorization evidence is treated as
  fail-closed rather than replaced by mocks;
- prior evidence affected by the current diff is marked stale immediately; and
- Evaluation is updated in the same task after every implementation, test,
  browser, generation, migration, documentation or validation change.

Do not invent a repository-wide conformance sensor, coverage command, port,
fixture, workflow or test alias. Structural conformance is an Orchestrator
comparison against the Spec and filesystem. Executable gates are the commands
declared by the Spec, current manifests, Rules and documentation/tooling.md.

Implement-spec never changes a PRD requirement to Implemented and never mutates
Confluence or Jira as a side effect. Evaluation ready means implementation
evidence may enter conclusion; it is not product closure.

An implementation, test, browser, network, console, build, migration,
documentation or visual error within the current Contract is an automatic
correction: record it, invalidate affected evidence, continue the responsible
Builder or activate a scoped Builder Fix only when the original Builder cannot
be resumed or the correction is genuinely independent, then rerun affected
checks. Do not pause for permission to make an in-Contract correction.

This also applies to maintenance-sized visual changes. A margin, padding, width,
max-width, gap, alignment, container, responsive or spacing change is not
validated by a passing unit test or an old screenshot; mark affected visual
evidence stale, recapture the exact state/viewport and record the comparison in
Evaluation.

## Builder activation

Before any feature source edit, activate a scoped execution assignment. The
assignment must include:

- exact Spec path and revision;
- assigned direct scope or Plan phase/task;
- RF-*/CA-* and selected RP-*/JN-* mapping;
- observable outcome;
- exact allowed and prohibited paths;
- owning module/application/layer;
- applicable Rule Pack and Architecture;
- Design Contract and saved references when UI is involved;
- dependencies and blocking findings for corrections; and
- focused and integrated validation exits.

Use Builder Direct in the current task for a small cohesive delivery. For
Plan-backed execution, use stable ownership Builders derived from actual affected
boundaries. Typical names are Builder Core, Builder Server, Builder Web,
Builder Validation and Builder Integration; activate only affected boundaries.
Do not create one Builder per package, phase or task.

When delegating, use descriptive stable task names that identify the module and
ownership boundary, such as identity-core-builder, identity-server-builder or
identity-web-builder. Use a similarly specific implementation-reviewer name.
Never use vague names such as worker, agent or reviewer alone. Record each
assignment's identifier, exact boundary, allowed paths and Spec revision in
Evaluation before accepting its work.

A Builder may own multiple sequential phases within its boundary. Paths may not
overlap between active Builders. Default to at most three concurrent
implementation Builders. Exceed that only when the Plan records stable
contracts, substantial independent work, a concrete parallelism benefit and the
integration cost is justified.

The Orchestrator owns SDD artifacts, root configuration, dependency installation,
lockfiles, shared/generated files, migration coordination, cross-Builder
integration and final validation. Builders edit only assigned code/tests and
route artifacts. Builders do not edit Spec, Plan, Evaluation, Rules,
Architecture, Modules, Design, Tooling or external systems.

A Builder report is not official evidence. The Orchestrator inspects the diff,
verifies the exit and materializes the result in Evaluation.

## Evaluation kickoff and lifecycle

Before the first implementation change for the current revision:

1. verify the complete PRD, content ID/version, source traceability and Spec
   status;
2. freeze the current Spec revision;
3. create or reconcile evaluation.md with status in_progress;
4. record the pre-implementation baseline, including existing failures,
   unavailable services and unrelated warnings;
5. activate Builder Direct or affected ownership Builders and record their
   exact assignments;
6. compare the untouched implementation with the Spec's required path/widget
   tree, contracts, states and exclusions;
7. for Plan-backed work, validate dependencies, mark the Plan and affected
   phases/tasks in_progress, and record the next action;
8. initialize the acceptance matrix, automated gates, manual/visual evidence,
   Rule/documentation compliance, findings and evidence log; and
9. record required services, accounts, fixtures, design references and evidence
   targets.

Do not proceed if the assignment, baseline comparison or Evaluation kickoff is
missing. A prose claim that these occurred is insufficient.

The local Shifu Evaluation shape is:

- front matter containing title, status, Spec path, Spec revision, optional Plan,
  source, PRD content ID/version when applicable and last-updated date;
- Evaluation status;
- Acceptance coverage;
- Automated gates;
- Manual and visual evidence;
- Review findings; and
- Evidence log.

Treat this structure as the local Evaluation contract. Preserve its section
order and the existing feature's front matter; do not replace it with a
narrative report or a feature-specific parallel ledger. At minimum, maintain
these tables:

| Section | Required columns or content |
| --- | --- |
| Acceptance coverage | Criterion, Spec coverage, Required evidence, Disposition, Status |
| Automated gates | CI ID, command/sensor, coverage, result, evidence |
| Manual and visual evidence | VM scenario details, exact viewport/state, reference, artifact path, observed result and status |
| Review findings | ACH ID, classification, source, affected evidence, status and resolution |
| Evidence log | EV ID, date, scope, exact command/scenario, result, finding, runtime notes and acceptance mapping |

Use the existing feature's names when a table has additional authoritative
columns. Add a row for every CA-*, executed automated/runtime gate, VM-* and
acceptance-relevant visual reference or supplemental state. Use stable EV-* for
evidence and CI-* for automated gates; use ACH-* for review findings. Ordinary
evidence may be pending, passed, failed, stale or not_applicable. A manual row
records both expected and observed behavior. Preserve failed attempts and
historical evidence rather than overwriting them.

Preserve existing Evaluation evidence, failed attempts and findings. Reconcile
missing columns or rows without deleting history. Use stable EV-* for evidence,
CI-* for automated gates and ACH-* for accepted/rejected review findings.
One row is required for each CA-*, each executed automated/runtime gate, each
VM-*, each acceptance-relevant visual reference or supplemental state, and each
finding. Use pending, passed, failed, stale or not_applicable for ordinary
evidence. Every manual row records expected and observed behavior.

Do not overwrite prior evidence. Evidence captured before the latest affected
change is historical or stale, not proof for the current candidate. Keep
Evaluation in_progress until all required evidence is current and no blocking
finding remains. Set it to ready only at the final implementation handoff.

## Direct execution

Use direct execution when no current Plan exists and the delivery is small and
cohesive:

1. activate Builder Direct with the current revision, RF/CA mapping, outcome,
   allowed/prohibited paths, Rule Pack, Architecture, design bundle and exits;
2. implement only that scope, then inspect the diff;
3. run focused repository-approved generation, lint, type, unit and integration
   checks required by the scope;
4. update Evaluation with exact commands/results, criterion coverage, findings
   and evidence freshness;
5. continue Builder Direct for in-Contract corrections and rerun only
   invalidated evidence; and
6. repeat until ready or an authority/environment blocker is reached.

Do not edit Spec, Plan or Evaluation while acting as Builder Direct. Return to
the Orchestrator role for artifact updates. Reserve broad builds for the final
Quality Gate unless bundler, export, environment, Docker or generated-artifact
changes require an earlier build.

## Plan-backed execution

When a current Plan exists, the Plan owns sequencing, status, attempts and next
action. Evaluation owns executed evidence, findings and results.

Before each dependency-ready wave:

1. confirm the exact Spec revision, dependencies, criteria, paths, Rules,
   Builder assignments and exits;
2. mark the phase and assigned tasks in_progress;
3. activate or resume each affected ownership Builder, keeping related phases
   with the same Builder;
4. coordinate shared/generated files, dependencies and lockfiles through the
   Orchestrator;
5. inspect and integrate Builder diffs without allowing overlapping paths;
6. run focused generation, lint, type, unit and integration checks from the
   exits;
7. update Evaluation immediately with exact results, evidence freshness and
   lessons, then update Plan status/finding IDs/attempts/next action;
8. complete a task only when its exit passes, and a phase only when every task
   and phase exit passes; and
9. on failure, keep affected work in_progress, resume the responsible Builder,
   invalidate affected evidence and rerun only what changed.

Keep the Plan itself in_progress until conclude-spec closes it. Do not mark the
Plan completed merely because implementation phases are complete.

## Builder-focused validation

Use the actual repository commands from the Spec and tooling documentation.
Typical ownership expectations are:

- Builder Core: applicable server lint, architecture, types and focused use-case
  tests;
- Builder Server: applicable server checks, controller/integration tests and
  real application-boundary scenarios for changed behavior;
- Builder Web: applicable web lint, architecture, types, unit tests, browser
  integration and build checks;
- Builder Validation: schema/type/unit checks and all consuming-boundary
  evidence;
- Builder Integration: generated routes, application composition, services,
  persistence, messaging and cross-layer checks required by the assignment.

When a server-backed behavior changes, validate the real FastAPI application
boundary, status/body/error contract, authorization, persistence and side
effects. A mocked controller or transport test is supporting evidence only.

When an HTTP route group changes:

- update apps/server/rest-client/<module>/<route-group>.rest in the same scope;
- include one labeled request for every controller route;
- verify methods, paths, parameters, headers, representative bodies and
  reusable non-secret variables; and
- record parity in Evaluation.

When UI/browser behavior changes, use the repository Playwright CLI workflow
and accessible role/name locators where possible. Exercise applicable keyboard,
focus, narrow-viewport, loading, empty, error and recovery states. Inspect
console errors, failed requests, HTTP statuses and final URLs. Capture and
inspect a fresh screenshot for each affected design state at its exact viewport.
Do not create a feature evidence directory or rely on a mocked transport test as
visual/runtime proof.

Builder checks are focused feedback, not official evidence. The Orchestrator
verifies required exits on the integrated candidate and records them in
Evaluation in the same task turn.

## Spec conformance gate during implementation

Treat the Spec as an active implementation Contract, not only final-validation
guidance. Before the first change, before each phase/task or Builder handoff,
and after every correction, compare the candidate with the Spec's required
paths, widget/module tree, declarations, behavior, design states, exclusions
and validation exits.

Record this checkpoint in Evaluation:

| Check | Required proof |
| --- | --- |
| File/widget tree | Required paths exist, no path is misplaced, and every intentional extra path is mapped or explicitly excluded. |
| Boundary ownership | Every changed path is inside the active Builder scope and declared module/layer. |
| Route artifacts | Every affected route group has a route-complete REST-client file with no credentials. |
| Contract | RF/CA, API fields, domain rules, persistence, error semantics and exclusions match the current revision. |
| UI states | Applicable loading, empty, success, error, recovery, disabled, selected, focus, keyboard and responsive states are exercised. |
| Design references | Every required screenshot has an exact state/viewport comparison and current artifact identifier. |
| Validation | Commands ran on the current candidate; console, failed requests, HTTP errors, hydration warnings and persistence results are classified. |

This is an Orchestrator conformance record, not a nonexistent repository-wide
sensor. If a path, declaration, behavior or state is missing, extra or
misplaced, keep the work in_progress, record an ACH-* finding, invalidate
affected evidence, correct it through the responsible Builder and rerun the
affected checks. Passing tests or screenshots alone does not establish Spec
conformance.

## Design authority and visual gate

For any UI or design-backed change, run this gate before editing feature source
and again before marking the affected task/phase complete. It applies to small
visual maintenance changes as well as new screens.

Before the first visual edit:

1. resolve and record the exact feature root and affected route/widget paths;
2. resolve the canonical feature-local design authority: prefer
   design/handoff.md, and use design/manifest.md only when the active Spec
   explicitly uses that legacy convention;
3. read the handoff/manifest and every saved reference for the affected
   surface, recording state, exact viewport, implementation path, reference
   path and approved supplemental states;
4. freeze the scope fence with allowed paths and excluded adjacent surfaces;
5. record an EV-* preflight row in Evaluation and an ACH-* finding for any
   unresolved mismatch or ambiguity before feature source edits begin.

For each affected visual surface:

1. capture or identify the baseline at the exact reference viewport/state;
2. implement the smallest composition slice and compare structure, hierarchy,
   surfaces, controls, typography/tokens, states, responsive behavior and
   keyboard/focus affordances before moving on;
3. treat a material in-Contract discrepancy as an automatic correction: mark
   affected visual EV-* rows stale, record the finding, fix it and recapture;
4. compare the final changed-file list against the scope fence; and
5. record fresh screenshot paths/artifact identifiers, differences, console and
   network classification in Evaluation.

If no design reference exists, record the visual-reference portion as
not_applicable while still validating responsive behavior, accessibility,
keyboard paths and scope. When .pen files are involved, use Pencil skills/MCP;
never inspect or edit encrypted .pen files with shell or generic filesystem
tools. Builders use saved references during implementation and do not depend on
live Pencil unless the Design Contract itself must change.

## UI and design-backed implementation

When the Spec has a Design Contract:

- read documentation/design.md, the selected UI Rules,
  the feature-local design manifest or handoff and every saved reference before
  coding;
- use the visual inventory as an executable checklist;
- preserve exact route, surface, state and viewport mappings;
- use existing Shifu semantic tokens, shared primitives, pt-BR copy and
  accessible focus language;
- keep feature widgets under the owning module and shared widgets under
  ui/shared;
- follow the stateful widget index.tsx plus colocated hook convention;
- keep routes thin and business decisions outside UI;
- do not depend on live Pencil during normal implementation;
- compare each affected state at the same viewport with Playwright CLI and
  record one visual evidence row per reference/state; and
- if a reference reveals unexpected or uncontracted behavior, pause that part
  and route the question to the Orchestrator rather than inferring scope.

A visual mismatch within the Contract is a correction. A requested new behavior,
state or component absent from the Contract is a Contract/design amendment.

## Hook and test-integrity gate

Follow the selected test Rules exactly. For stateful or composed widgets, verify
that behavior-owning colocated hooks have the required tests at the permitted
boundary. The component test that mocks its owning hook is not a substitute for
testing that hook's public state, effects, guards and outcomes when the Rules
require a hook test.

Do not create dedicated tests for query/action hooks or web REST services when
the selected Rules assign their observable behavior to the consuming
widget/page/route boundary. Record that exception and the consuming evidence in
Evaluation. Do not create tests under prohibited provision directories or call
concrete infrastructure providers directly when the Rules forbid it.

For every test path in the Spec, verify its placement and ownership before
editing. If a test contract conflicts with a Rule or test-integrity policy, stop,
record the blocker and route a material Spec amendment. Do not weaken a Rule or
delete a test to make a gate pass.

## Living evidence and corrections

After every implementation change, generated artifact, migration, test,
environment/fixture change, browser run, documentation correction or validation
change:

1. inspect affected paths and diff;
2. mark affected prior evidence stale or historical;
3. record the exact command/scenario, result, criteria, evidence ID and
   freshness in Evaluation;
4. record material findings as ACH-* with severity, status and resolution; and
5. update Plan status, attempts and next action when a Plan exists.

If an error is within the current Contract, fix it immediately through the
responsible Builder and rerun invalidated evidence. If it requires product,
technical authority, module ownership, Architecture, Rule or Design change,
pause and route create-spec.

### User-requested changes during implementation

Classify each new request before changing code or artifacts.

For an in-Contract correction:

1. keep the Spec revision unchanged;
2. record a mapped finding in Evaluation;
3. set Evaluation and affected Plan work in_progress;
4. resume the responsible Builder or activate a scoped Builder Fix only when
   necessary;
5. rerun affected exits, manual scenarios and visual comparisons; and
6. continue the selected strategy automatically.

For a Contract change:

1. set the Spec to draft;
2. invoke create-spec for clarification and authority alignment;
3. increment the Spec revision and refresh affected Contract/design/validation;
4. preserve invalidated evidence as historical;
5. set Evaluation to in_progress;
6. reconcile or supersede the Plan as required; and
7. resume this workflow under the selected strategy.

Ask the user only when the intended product/technical outcome, authority,
environment access or safety decision is genuinely ambiguous.

## Implementation Reviewer

For Plan-backed execution, activate exactly one read-only Implementation
Reviewer after all Builder diffs and Orchestrator-owned artifacts are integrated.
Do not create Reviewers per Builder, phase, application, package, layer or
specialty. Direct execution does not require a separate Reviewer unless the
Spec or repository authority explicitly requires one.

Do not substitute or reactivate the Spec Reviewer. Give the Implementation
Reviewer the exact Spec revision, Plan, Rule Pack, integrated diff, changed
paths, required file/widget tree, design references, REST-client artifacts,
current Evaluation index, required services/fixtures and known risks.

The Reviewer checks the complete candidate for Spec conformance, cross-Builder
contracts, missing states/tests, integration conflicts, Rule violations and
stale/unsupported evidence. For UI, it inspects every required screenshot and
replays high-risk responsive, keyboard, accessibility, console and network
interactions with Playwright CLI. For server-backed behavior, it may replay
high-risk real application-boundary requests and inspect authorization,
persistence and side effects.

The Reviewer does not edit files, decide official evidence, change statuses or
resolve Contract ambiguity. Its report is not evidence. The Orchestrator
verifies each finding, records accepted ACH-* entries, invalidates affected
evidence, resumes the responsible Builder and reruns the affected exits.
Resume the same Reviewer after correction; do not replace it merely because the
candidate changed. Give the Reviewer the current conformance record and
Evaluation index; it consumes that record and does not replace it with an
unrecorded personal verdict.

## Integrated validation and readiness

After all implementation work is complete:

1. compare the complete integrated diff against the exact Spec revision,
   allowed/prohibited paths, widget/module tree, Contracts, exclusions and
   generated-artifact treatment;
2. record a fresh Spec conformance checkpoint and verify every changed path,
   declaration, state, exclusion and generated artifact against it;
3. run all applicable focused and broad Web/Server checks named by the Spec and
   tooling documentation;
4. review generated routes, migrations, lockfiles, REST-client examples and
   shared configuration when affected;
5. preflight actual services, database/auth/provider state, accounts and
   fixtures;
6. execute every applicable VM-* with the Playwright CLI or the real boundary
   required by the Spec;
7. verify every affected REST-client file against its controller route group
   and shared request schemas;
8. inspect every CA-* and every supplied/required supplemental screenshot with
   exact viewport/state, console/network, accessibility, layout and persistence
   evidence;
9. activate and complete the single Implementation Reviewer when Plan-backed;
10. verify and classify every Reviewer finding; and
11. record all commands, captures, parity results, findings and resolutions in
    Evaluation.

Keep the final integrated phase in_progress while integrated validation is active.
A required manual/runtime scenario that is unavailable, inaccessible,
non-repeatable, times out or fails is a blocking validation finding. Stop
unrelated feature implementation until the environment or implementation changes
and the scenario is freshly rerun.

When all criteria have current evidence, all required gates pass, all verified
blocking findings are resolved and the exact candidate is reconciled:

- set Spec status to implemented;
- set Evaluation status to ready;
- keep Plan status in_progress until conclusion, with all completed phases/tasks
  and the next action recorded; and
- invoke conclude-spec immediately.

Do not change PRD Implemented state. Do not claim ready from evidence captured
before the latest affected change.

## Rule and documentation lessons

When a finding exposes reusable missing or ambiguous guidance, keep two records:

1. an ACH-* finding describing the concrete problem, affected evidence, status
   and resolution; and
2. a Lessons learned entry when the finding exposes guidance future work can
   reuse.

For each reusable lesson:

- record the concrete finding and resolution in Evaluation;
- extract the reusable lesson;
- update the applicable authority only when the lesson is already consistent
  with the approved Contract and the authority workflow permits it; and
- record the authority path and disposition, or an explicit No change reason.

If the reusable convention is unclear, pause dependent work and route a focused
Antipatterns to Avoid or authority change through its required workflow. Reread
the changed authority, recompute the Rule Pack, invalidate affected evidence and
rerun the correction. Do not turn a transient environment failure, isolated
typo, already-documented Rule or feature-local detail into global guidance.

## Implementation handoff

Return a concise result containing:

- strategy: direct or Plan-backed;
- Spec path and exact revision;
- Plan path/status and current phase/tasks when present;
- Builders and owned paths, including any resumed/fix Builder;
- changed files and generated artifacts;
- RF/CA coverage and current EV/VM/CI/ACH evidence;
- commands run and exact results;
- REST-client parity result when applicable;
- runtime, persistence, authorization and side-effect evidence when applicable;
- visual/reference states, screenshots and Playwright findings when applicable;
- active blockers, stale evidence and limitations;
- Implementation Reviewer result when applicable; and
- readiness: ready for conclude-spec, or the exact blocker and next action.

Do not claim implementation, evidence, review, readiness or quality gates passed
unless observed and recorded.
