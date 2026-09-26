---
title: SHIFU-68 skill removal evaluation
status: completed
spec: ./spec.md
spec_revision: 2
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-68
prd_content_id: '83066881'
prd_version: '21'
last_updated_at: 2026-09-26
---

# Evaluation status

The integrated implementation passed its automated gates, independent review
and user acceptance. The user tested the running feature and confirmed on
2026-09-26 that removal works correctly. The delivery was then moved to
`codex/SHIFU-68-skill-removal` for scoped commits.

| Field | Current state |
| --- | --- |
| Implementation | `completed` |
| Governing Spec | revision 2, `completed` |
| Plan | `completed`; F0–F4 complete |
| Baseline | `main == origin/main == fa893802f637b345a5456c5d94918249615f67d4` at kickoff |
| Branch | `codex/SHIFU-68-skill-removal` |
| User acceptance | Running feature tested; user confirmed removal behaves correctly |
| Next action | Create scoped local commits; PR publication is not part of this authorization |

# Acceptance coverage

| Criterion | Evidence | Status |
| --- | --- | --- |
| CA-01 | Removal use case plus real HTTP/PostgreSQL 204 and cascade assertions | `passed` |
| CA-02 | Private 404 for missing/not-owned/repeated removal with preservation assertions | `passed` |
| CA-03 | Unauthenticated integration request rejected and rows preserved | `passed` |
| CA-04 | All statuses plus pending/failed evaluation and legacy/v2 dependent rows covered | `passed` |
| CA-05 | Goal, sibling, same Skill in another Goal and Curriculum preservation covered | `passed` |
| CA-06 | Forced rollback and coordinated concurrent transactions complete without deadlock | `passed` |
| CA-07 | Real Inngest late-event test is stale/no-op after domain removal | `passed` |
| CA-08 | Shared menu/dialog exercised on SkillPage, Lista and Grafo | `passed` |
| CA-09 | Cancel/Escape emits no request and restores trigger focus | `passed` |
| CA-10 | Pending deduplicates; error remains visible and retryable | `passed` |
| CA-11 | Lista/Grafo removal preserves selected view and siblings | `passed` |
| CA-12 | SkillPage success returns to the same Goal graph | `passed` |
| CA-13 | Keyboard/focus/pt-BR/mobile no-horizontal-scroll route coverage | `passed` |

# Automated gates

| CI ID | Command/sensor | Result | Status |
| --- | --- | --- | --- |
| CI-01 | `cd apps/server && uv run poe check:lint` | clean | `passed` |
| CI-02 | `cd apps/server && uv run poe check:architecture` | clean | `passed` |
| CI-03 | `cd apps/server && uv run poe check:types` | clean | `passed` |
| CI-04 | `cd apps/server && uv run poe test:unit` | 132 passed | `passed` |
| CI-05 | `cd apps/server && uv run poe test:integration` | 94 passed | `passed` |
| CI-06 | `cd apps/server && uv run poe test:jobs` | 7 passed | `passed` |
| CI-07 | `cd apps/server && uv run poe build` | sdist and wheel built | `passed` |
| CI-08 | `pnpm --filter web check:lint` | 269 files clean | `passed` |
| CI-09 | `pnpm --filter web check:architecture` | 265 modules / 910 dependencies, no violations | `passed` |
| CI-10 | `pnpm --filter web check:types` | clean | `passed` |
| CI-11 | `pnpm --filter web test:unit` | 51 files / 238 tests passed | `passed` |
| CI-12 | Focused Playwright route suites | 22 passed after review corrections | `passed` |
| CI-13 | `pnpm --filter web build` | built; existing chunk-size warnings only | `passed` |
| CI-14 | Controller-to-`learning.rest` parity audit | all 18 registered controller routes represented; scenario variants retained | `passed` |
| CI-15 | Playwright CLI request/DOM/URL/focus/mobile assertions | focused affected routes passed | `passed_automated` |

The complete 100-test Playwright run produced 88 passes and 12 failures outside
the SHIFU-68 surfaces. The dominant environment failure was a stale shared local
database missing `identity_account_action_tokens.communication_id`; unrelated
Identity/material timeouts followed. Both affected Learning route files were
then run together and passed 22/22 after review corrections. React Flow's pre-existing attribution warning
also remains visible in webServer output.

# Manual and visual evidence

| Scenario | Expected | Automated observation | Manual status |
| --- | --- | --- | --- |
| VM-01 SkillPage desktop | menu/dialog, one DELETE, recoverable error, same-Goal graph | automated flow passed; user accepted running removal behavior | `passed` |
| VM-02 SkillPage 390 × 844 | no clipping/scroll; keyboard/focus usable | narrow viewport assertions passed; user accepted behavior | `passed` |
| VM-03 GoalDetail Lista | removed row disappears; sibling/list view remain | request and same-view assertions passed; user accepted behavior | `passed` |
| VM-03 GoalDetail Grafo | node/relations disappear; sibling/graph view remain | user-provided running screenshot plus automated selected-view/removal assertions | `passed` |
| Supplemental pending/error | disabled/busy, no duplicate; retryable error | component and route assertions passed | `passed` |

The user supplied a fresh screenshot of the running GoalDetail Grafo and then
confirmed the removal behavior works correctly. No additional screenshots were
persisted in the repository; the other states rely on the saved design bundle,
Playwright DOM/request/focus assertions and explicit user acceptance.

# Review findings

Exactly one integrated Implementation Reviewer was activated after the automated
candidate existed. Its three P2 findings were corrected and the affected unit,
type and Playwright gates were rerun. The P3 lockfile note is accepted: pnpm
11.25.0 generated platform `libc` annotations and transitive `supports-color`
normalization together with the required DropdownMenu graph; the package change
itself remains limited to the declared dependency and supply-chain policy passed.

| ACH ID | Classification | Source | Affected evidence | Status | Resolution |
| --- | --- | --- | --- | --- | --- |
| ACH-01 | P2 duplicate submission race | Implementation Reviewer | CA-10 | `resolved` | Synchronous ref mutex added to both page controllers; unit and route double-activation coverage passed |
| ACH-02 | P2 missing Grafo success evidence | Implementation Reviewer | CA-11 | `resolved` | Added Grafo success route test proving node disappearance and selected view; 22/22 passed |
| ACH-03 | P2 incomplete retry/destination evidence | Implementation Reviewer | CA-10, CA-12 | `resolved` | Mobile route now proves fail→retry→success, exact request count, final Goal URL and removed item absence |
| ACH-04 | P3 generated lockfile churn | Implementation Reviewer | F0 hygiene | `accepted` | Generated by repository pnpm 11.25.0; supply-chain check and all web gates pass; no hand edit performed |

# Evidence log

| EV ID | Scope | Result | Acceptance mapping |
| --- | --- | --- | --- |
| EV-01 | Focused Core/controller/job pytest | 19 passed, 1 expected skip outside real-job mode | CA-01–CA-07 |
| EV-02 | Full server unit/integration/jobs/build/static gates | 132 + 94 + 7 passed; build/static clean | CA-01–CA-07 |
| EV-03 | Full web unit/static/build gates | 238 passed; lint/architecture/types/build clean | CA-08–CA-13 |
| EV-04 | Focused affected Playwright routes | 22 passed in 37.6 s after reviewer corrections | CA-08–CA-13 |
| EV-05 | Full Playwright classification | 88/100 passed; 12 unrelated environment failures classified above | non-blocking baseline context |
| EV-06 | `git diff --check` and REST parity | clean; all registered Learning routes represented | complete candidate hygiene |
| EV-07 | User acceptance on running local stack | removal confirmed correct; fresh Grafo screenshot supplied in task | VM-01–VM-03, CA-08–CA-13 |

# Final conformance record

- Spec: `documentation/features/learning/skill-removal/spec.md`, revision 2.
- Allowed delivery paths are exactly the Server/Web/REST client/dependency/SDD
  paths declared by the Spec; no environment, credential, database, browser
  storage, coverage or runtime artifact is included.
- Server obligations cover authenticated private removal, atomic cascade,
  rollback, isolation, global lock order and late-event no-op.
- Web obligations cover the shared menu/dialog, all Skill states, Lista/Grafo,
  pending/error/retry, synchronous duplicate protection, focus/keyboard/mobile,
  view preservation and same-Goal navigation.
- RP-03, RP-21 and JN-14 are `implemented`; RP-25 is `implemented` for this
  feature boundary; JN-03 remains `partially_implemented` by the Spec's bounded
  scope. No external PRD checkbox was changed.
- CI publication is not applicable: the repository has no checked-in
  `.github/workflows` directory and no PR was requested or created.
- The full Playwright baseline limitation and generated pnpm lockfile
  normalization remain recorded above and are non-blocking for this delivery.
