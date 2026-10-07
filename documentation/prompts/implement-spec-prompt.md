---
name: implement-spec
description: Implement a ready or resumed Shifu Spec autonomously, verify the integrated candidate and preserve evidence for continuation.
---

# Implement a Shifu Spec

Follow [documentation/sdd.md](../sdd.md). The Spec fixes required behavior,
contracts, exclusions and checkers. Organize execution directly in the current
task. Use focused delegation when scopes are independent; there is no Plan
artifact, phase/task approval sequence or `create-plan` transition.

## Persistence and stopping rule

Own implementation and verification until Evaluation is `ready`. Do not stop
when one named check passes, code is complete or a reviewer responds while other
required obligations remain actionable. A follow-up about one check steers the
ongoing Spec unless the user explicitly narrows or cancels the objective.

1. Reconcile all CI/VM and baseline checks, CA mappings, open ACH findings and
   independent review against Evaluation before selecting the next action.
2. Execute outstanding checks, diagnose failures, fix authorized in-contract
   causes and rerun affected verification. After each correction inspect the
   entire remaining obligation set; retain unaffected current passing proof.
3. Investigate local setup failures within existing authorization: health and
   configuration, expired browser state, source-defined accounts/data and stale
   fixtures/seed definitions. Use isolated fixtures or task-owned environments.
   A first failed attempt or missing setup needs diagnosis, not immediate handoff.
4. Obtain required review/rechecks, resolve blocking findings and reconcile
   Documentation Alignment. Never remove checks or weaken assertions/thresholds
   merely to pass; material changes go through contract reconciliation.
5. Before yielding, audit every remaining check/finding and continue whenever a
   safe authorized action can advance it. Handoff describes an interruption or
   genuine blocker; it does not replace executable work.

A stale fixture/seed source is actionable when intended data is defined by the
contract. Inspect its consumers and applicable Rules, correct source definitions,
validate them and rerun the originally blocked check. Distinguish source correction
from applying a seed: inspect the real command/reset behavior and use disposable
or isolated targets. Never reset/reseed shared data without explicit authorization.
Ask only for materially ambiguous intended data or a required shared operation
that lacks authorization after isolated alternatives have been investigated.

Stop unfinished work only for an explicit stop/scope restriction, a genuinely
missing material decision/authorization, or an external dependency unavailable
after relevant diagnosis and permitted recovery. Finish independent work first;
record affected IDs, attempted recovery/proof, why outside action is needed and
the precise required input/change. Do not invent non-applicability or mark missing
proof Passed. Resume when the blocker clears without asking again for authority.

## Establish or resume the contract

Read the complete canonical templates in `documentation/templates/sdd/`:

- [`documentation/templates/sdd/spec.md`](../templates/sdd/spec.md) for contract structure;
- [`documentation/templates/sdd/evaluation.md`](../templates/sdd/evaluation.md) for progress, evidence and continuation.

Use the Evaluation template as the starting structure at kickoff. On resume,
reconcile active artifacts with these templates while preserving historical
requirements, identifiers and observed results; never overwrite existing evidence
with template placeholders.

Read the current Spec and Evaluation, applicable module/architecture/Rule
sources, relevant tooling/manifests and saved design references. Follow the SDD
source preflight; reuse complete sources already current in this context.
Inspect Git status/diffs and preserve unrelated work. Use CodeGraph for each
new code exploration when available under `AGENTS.md`.

Initial implementation requires a `ready` Spec. Resumed work requires the same
current contract and an Evaluation with unfinished criteria or findings.
Do not activate the Spec Reviewer for implementation evidence. A material
contract change routes through `create-spec`; preserve history, reconcile
source/design/checkers, increment the revision and invalidate affected proof.

Create or reconcile `evaluation.md` before editing. Record the current contract,
branch/candidate and known baseline facts. The Spec owns its revision; do not
duplicate `spec_revision` in Evaluation metadata. Identify evaluated revisions
in result details where material. Initialize per-CA Progress rows separating
implementation from verification, plus Current State, Check Results, Findings,
Lessons Learned, Handoff and Delivery using the
[Evaluation template](../templates/sdd/evaluation.md).
Read existing failure reports; do not launch integration suites for a baseline
or to complete kickoff paperwork. Environmental availability can be inspected
without starting a behavioral suite.

On continuation, compare recorded progress/evidence with the current tree.
Completed criteria stay completed only when their covered behavior and
proofs remain unchanged. Inspect recorded active process sessions/ports before
starting services. Reconcile active legacy sections without rewriting historical
IDs/results; remove duplicated revision metadata only after verifying its claims.
Recover unfinished work from the diff and findings;
choose the next implementation action without reconstructing a task ledger.

## Autonomous execution and bounded ownership

The agent decides order, implementation structure, dependencies and recovery
within the approved contract and repository Rules. Resolve routine reversible
choices directly. Ask only when an unresolved choice materially changes
product behavior, scope, ownership, public/persistent contracts or a
consequential technical commitment. Existing internal file trees guide
placement; they do not require an amendment for every helper or widget.

Implement directly for cohesive work; for independent streams, assign specifically
named sibling Builders with:

- Spec path/revision and relevant RF/CA outcomes;
- exact allowed/prohibited ownership boundaries and shared dependencies;
- applicable Rule Pack, design references and existing findings;
- unit/component/static feedback commands and expected implementation result.

Builders do not create further subagents. Keep concurrent ownership disjoint;
tell Builders they are not alone and must preserve others' edits. Coordinate shared contracts, generated artifacts,
migrations and cross-boundary changes in the main task. Inspect every returned
diff and incorporate only contract-conforming work. Delegate by coherent
ownership/outcome, not one agent per file or ceremonial phase.

Builders write or update tests from acceptance claims, including failures,
recovery and enumerated states. They run focused unit/component and static
checks during implementation. Server HTTP/PostgreSQL, Playwright browser
integration, real Inngest jobs and migration integration belong to the final
integrated verification cycle, not each Builder exit. Prefer actual CI
commands and explicit reproducible test configuration over developer secrets.

Follow selected test-boundary Rules: use-case tests mock ports; controller tests
exercise the real registered app/persistence; jobs exercise registered durable
execution; Web tests use the owning widget/hook/Page/Layout boundary. Keep
existing coverage and assertions meaningful. Do not weaken a check, skip a
failure, remove valid scenarios or invent a command to report green.

Update route-group REST examples with their owning implementation. Verify
method/path/schema/status parity and include reusable non-secret variables.
Generate routes or other artifacts with repository commands when needed.

## Design-backed implementation

Read the Spec's design contract, saved handoff/manifest and affected references.
Use existing semantic tokens, primitives, accessible pt-BR copy and the selected
UI/routing Rules. Use Pencil MCP for `.pen` inspection/editing; never read an
encrypted design with shell tools. Normal implementation uses saved references.

The Spec defines required happy-path rendered states and viewports. Cover
loading, empty, error, recovery, concurrency and unusual outcomes through
appropriate automated tests. Do not turn every saved frame into another manual
scenario. Required visual evidence comes from the integrated candidate after
the last affected UI edit, with route/state/viewport/fixture and artifact path.
An earlier capture of unchanged UI may remain valid when its dependencies and
rendered state are unchanged; explain retained evidence in Evaluation.

## Integrated verification and failure loop

Execute the Verification Contract's Automated, Manual and Visual checks and all
applicable Rule/Tooling baseline gates. For finite contracted input sets verify
defined combinations; for unbounded inputs use the contracted equivalence classes
and boundaries. Execute targeted mutation checks when required by the Spec and
record detected/surviving mutants and justified exclusions directly in Evaluation.
If required tooling is unavailable the check is Blocked; coverage is no substitute.
Do not install a runner as an incidental implementation or documentation action.

After all implementation streams and generated artifacts are integrated:

1. Compare the complete diff with the Spec's outcomes, boundaries, public
   contracts, persistent invariants, exclusions and checker coverage.
2. Before final integration checks, perform any delivery-branch synchronization
   already authorized under `conclude-spec`. Read its Git safety procedure;
   record the resulting candidate and preserve unrelated work. An unsafe merge
   or unresolved contract blocks only the work that depends on it.
3. Run applicable type, lint, complexity, architecture, unit/component and build
   checks under [Tooling](../tooling.md#scoped-type-lint-and-complexity-checks).
   Lint selects changed paths; types retain affected app/project configuration
   and affected consumer scope. Record each static category explicitly, even
   when lint and configured complexity rules share a command. Missing required
   quantitative complexity tooling is Blocked, never inferred passing from lint.
   One designated runner in the main task owns integration commands/results.
4. Run the contracted affected integration files/scenarios against the integrated
   candidate. Use actual commands with exact selections and show intended tests
   ran, including registered Inngest functions where required. Select tests only
   for scoped changes and directly affected consumers under
   [Tooling's selection policy](../tooling.md#selecting-unit-and-integration-tests).
   Broaden only for demonstrated dependency impact or a gap in that scope's proof;
   full local suites require scope spanning that suite or an explicit user request.
5. On failure, record the command/result and mapped finding, fix within the
   contract and rerun the failed and affected integration checks. Continue until
   all required selections pass. Passed unaffected selections retain their evidence;
   broader reruns require a concrete changed shared dependency or coverage gap.
   Retain historical full-run failures; focused corrections establish their scoped
   current results, not an inferred full-suite pass or new coverage measurement.
   Avoid duplicate unchanged full tests when an actual coverage command runs them.
6. Execute the Spec-required concise happy-path manual journeys with Playwright
   CLI or their real runtime boundary. Check final URL, requests, persistence,
   keyboard/focus, narrow viewport and console/network findings as applicable.
   Capture required visuals within those journeys. Do not add manual negative
   matrices or repeated accounts/fixtures without an acceptance obligation.
7. Inspect actual captures against the references and record concrete
   differences and evidence limits. A screenshot cannot prove persistence or
   authorization; mocked transport cannot replace a required real journey.
8. Stop only task-started application processes and disposable fixtures;
   preserve shared services/data under `AGENTS.md`.

Required unavailable services, accounts or fixtures are blockers, never passing
checks. Continue independent useful work; report the precise unavailable proof.
Retry a transient environment failure when there is evidence it can succeed.
An explicit user waiver is recorded as waived, without a passing claim or
removal of automated acceptance obligations.

## Parallel review and corrections

Launch the independent
[Implementation Reviewer](../agents/implementation-reviewer-agent.md) on the
integrated diff, current Spec, selected Rules and current acceptance evidence.
For design-backed UI, launch the
[Visual Reviewer](../agents/visual-reviewer-agent.md) **in parallel** on the same
candidate and required existing captures/references. Add no mandatory third
serial reviewer. Additional specialists need a distinct material risk, not a
package count or task boundary.

Reviewers inspect assertions and evidence scope/freshness against every CA.
They consume the recorded integration results; they do not rerun green suites
merely to occupy a different role. Missing, stale or unsupported proof yields
a concrete finding and the specific needed checker. The Orchestrator reconciles
reports, verifies findings and records ACH IDs and their disposition.

Fix in-contract findings autonomously. Rerun only invalidated checkers and
visual comparisons, and resume only the affected review scope. A correction
that crosses both code and visuals reactivates both reviewers in parallel.
A contract conflict returns to `create-spec`; implementation findings stay in
this correction loop. Do not silently reduce acceptance or update external PRDs.

## Evidence and readiness

Follow the seven-section [Evaluation template](../templates/sdd/evaluation.md).
Progress has one row per CA with separate Implementation (Pending/Partial/Complete)
and Verification (Pending/Partial/Passed/Failed/Blocked/Stale), mapped checks/evidence
and remaining work. Check Results includes baseline checks and uses Pending,
Passed, Failed, Blocked, Stale or Not applicable, with EV IDs, exact procedures,
actual test selection/counts, expected/observed outcomes, candidate/date,
environment/fixtures, artifact paths and limits. Record explicit Manual/Visual
types for VM checks. Preserve failed/interrupted attempts and limitations.
Use stable CA/CI/VM/EV/ACH IDs. Record meaningful checkpoints such as accepted Builder work,
checker runs and resolved findings, rather than a ledger update per file edit.

Invalidate evidence by affected claim/dependencies, not by commit age alone.
A change in implementation, fixtures, environment or contract reopens the checks
it affects. Unchanged passed evidence remains valid across role transitions,
ledger edits, review and conclusion. Record the retained evidence and reason.

Keep a small factual Handoff: contract revision, branch/candidate, completed and
unfinished criteria, interrupted/uncommitted paths and ownership, latest results,
task-started process sessions/ports and cleanup, blockers and next action. Keep
blockers specific; do not convert this section
into phases, task trees, estimates or a second contract.

Record reusable lessons with supporting ACH/EV references and their documentation
action or reason no change is warranted. A trivial correction need not become a
lesson or global policy. Keep Delivery source verification, documentation alignment,
publication/CI state and limitations factual.

When all criteria have current passing proof or justified non-applicability,
applicable checkers pass and blocking findings are resolved, set Spec to `implemented`, Evaluation to
`ready` and continue directly into `conclude-spec`. Conclusion reuses these
results; it does not start another broad integration run. The exact automated,
manual, review, waiver and limitation records must support every readiness claim.
A waiver cannot turn a required Failed/Blocked/Stale check into a pass or readiness.
Continue local conclusion directly; publication still requires existing authority,
and published completion waits for current-head CI and blocking review resolution.

## Report

Return Spec/Evaluation links, revision/candidate, implemented outcomes, checker
results, reviewer findings/dispositions, remaining criteria/blockers and next
action. Keep runtime/visual limitations explicit. Reusable guidance uncovered
by a defect may be recorded as a grounded lesson; repository-wide authority
changes and external writes still follow their authorization boundaries.
