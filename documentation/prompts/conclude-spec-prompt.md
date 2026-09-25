---
name: conclude-spec
description: Verify a Shifu delivery and complete its local SDD artifacts.
---

# Conclude a Shifu Spec

Close a validation-ready Shifu implementation in the current task. This workflow
owns final evidence reconciliation, delivery documentation, the commit-to-PR
publication handoff, and local SDD artifact completion. It does not implement
code or process later pull-request review feedback.

Conclusion is an active verification and correction loop. If an in-Contract
implementation correction is required, route it through implement-spec, wait for
current evidence and resume this workflow. Do not report a routine fix as a
suggested next step while authorized in-scope work remains.

An explicit `conclude-spec` request authorizes fetching the latest `main` from
the delivery branch's configured remote and merging it into the current delivery
branch as described below. This does not authorize merging the delivery branch
into `main` or deploying.

Pause for the user only when a product/technical Contract or higher-authority
decision is required, publication is unavailable, an external service blocks
progress, or the same actionable failure cannot be resolved within the
Orchestrator's bounded retry policy.

## Preconditions

Require all of the following before closure work begins:

- spec.md status is implemented and its exact revision is current;
- evaluation.md exists with status: ready, references the same Spec revision and
  implementation, and contains current evidence;
- direct implementation is complete, or every Plan phase/task is complete;
- every applicable RF-*/CA-*, VM-*, runtime, visual and automated check has
  current evidence or an explicit non-applicable disposition;
- no blocking implementation or Spec Reviewer finding remains;
- canonical PRD URL/content ID/version and Jira/source traceability still match;
- the complete integrated diff is available for inspection; and
- required services, accounts, fixtures and generated artifacts are available,
  or their limitations are explicitly recorded.

If a precondition fails, keep the relevant artifact status in draft,
in_progress or stale as applicable, record the concrete blocker and route it
through the authority rules below. Never mark a skipped, unsupported, stale or
unavailable gate as passed.

## Synchronize the delivery branch with main

Before final conformance validation, bring the latest `main` from the delivery
branch's configured remote into the current delivery branch. An explicit
`conclude-spec` invocation authorizes this synchronization merge; it does not
authorize merging the delivery branch into `main`.

1. Confirm the current branch is the delivery branch, not `main` or production.
   Identify its configured remote and verify that remote has the expected `main`
   branch. Do not assume a remote name when the repository configuration is
   ambiguous.
2. Inspect and classify staged, unstaged and untracked work. Preserve unrelated
   changes. Never reset, stash, autostash, switch branches or overwrite files to
   make the merge proceed. If Git cannot safely integrate `main` while
   preserving the current work, record the exact blocker and pause.
3. Fetch the remote's latest `main` and merge that ref into the current delivery
   branch. Do not rebase. Record the fetched commit and the resulting delivery
   branch SHA in evaluation.md.
4. If the merge has conflicts, immediately read and follow
   [`resolve-merge-conflicts-prompt.md`](resolve-merge-conflicts-prompt.md).
   Let that workflow resolve the conflicts, run all applicable checkers and
   stage only its task paths. Then resume conclude-spec, finish the pending
   synchronization merge with `git merge --continue`, and verify that the merge
   did not include unrelated work. If any checker fix changes the candidate,
   rerun affected checks before continuing.
5. Run the complete applicable validation gates against the synchronized
   candidate. Refresh Evaluation evidence for the resulting tree and SHA before
   closure. A failed fetch, missing remote `main`, unsafe dirty-worktree state,
   or unresolved conflict is a blocker; do not claim the Spec is completed.

Do not use `git pull` without naming and verifying its source: the current
branch's configured upstream may be the delivery branch's remote, not `main`.

## Workflow continuity and authority routing

Treat routes named by this workflow as immediate transitions inside the current
task, not as recommendations for the user to run later.

### Implementation correction

When the candidate does not satisfy the current Spec but the Contract is still
valid:

1. record the finding in evaluation.md as ACH-* with affected criteria and
   evidence;
2. mark affected EV-*/validation rows stale and set Evaluation to in_progress;
3. invoke implement-spec, which selects direct or Plan-backed execution and
   creates/resumes the responsible Builder;
4. let implementation refresh the affected evidence and return Evaluation to
   ready; and
5. resume this conclusion workflow from preflight.

Do not create a Builder or edit implementation files inside conclude-spec. Do
not erase failed attempts or replace a current finding with a narrative.

### Contract or authority change

When closure reveals changed behavior, a missing Contract obligation, a new
module/architecture decision, a changed PRD requirement or a global Rule gap:

1. keep the delivery in progress and record the discrepancy;
2. set the Spec to draft or stale according to whether its source authority or
   Contract requires reconciliation;
3. invoke create-spec for clarification and authority alignment;
4. obtain the required product, technical or user authority before any
   normative external or repository-wide change;
5. increment the Spec revision and reconcile Plan, Evaluation, paths, criteria,
   design references and validation; and
6. resume implementation and then conclusion through the normal lifecycle.

Do not silently change the PRD, Architecture, Modules, Design, Tooling, Rules,
ownership or acceptance Contract during conclusion. Do not mutate Confluence or
Jira unless the user explicitly requested that external action.

### Transient infrastructure or CI failure

Keep the Spec in_progress, record the exact command/run, environment, timestamp,
SHA and evidence, and retry only when there is concrete evidence the failure is
transient. A rerun must not conceal a product failure or stale candidate. If no
applicable CI workflow exists in the repository, record that fact as not
applicable; never invent a passing CI result.

## Final conformance preflight

Read the exact Spec Validation Contract, current Plan when present,
evaluation.md, documentation/sdd.md, documentation/tooling.md, the selected
Rules, the integrated diff and the complete canonical PRD again. Verify the
PRD content ID/version against the Spec. If the source version changed in a way
that affects the Contract, route to create-spec rather than closing the old
revision.

Inspect the complete worktree and documentation scope:

    git status --short
    git diff --stat
    git diff
    git diff --cached --stat
    git diff --cached
    git log -10 --format='%h %s'

Classify every changed path as delivery-owned implementation or test scope,
required factual documentation alignment, operational SDD ledger closure, or
unrelated user-owned work.

Inspect changed documentation paths even when no runtime code changed, including
Specs, Plans, Evaluations, PRDs, Architecture, Modules, Design, Tooling, Rules,
prompts and REST-client examples. Delivery-owned and required factual
documentation belongs in normal delivery commits and PR traceability; purely
operational closure updates may remain ledger-only according to the commit rules.
Preserve unrelated user-owned paths and record their explicit exclusion. Never
stage them by assumption.

Create a final implementation conformance record in evaluation.md containing:

- exact Spec path and revision;
- Builder/Plan scope matched against the complete diff;
- final allowed and prohibited paths;
- required file/widget tree and generated-file treatment;
- Contract obligations, exclusions and applicable UI states;
- current evidence IDs for every affected CA-* and VM-*;
- current automated, runtime, REST-client, manual and visual results; and
- all limitations, stale rows, accepted assumptions and unresolved findings.

Passing tests alone is not a conformance record. The record must establish that
the implementation matches the exact Spec, not merely that a subset of tests is
green.

## Acceptance and evidence reconciliation

Verify every RF-* and CA-* in both directions. For each criterion, confirm the
evidence is current for the exact implementation revision and identifies:

- command/test boundary and actual result;
- runtime request/response, persistence, authorization and side effects when
  server-backed;
- manual route, viewport, account/fixture, actions and expected result when
  VM-* applies;
- visual reference, exact state/viewport, fresh screenshot/artifact path and
  inspected differences when design-backed; and
- relevant ACH-* findings, stale evidence and resolution.

Maintain an acceptance matrix in evaluation.md with these columns:

| Acceptance | RF coverage | Automated evidence | Runtime/manual evidence | Visual evidence | Status |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | EV-01 | VM-01 / EV-02 | EV-03 or — | passed |

Use stable evidence identifiers. Do not reuse an old evidence ID for a changed
path or changed Contract. A correction invalidates affected evidence until the
corrected candidate is revalidated.

### HTTP and REST-client parity

For every affected route group, verify the matching
apps/server/rest-client/<module>/<route-group>.rest file is present, included in
the scoped delivery or explicitly created by the Contract, and contains:

- one current labeled request for every controller route in the group;
- current method, path, path/query parameters, headers and representative body;
- reusable local variables without credentials, private keys or real tokens; and
- parity with router/controller declarations, shared request schemas, response
  statuses and current error contracts.

Record the exact artifact path and comparison result in evaluation.md. REST
parity is artifact evidence; it does not replace real HTTP integration,
persistence or authorization evidence.

### UI and browser evidence

For every affected UI or browser surface, verify:

- exact Spec widget hierarchy and expected file tree;
- all required supplied and supplemental design states at their exact viewport;
- loading, empty, success, error, recovery, disabled, selected and pending
  behavior where applicable;
- semantic names, focus order, keyboard path, focus visibility, reduced motion,
  responsive/narrow-viewport behavior and pt-BR visible labels;
- fresh Playwright CLI screenshots for each acceptance-relevant design state;
- console errors, failed requests, HTTP statuses and final URL; and
- persistence/authentication/navigation effects that matter to the criterion.

Inspect every fresh screenshot. A screenshot supports visual assertions but does
not replace behavior, accessibility, network or persistence checks. Do not
require a feature-local evidence directory; record saved design references and
transient Playwright artifact paths in evaluation.md.

### Server-backed evidence

For every server-backed criterion, verify the real application boundary and the
relevant persistence, account/tenant authorization, transaction, event,
provider or retry result. Mocked transport is supporting evidence only and is
not sufficient for a real integration claim.

## Local validation gates

Run every applicable command named by the Spec, current Rules and
documentation/tooling.md. Use only commands that exist in current manifests.
Typical affected-workspace gates are:

    pnpm --filter web check:lint
    pnpm --filter web check:architecture
    pnpm --filter web check:types
    pnpm --filter web test:unit
    pnpm --filter web test:integration
    pnpm --filter web build

    cd apps/server
    uv run poe check:lint
    uv run poe check:architecture
    uv run poe check:types
    uv run poe test:unit
    uv run poe test:integration
    uv run poe build

Run focused checks first, then the broader applicable workspace gates. Every
affected Web or Server workspace must pass its available configured checks; do
not claim a coverage floor or test:coverage result when the repository does not
define one. Do not invent or claim a repository-wide
check:spec-implementation command.

Record each command exactly, including working directory, result, relevant
summary and any omitted command with its reason. A skipped, failed or
environment-blocked command prevents readiness unless the Evaluation records a
valid non-applicable disposition authorized by the Spec/Rules.

## Documentation and PRD traceability

Map every selected RP-* through the Spec's RF-* and CA-* criteria to current
Evaluation evidence:

| RP/JN | RF coverage | CA coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- | --- |
| RP-01 / JN-01 | RF-01 | CA-01, CA-02 | EV-01, VM-01 | implemented | unchanged |

Use only these local dispositions:

- implemented — the complete selected outcome and all mapped Contract obligations
  are delivered and evidenced;
- partially_implemented — only a bounded portion is delivered;
- not_implemented — selected but not delivered; or
- not_applicable — explicitly excluded or no longer applicable with evidence.

Partial or deferred delivery is never full implementation. Do not change a
Confluence checkbox or PRD status unless the user explicitly requests that
external mutation and the applicable authority workflow is followed.

Check factual documentation against delivered facts:

- update the applicable module PRD authority only when an authorized factual
  correction is required;
- update documentation/architecture.md for an accepted architectural/data-flow
  clarification;
- update documentation/rules/ for a reusable implementation/testing/tooling
  pitfall;
- update documentation/design.md for reusable visual/accessibility/responsive
  guidance; and
- update documentation/tooling.md for reusable command/environment/generation
  or CI guidance.

Product intent, Contract obligations, module ownership, Architecture and global
Rule changes require the authority route, not a silent closure edit.

## Findings and lessons learned

For every resolved or active material finding:

1. record the observed issue, evidence, severity, status and resolution in
   evaluation.md as ACH-*;
2. extract a reusable principle under Lessons learned when the finding could
   recur; and
3. decide the authority disposition in the same conclusion pass.

For each lesson, name the applicable Markdown authority file(s), make a factual
update when it is already consistent with the approved Contract, or record
No change with a concrete reason. If the lesson would change product intent,
architecture, ownership or a global policy, route it through create-spec or the
applicable authority workflow.

Do not create a durable documentation change for a transient environment
failure, isolated typo, already-covered Rule or feature-local detail that would
overfit global guidance. A finding without a lesson/disposition decision is
incomplete closure evidence.

## Commit and PR publication handoff

An explicit `conclude-spec` request authorizes the complete end-of-workflow
handoff: after local validation and SDD reconciliation, invoke `commit-code`
and then invoke `create-pr`. This is the standard completion path for a
validation-ready delivery. A user request for local-only conclusion is an
explicit override and skips both publication steps.

Before the handoff, confirm:

- the current task was explicitly invoked through `conclude-spec`, or the user
  separately authorized the equivalent commit and PR publication;
- the candidate is validation-ready and local SDD artifacts are reconciled;
- preserve unrelated changes and stage only exact delivery paths; and
- the synchronization merge from `main` into the delivery branch is authorized
  above; merging the delivery branch into `main` or deploying still requires a
  separate explicit request.

When the handoff is authorized:

1. ensure the branch follows the repository's actual branch strategy and is not
   main or production;
2. inspect the complete diff and documentation classification again;
3. invoke commit-code for intentional scoped commits, including required factual
   documentation but excluding unrelated user-owned work. `commit-code` must
   not push;
4. invoke create-pr to create or update one ready-for-review PR using the actual
   branch, the commits just prepared, Jira, Spec, Evaluation and validation
   metadata. `create-pr` owns the push and PR publication;
5. verify the PR base, head SHA, title/body traceability and publication state; and
6. record the branch, commit hashes and PR URL in the delivery record and
   evaluation.md when operationally relevant.

Do not bypass create-pr with an ad hoc PR edit. Do not create duplicate PRs. If
publication is unavailable, record the exact publication limitation and pause
the handoff rather than claiming a published PR. Local SDD artifacts may still
be completed when all local gates pass, but the conclusion summary must mark
commit/PR references unavailable.

## Pull-request CI gate

Run a PR CI gate only when a delivery PR exists and applicable checked-in
workflows are present. Shifu currently has no committed .github/workflows
directory, so do not invent Core, Server or Web workflow results. Record CI as
not applicable for the current repository state when no workflow is available.

When workflows are present and publication is authorized:

1. inspect checks attached to the current PR head SHA;
2. select workflows by their actual path filters and changed applications;
3. poll every applicable check until a terminal result;
4. record workflow/check name, result, run URL, head SHA and relevant summary in
   evaluation.md; and
5. record why each expected workflow is inapplicable when path filters exclude
   it.

A pending, in-progress, cancelled, missing or earlier-SHA run is not a pass. Use
authenticated gh CLI for GitHub context according to the repository workflow. A
local build or branch-push run does not substitute for the current PR head check.

If CI fails:

- record the failure and keep the Spec in_progress;
- classify it as implementation, Contract, transient infrastructure or
  evidence-only failure;
- route implementation/Contract corrections through the authority rules;
- after implement-spec returns Evaluation to ready, invoke commit-code when
  authorized, update the existing PR through create-pr, and rerun the gate on
  the new head SHA; and
- rerun the same SHA only for a documented transient failure.

Do not report an actionable failure as a suggested next step while the current
task can route it. Do not use CI failure to change product dispositions unless
it proves a product requirement failure.

## Complete the local SDD artifacts before publication

Only after all applicable validation, evidence and findings are resolved, and
before invoking `commit-code`:

- set evaluation.md to completed;
- set plan.md to completed, when present;
- set spec.md to completed and retain its concise outcome and a link to
  evaluation.md; and
- preserve detailed evidence, findings, lessons and delivery references in
  evaluation.md.

Do not create a closure-only commit solely to update operational SDD ledgers.
Create a normal delivery commit when implementation or required factual product
documentation needs committing. Closure-only artifact changes still belong in
the final local delivery state.

If a later review comment identifies actionable work, do not process it here.
Use resolve-pr-feedback while the PR is open. After merge, use the bug-fix
workflow for a defect or create a new Spec for changed behavior. This workflow
authorizes only the `main`-into-delivery synchronization described above; do not
merge the delivery branch into `main` or deploy unless separately requested.

## Conclusion summary

Return a concise, evidence-backed summary containing:

- clickable Spec, Plan when present, Evaluation and PR links;
- exact Spec revision and final local statuses;
- Jira/source, branch and commit references when present;
- validation result with CA-*, VM-*, runtime, REST-client and visual coverage;
- each selected RP-*/JN-* disposition and whether any PRD checkbox was
  intentionally unchanged;
- applicable local CI workflows/results or the explicit not-applicable reason;
- delivery documentation paths included and preserved unrelated exclusions;
- documentation alignment and remaining non-blocking limitations;
- finding-derived authority improvements and justified No change dispositions; and
- PR state and the next authorized action.

Do not claim completed status, accepted evidence, CI success, publication, merge
or deployment unless it was actually observed and recorded.
