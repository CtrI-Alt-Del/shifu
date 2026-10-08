---
name: conclude-spec
description: Verify a Shifu delivery and complete its local SDD artifacts.
---

# Conclude a Shifu Spec

Close the current delivery by reconciling the Spec contract, Evaluation evidence,
findings and publication references. Consume valid implementation evidence;
conclusion does not start another full validation or review cycle.

An explicit `conclude-spec` invocation authorizes fetching and merging the latest
`main` from the delivery branch's verified remote into that branch, followed by
scoped `commit-code` and `create-pr` publication. A local-only request skips commit
and PR publication. This never authorizes merging the delivery into `main`,
deployment, or Jira/Confluence mutation.

Automatic continuation from implementation does not expand authorization. Perform
synchronization and publication only when the user's request already grants them;
otherwise conclude locally and report publication as not requested.

## Preconditions and continuity

Read the complete canonical templates in `documentation/templates/sdd/`:
[`spec.md`](../templates/sdd/spec.md) and
[`evaluation.md`](../templates/sdd/evaluation.md). Use them to confirm section
ownership and closure records; preserve the delivery's contract and historical
evidence rather than replacing populated artifacts with blank templates.

Read `documentation/sdd.md`, the exact Spec revision and Verification Contract
(legacy Validation Contract), Evaluation, relevant Rules and tooling, and the integrated diff. Verify canonical
PRD content ID/version; reuse a complete current read in the same context, and
reread the complete page if its version changed or authority is uncertain. Report authority conflicts;
return an affected Spec to `draft` or `stale` for reconciliation through
`create-spec`, then resume implementation. Never silently alter product intent,
module ownership, Architecture, Rules or the acceptance contract.

Require:

- the current Spec is `implemented` and Evaluation is `ready` for that revision;
- every applicable `RF-*`, `CA-*`, checker and required `VM-*` has current passing
  evidence or an explicit, justified non-applicable disposition; Progress
  distinguishes Complete implementation from Passed verification;
- required independent implementation and visual reviews cover the candidate;
- no blocking finding remains; and
- Jira/source traceability, scope and exclusions are accurate.

A failed, missing, unavailable, skipped, waived or stale required check is not a
pass and cannot yield readiness or completion. Reconcile Check Results, Progress,
Findings and the actual candidate; a passing status without observed proof is
insufficient.
Keep Evaluation `in_progress` while required evidence or corrections are pending.
Retain a factual handoff: criterion progress, current candidate, reusable and stale
results, unfinished code, blockers and the next concrete action.

For an in-contract defect, add an `ACH-*`, invalidate only affected evidence and
route directly to `implement-spec` inside the current task. The responsible
Builder corrects it; the designated verification runner refreshes affected checks
until they pass. Resume conclusion when Evaluation is ready. Do not stop at a
suggested next step for a fix that is already authorized.

## Synchronize before final integration verification

1. Confirm the current branch is the delivery branch, not `main` or production,
   and verify its configured remote and real `main` ref.
2. Inspect staged, unstaged and untracked work. Preserve unrelated changes; never
   reset, stash, autostash, switch branches or overwrite work to force a merge.
   Pause only if Git cannot safely preserve the work or authority is unresolved.
3. Fetch and merge that remote's latest `main`; do not rebase. Record the fetched
   commit and resulting candidate in Evaluation. If the latest fetched ref was
   already incorporated, reuse that synchronization result.
4. For conflicts, follow `resolve-merge-conflicts-prompt.md`, preserve both intents,
   stage exact owned paths, finish the pending merge and inspect the integrated
   diff. Coordinate integration execution with the designated runner instead of
   duplicating it in the conflict workflow.
5. Inspect changes introduced by synchronization. Run outstanding required
   integration selections only after the synchronized candidate is integrated. If
   checks already passed and synchronization changes covered behavior, fixtures,
   dependencies or configuration, reopen only affected checks and review scope.
   An ancestry-only merge or unaffected change does not mandate a blanket rerun.

Perform authorized synchronization before final integration verification whenever
possible. If `main` advances during publication, apply this same scoped evidence
invalidation rule. Do not use an unqualified `git pull`; the delivery upstream may
be a different branch. Failed fetches, unknown remote authority and unresolved
conflicts prevent publication.

## Reconcile conformance and evidence

Inspect the complete worktree and delivery diff:

```bash
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
git log -10 --format='%h %s'
```

Classify exact delivery paths, required factual documentation, operational ledger
changes and unrelated work. Include required delivery documentation in ordinary
commits; preserve unrelated changes and explicitly exclude them. Never inspect
`.pen` bytes with filesystem tools.

For every selected criterion, confirm current implementation satisfies the Spec
and its concrete checker. Passing tests alone do not establish complete contract
coverage. Record boundaries, exclusions, checker evidence and known limitations.
Use stable identifiers and preserve failures and their resolutions.

Use Evaluation Progress and Check Results, rather than adding another acceptance
matrix. Progress separates implementation from verification and maps CA/RF to
CI/VM and EV IDs. Manual and Visual VM checks have explicit types and pass
conditions; baseline checks remain in the same results record. Confirm separate
current type, lint, complexity and local changed-code coverage dispositions for the
scoped changes and affected consumer projects. Reuse applicable results;
configured complexity lint is not
proof of a quantitative metrics gate, and missing required tooling blocks closure.

Evidence includes exact command and working directory, result, code revision or
worktree identity, relevant fixture/configuration and covered criteria. Results
remain valid when their contract, covered code and dependencies, fixtures and
configuration are unchanged. Explain reuse across a new candidate SHA; ledger
edits alone do not invalidate results. Corrections invalidate affected evidence
until refreshed; unknown impact requires checking the broader potentially affected
scope. Do not overwrite an old evidence ID with a materially different result.

For HTTP changes, compare each affected controller route group with its matching
`apps/server/rest-client/<module>/<route-group>.rest` file. Require one labeled
request per route, current parameters/headers/body/status/error contracts and
reusable non-secret variables. This artifact check does not replace real HTTP,
authorization or persistence evidence.

For server-backed criteria, require evidence through the real application
boundary for the relevant authorization, persistence, transaction, events,
providers and retries. Mocked transport cannot prove a real integration claim.

For UI criteria, consume the required happy-path Playwright CLI interaction
assertions and inspected captures for the Spec's exact routes/states/viewports.
Check keyboard/focus, responsive behavior, final URL, console/network results and
relevant persisted effects. Screenshots do not prove authentication or persistence.
Negative, loading, empty, error, recovery and unusual outcomes belong in automated
tests. Do not add manual scenarios or captures during closure without an affected
contract or concrete correction that requires them. Code and visual review run
in parallel on the same candidate; no third serial reviewer is required.

## Verification ownership and failure loop

The designated Orchestrator verification runner owns affected server, browser and
job integration selections after implementation is fully integrated. Select local
tests only for scoped changes and directly affected consumers; conclusion does not
add unrelated suites. Broader selections require demonstrated dependency impact
or a concrete gap in that scope's proof. Full local suites require scope spanning
that suite or an explicit user request. Fix failures and rerun failed
or affected selections until required checks pass. Retain unaffected passing proof.
Applicable PR-head CI still executes its actual configured commands independently.

Consume current unit/component, lint, type, architecture, build, integration,
local changed-code coverage and manual evidence defined by the Spec and repository
Rules. Use only commands that
exist in manifests and tooling; never invent a generic checker or claim a
coverage percentage from a run that did not measure it.
Closure, reviewers, commit and PR workflows reuse that evidence. Additional runs
require a missing result, changed covered behavior/dependency/fixture/configuration,
or a concrete unresolved finding. Record skipped or environment-blocked checks
as limitations, never successes. Retry transient infrastructure failures only on
concrete evidence; keep unresolved external blockers explicit.

## Delivery disposition and lessons

Map selected PRD requirements through `RF-*` and `CA-*` to accepted evidence:

| RP/JN | RF coverage | CA coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- | --- |
| RP-01 / JN-01 | RF-01 | CA-01 | EV-01 | implemented | unchanged |

Use `implemented`, `partially_implemented`, `not_implemented` or `not_applicable`
with evidence. Partial delivery never counts as full implementation. Keep product
requirements canonical in Confluence; do not change checkboxes or Jira status
without an explicit request and the applicable authority workflow.

Record material findings as `ACH-*` with evidence, severity, affected checks,
status and resolution in Findings. Read Lessons Learned and identify lasting
guidance for Architecture, Modules, Design, Infrastructure, Tooling, Rules or
workflow guidance; keep feature-specific details local. State a concrete No change
reason when existing guidance is sufficient, rather than inventing a lesson.

For documentation updates beyond routine Spec/Evaluation closure, reuse explicit
scope/authorization already granted. Otherwise prepare the exact target, proposed
change, supporting ACH/EV lesson and reason, and obtain approval before applying
it. Permission to conclude alone does not authorize new global policy. Partial
approval covers only approved changes; external Jira/Confluence writes still need
explicit external-write authorization. Record proposed/applied/rejected/deferred
updates in Lessons Learned and Delivery. Optional deferred improvements do not
block closure; unresolved required alignment or material authority conflicts do.
Do not promote transient failures into global policy or silently weaken Rules.

## Complete artifacts and publish

Reconcile all seven Evaluation sections: Current State, Progress, Check Results,
Findings, Lessons Learned, Handoff and Delivery. Keep Spec Documentation Alignment
and Revision History accurate, with detailed observed proof and delivery state in
Evaluation. Preserve failed attempts, previous PR heads, evidence scope and current
process/dirty-path facts. Routine closure/status updates do not increment revision.
No `plan.md` is created, read or completed.

For local closure when publication is not requested or explicitly local-only,
set both artifacts `completed` after all local requirements pass; record
publication/current-head CI as not requested or not applicable, with the reason.
For authorized publication, retain Spec `implemented` and Evaluation `ready`
through commit/PR handoff until publication, required current-head CI and blocking
review conversations are resolved. A publication failure records a blocker and
must not be reported as completed delivery. Do not create a closure-only commit
solely for operational ledger updates; include required factual delivery
documentation in normal delivery commits.

For an explicitly authorized publication:

1. Verify the branch, synchronization result, scoped diff and current evidence.
2. Invoke `commit-code` to create scoped delivery commits; it must not push.
3. Invoke `create-pr` to push and create/update the same delivery PR, reusing the
   prepared commits and valid verification evidence.
4. Verify base, head SHA, title/body traceability and publication state; record
   branch, commit hashes and PR URL. Attach every created or updated delivery PR
   to the task using the available app artifact tool.

Do not create duplicate PRs or use ad hoc publication to bypass the workflow.
If publication is unavailable, report the blocker and retain the publication-ready
states; do not claim publication or completed authorized delivery.

For each current delivery PR head, inspect applicable checked-in CI workflow path
filters and current checks with authenticated `gh`; wait for terminal results and
record name, run URL, head SHA and result. Inspect repository state rather than
assuming workflows exist. Missing, pending, cancelled or earlier-head CI is not
passing current-head CI. If no applicable workflow exists, record not applicable.
A required current-head CI execution is distinct from repeating local suites.

For actionable CI failures, reopen Evaluation and route the correction through
`implement-spec`, refresh affected evidence, then commit and update the existing
PR when authorized. Rerun the same SHA only for a documented transient failure.
Do not change product disposition unless the failure establishes a product defect.

Complete published Spec/Evaluation only after all required current-head CI passes
and blocking review conversations have verified resolutions. Do not wait
indefinitely for hypothetical future feedback. Later PR feedback follows
`resolve-pr-feedback`; after merge, use the bug/change workflow. Do not merge the
delivery into `main` or deploy without separate authority.

## Output

Return concise clickable Spec, Evaluation and PR links; Spec revision and final
statuses; branch/commits and Jira/PRD references; criterion/checker coverage and
reused evidence; delivery dispositions; CI and publication state; resolved findings,
remaining limitations, factual documentation updates and preserved exclusions.
Claim only outcomes actually observed and recorded.
