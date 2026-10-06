---
name: implement-spec
description: Implement a ready or resumed Shifu Spec autonomously, verify the integrated candidate and preserve evidence for continuation.
---

# Implement a Shifu Spec

Follow [documentation/sdd.md](../sdd.md). The Spec fixes required behavior,
contracts, exclusions and checkers. Organize execution directly in the current
task. Use focused delegation when scopes are independent; there is no Plan
artifact, phase/task approval sequence or `create-plan` transition.

## Establish or resume the contract

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

Create or reconcile `evaluation.md` before editing. Record the Spec revision,
current branch/candidate and known baseline facts. Initialize acceptance rows
and the small handoff using the [Evaluation template](../templates/sdd/evaluation.md).
Read existing failure reports; do not launch integration suites for a baseline
or to complete kickoff paperwork. Environmental availability can be inspected
without starting a behavioral suite.

On continuation, compare recorded progress/evidence with the current tree.
Completed criteria stay completed only when their covered behavior and
proofs remain unchanged. Recover unfinished work from the diff and findings;
choose the next implementation action without reconstructing a task ledger.

## Autonomous execution and bounded ownership

The agent decides order, implementation structure, dependencies and recovery
within the approved contract and repository Rules. Resolve routine reversible
choices directly. Ask only when an unresolved choice materially changes
product behavior, scope, ownership, public/persistent contracts or a
consequential technical commitment. Existing internal file trees guide
placement; they do not require an amendment for every helper or widget.

For independent streams, assign specifically named Builders with:

- Spec path/revision and relevant RF/CA outcomes;
- exact allowed/prohibited ownership boundaries and shared dependencies;
- applicable Rule Pack, design references and existing findings;
- unit/component/static feedback commands and expected implementation result.

Keep concurrent ownership disjoint; tell Builders they are not alone and must
preserve others' edits. Coordinate shared contracts, generated artifacts,
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

After all implementation streams and generated artifacts are integrated:

1. Compare the complete diff with the Spec's outcomes, boundaries, public
   contracts, persistent invariants, exclusions and checker coverage.
2. Before final integration checks, perform any delivery-branch synchronization
   already authorized under `conclude-spec`. Read its Git safety procedure;
   record the resulting candidate and preserve unrelated work. An unsafe merge
   or unresolved contract blocks only the work that depends on it.
3. Run applicable final static, unit/component and build gates. One designated
   verification runner in the main task owns the integration commands/results.
4. Run every applicable integration suite once against the integrated
   candidate. Batch tests using actual repository commands and show that the
   intended tests ran, including registered Inngest functions where required.
5. On failure, record the command/result and mapped finding, fix within the
   contract and rerun the failed and affected integration checks. Continue until
   all applicable suites pass. Passed unaffected suites retain their evidence;
   broader reruns require a concrete changed shared dependency or coverage gap.
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

Evaluation holds one acceptance matrix and checker results, manual/visual
observations, findings and evidence log. Use stable CA/CI/VM/EV/ACH IDs; retain
failed attempts. Record meaningful checkpoints such as accepted Builder work,
checker runs and resolved findings, rather than a ledger update per file edit.

Invalidate evidence by affected claim/dependencies, not by commit age alone.
A change in implementation, fixtures, environment or contract reopens the checks
it affects. Unchanged passed evidence remains valid across role transitions,
ledger edits, review and conclusion. Record the retained evidence and reason.

Keep a small factual current handoff: Spec revision, branch/candidate, completed
and unfinished criteria, interrupted/uncommitted work, latest check results,
blockers and next action. Keep blockers specific; do not convert this section
into phases, task trees, estimates or a second contract.

When all criteria have accepted current dispositions, applicable checkers pass
and blocking findings are resolved, set Spec to `implemented`, Evaluation to
`ready` and continue directly into `conclude-spec`. Conclusion reuses these
results; it does not start another broad integration run. The exact automated,
manual, review, waiver and limitation records must support every readiness claim.

## Report

Return Spec/Evaluation links, revision/candidate, implemented outcomes, checker
results, reviewer findings/dispositions, remaining criteria/blockers and next
action. Keep runtime/visual limitations explicit. Reusable guidance uncovered
by a defect may be recorded as a grounded lesson; repository-wide authority
changes and external writes still follow their authorization boundaries.
