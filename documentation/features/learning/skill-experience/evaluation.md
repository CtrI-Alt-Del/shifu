---
title: Learning Skill Experience — Evaluation
status: ready
revision: 1
spec: ./spec.md
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-66
last_updated_at: 2026-09-25
---

# 1. Delivery disposition

| PRD requirement | Disposition | Note |
| --- | --- | --- |
| Learning `RP-05` | `implemented` | The page presents the Skill's situation, overall result and focus. |
| Learning `RP-08` | `implemented` | Released Competencies open; a blocked one explains its requirement without leaving the page. |
| Learning `RP-13` | `implemented` | A running evaluation shows progress without any final result. |
| Learning `RP-14` | `implemented` | A failed evaluation preserves the attempt and recovers through the retry endpoint SHIFU-74 delivered. |
| Learning `RP-15` | `partial` | Competency-level progress and the Skill average are implemented. The Concept-level model is out of scope by `D1`. |
| Learning `RP-16` | `partial` | Status bands, mastery thresholds, focus and permanent release are implemented. Regression verification is out of scope by `D1`. |
| Learning `RP-17` | `implemented` | The recommendation is the focus Competency's, never recomputed, and is suppressed while an evaluation holds the Skill. |
| Learning `RP-25` | `implemented` | pt-BR, desktop and mobile, keyboard, visible focus, no colour-only state. |

# 2. Quality gates

| ID | Command | Result |
| --- | --- | --- |
| `CI-01` | `uv run poe check:lint` (`apps/server`) | `ruff check` and `ruff format --check` clean over `src` and `tests`. |
| `CI-02` | `uv run poe check:types` | 0 errors, 0 warnings, 0 notes. |
| `CI-03` | `uv run poe check:architecture` | All modules validated by `tach`. |
| `CI-04` | `uv run poe test:unit` | 126 passed; 16 of them new. |
| `CI-05` | `uv run pytest tests/learning/server -p no:tach` | 53 passed against real PostgreSQL; 9 of them new. The `poe` task reports the suite as skipped when `tach` impact analysis finds no affected module, so it was run with the plugin disabled. |
| `CI-06` | `pnpm --dir apps/web check:types` | Clean. |
| `CI-07` | `pnpm --dir apps/web check:lint` | Clean over 265 files. |
| `CI-08` | `pnpm --dir apps/web check:architecture` | No dependency violations, 260 modules cruised. |
| `CI-09` | `pnpm --dir apps/web test:unit` | 50 files, 230 tests pass; 9 of them belong to this feature. |
| `CI-10` | `pnpm --dir apps/web test:integration` | `tests/learning` 45 passed with `--workers=1`, 8 of them new. The repository-wide parallel run is not green on this machine; see `ACH-01`. |

# 3. Acceptance matrix

| CA | Evidence |
| --- | --- |
| `CA-01` | `CI-04` rejects a Goal of another account before reading Curriculum; `CI-05` `test_goal_of_another_account_is_a_private_absence`. |
| `CA-02` | `CI-05` returns `{"code":"not_found","message":"Recurso não encontrado."}` for an absent Skill and for another account. |
| `CA-03` | `CI-05` asserts name, `skillStatus`, `overallResult` and focus; `CI-09` asserts the rendered header; `VM-01`. |
| `CA-04` | `CI-05` asserts progress, status and availability per row; `CI-09` asserts the rendered list. |
| `CA-05` | `CI-05` reads the seeded values the domain computed: 90, 55 and 90. |
| `CA-06` | `CI-05` `test_overall_result_averages_every_competency` compares the payload against the mean of the rows, blocked included; `CI-04` covers a blocked Competency contributing zero. |
| `CA-07` | `CI-05` asserts `mastered`, `developing` and `mastered` for the seeded experience. |
| `CA-08` | Enforced by `CompetencyProgress`; `CI-04` exercises a mastered row at 92 with a hard score of 90. |
| `CA-09` | `CI-04` `test_should_focus_the_first_competency_that_is_not_mastered`; `CI-05` asserts the focus is `Estruturas de repetição`. |
| `CA-10` | The payload derives availability from `content_released`, which the domain never clears; `CI-04` covers a released Competency below its previous progress. |
| `CA-11` | `CI-04` asserts the recommendation is the composed Competency detail's; `CI-05` compares it field by field with the Competency endpoint. |
| `CA-12` | `CI-09` and `CI-10` assert the four identifiers in the destination. |
| `CA-13` | `CI-09` and `CI-10` assert the alternative opens the focus Competency route. |
| `CA-14` | `CI-09` and `CI-10` assert the released row is a link to its detail route. |
| `CA-15` | `CI-09` and `CI-10` assert a blocked row is a button, that no link exists for it, and that selecting it keeps the route and announces the requirement. |
| `CA-16` | `CI-04` suspends the recommendation while an evaluation holds the Skill; `CI-09` and `CI-10` assert the running notice and the absent recommendation. |
| `CA-17` | `CI-04` keeps every Competency in the payload during a held evaluation; `CI-10` asserts the three rows stay reachable. |
| `CA-18` | `CI-09` asserts the retry handler is called once from the failed state; the retry itself is SHIFU-74's endpoint and its suites. |
| `CA-19` | `CI-10` covers the absence and the failure surfaces of the route. |
| `CA-20` | `CI-10` focuses the primary action and asserts no horizontal scroll at 375 × 812. |
| `CA-21` | Every state carries a text label beside its colour: the status pills, `Em foco`, `Bloqueada` with a lock icon, and the three threshold marks inside the progress bar. |

# 4. Manual validation

### `VM-01` — Visual comparison against the twelve frames

The Pencil frames were exported at scale `1` into `design/` and compared node by node
against the implementation rendered with the same data. Side-by-side captures were
produced for the base, running-evaluation, failed-evaluation and mobile states. The
comparison and its deltas are recorded in `design/handoff.md`.

### `VM-02` — Rendered states

The four states above were rendered through the real page composition with the
transport mocked at the BFF boundary, at 1440 × 900 and at 390 × 844, and inspected.
Layout holds at both widths and no state depends on colour alone.

# 5. Findings

| ID | Severity | Status | Description |
| --- | --- | --- | --- |
| `ACH-01` | Medium | Open, pre-existing | The repository-wide `pnpm --dir apps/web test:integration` is not green on this machine: `tests/identity/sign-in-auth-handler.test.ts` and `tests/identity/register-confirmation-auth-handler.test.ts` fail identically on a clean `main` checkout, and several other suites flake under the default worker count while passing with `--workers=1`. Verified by stashing this delivery and reproducing the same six identity failures on `main`. Not caused by this delivery and left untouched. |
| `ACH-02` | Low | Accepted | The frame draws the blocked badge with a `lock` icon; the shared `Icon` registry offers `lock-keyhole`, which was used instead. Extending the registry for one glyph belongs to the design system. |
| `ACH-03` | Low | Accepted | The frame draws the failed-evaluation chip with `alert-triangle`, which is not registered; `circle-alert` was used, matching what `CompetencyDetailFeedback` and `MaterialFeedback` already render for the same meaning. |
| `ACH-04` | Low | Open, out of scope | The `uyfWq` frame is the *menu aberto* variant, so it shows the Skill actions menu expanded. This delivery renders the trigger button only, because every item of that menu belongs to SHIFU-36. |

# 6. Conclusion

Every `CA-*` has accepted evidence. `RP-15` and `RP-16` are partial by the declared
scope decision `D1`, which the Spec records and the ticket's own acceptance criteria
support. `ACH-01` is a pre-existing environment failure proven against `main`. The
recommendation shown by this page is the same object the Competency page serves, and the
recovery of a failed evaluation reuses the endpoint SHIFU-74 delivered rather than
duplicating it.
