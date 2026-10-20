---
title: Goal Planner proposal review evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-20
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01 … CA-11 (spec revision 2) |
| Automated checks | 7 / 7 passed: Vitest scope (60 files, 399 tests), scoped CI coverage run (28 files, 291 tests) with the changed-file gate green for 17 / 17 files, browser suite (26 scenarios, 9 of them for the review), `tsc`, `biome`, `depcruise`, route generation |
| Type / lint / complexity | `tsc --noEmit` clean; `biome check` clean on the delivery (7 pre-existing Mentor warnings untouched); `depcruise` 506 modules without violations |
| Manual checks | 0 / 1: VM-01 not run against the real model (`OPENROUTER_API_KEY` absent); the review was exercised with mocked transport only (EV-08) |
| Visual checks | 8 / 8 frames compared (EV-09) |
| Independent review | Pending (pull request review) |
| Blockers | None for the delivery; VM-01 needs the OpenRouter key |
| Candidate | Branch `feat/shifu-93` on top of `feat/shifu-92` (PR #34) and `feat/shifu-91` (PR #32): `e55b1bc` feature, `228c523` docs; PR #35 |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 (EV-01 review widget), CI-02 (EV-03 scenarios 1, 2), VM-02 (EV-09 `bzItW`, `gXrEP`) | None |
| CA-02 | RF-02 | Complete | Passed | CI-01 (EV-01 review hook and widget), CI-02 (EV-03 scenario 2), VM-02 (`zX9Ow`, `zCbC0`) | None |
| CA-03 | RF-03 | Complete | Passed | CI-01 (EV-01 graph hook: relation edges, root edges, circular guard), CI-02 (EV-03 scenario 2 asserts the nodes and their justifications) | None |
| CA-04 | RF-04 | Complete | Passed | CI-01 (EV-01 review hook), CI-02 (EV-03 scenario 3: message, `aria-invalid`, focus) | None |
| CA-05 | RF-09 | Complete | Passed | CI-01 (EV-01 review hook, page hook contract), CI-02 (EV-03 scenario 3: notice, no request) | None |
| CA-06 | RF-05 | Complete | Passed | CI-01 (EV-01 review widget, dialog hook), CI-02 (EV-03 scenario 4), VM-02 (`eSaNL`, `NxoN7`) | None |
| CA-07 | RF-06 | Complete | Passed | CI-01 (EV-01 dialog widget restores focus), CI-02 (EV-03 scenario 4: X, Esc, focus back, edits kept) | None |
| CA-08 | RF-07 | Complete | Passed | CI-01 (EV-01 page hook, server function), CI-02 (EV-03 scenario 4 asserts `{ planningId, initialIntent }`, the processing copy and the new batch), VM-02 (`SU4H8`, `lPCGg`) | None |
| CA-09 | RF-07 | Complete | Passed | CI-01 (EV-01 page hook conflict and unavailable), CI-02 (EV-03 scenario 5) | None |
| CA-10 | RF-08 | Complete | Passed | CI-02 (EV-03 scenario 6) | None |
| CA-11 | RF-10 | Complete | Passed | CI-02 (EV-03 scenario 7: arrow keys on the tabs, Enter opens, Esc closes, stacked actions, no horizontal scroll), VM-02 (mobile frames) | None |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated (Vitest) / CA-01 … CA-09 | Passed | `feat/shifu-93` working tree, 2026-10-20, jsdom | `apps/web`: `pnpm exec vitest run src/ui/intelligence src/rest src/ui/shared src/ui/learning/widgets/pages/goal-detail-page src/routes/intelligence src/constants` | 60 files, 399 passed. New: `planning-proposal-review.test.tsx` (9 cases, owning hook mocked, real graph/list/dialog composition with ReactFlow and ELK doubles, measured container for the wide and the compact geometry), `use-planning-proposal-review.test.ts` (6), `use-proposal-skill-graph.test.ts` (4: edges, sizing and circular relations, grid fallback, zoom bounds), `use-restart-planning-dialog.test.ts` (4), `restart-planning-dialog.test.tsx` (2: focus restore through the Radix unmount macrotask, submit and close). Updated: `use-planner-page.test.ts` (+3: restart success, refused restart, creation contract with and without consumer), `planner-page.test.tsx` (review composition, notice and busy state), `planning-server-functions.test.ts` (`restartPlanningServer` validation and the real `IntelligenceService` call), Learning `goal-skill-graph.test.tsx` (+1 case: init fit, zoom forwarding, restore, focus and hover) |
| EV-02 | CI-01 / Coverage / all | Passed | Same candidate | `apps/web`: `vitest run --coverage` over the 28 files listed in `web-app-ci.yaml` (291 passed), then `node --experimental-strip-types apps/web/scripts/check-changed-coverage.ts --files <17 changed web files>` | `Passed per-file coverage thresholds for 17 changed eligible Web source file(s)`. Highlights: `use-proposal-skill-graph.ts` 98.2 % lines / 85.5 % branches, `use-planner-page.ts` 99.4 % / 93.9 %, `intelligence-service.ts` 95.1 % lines / 83.3 % branches, Learning `goal-skill-graph/index.tsx` 22 / 23 lines once its test entered the CI list (ACH-06) |
| EV-03 | CI-02 / Automated (Playwright, mocked `_serverFn`) / CA-01 … CA-11 | Passed | Same candidate, local FastAPI 7777 + Vite 7000 reused, Chromium 1440 × 900 and 390 × 844 | `apps/web`: `pnpm test:integration tests/intelligence/planner-page.test.ts` (`PLANNER_CAPTURE_DIR` set for the captures) | Review subset (`--grep review`) 9 passed in 22 s; whole planner suite 26 passed in 1.5 min, so the SHIFU-92 scenarios survive the new transport (`restartPlanningServer`), the tree-shaped fixture and the capture helper. Scenario numbers used above: 1 CA-19 surface, 2 graph/list, 3 validation and notice, 4 restart, 5 refused restart, 6 cancel, 7 mobile keyboard, 8 and 9 frame walks |
| EV-04 | CI-03 / Types / all | Passed | Same candidate | `apps/web`: `pnpm check:types` | Clean |
| EV-05 | CI-03 / Lint and format / all | Passed | Same candidate | `apps/web`: `pnpm check:lint`; `biome check` on the touched directories | 7 warnings, all pre-existing in Mentor files; delivery files clean after formatting the generated test imports |
| EV-06 | CI-03 / Architecture / all | Passed | Same candidate | `apps/web`: `pnpm check:architecture` | No dependency violations (506 modules, 1789 dependencies) |
| EV-07 | CI-03 / Route generation / all | Passed | Same candidate | `apps/web`: `pnpm generate-routes` | No route change (the review lives in the existing planner route); the local generator only strips the `Register` augmentation, restored with `git checkout` |
| EV-08 | VM-01 / Manual / CA-08 | Not run | Local FastAPI without `OPENROUTER_API_KEY` | Open a planning, reach a real proposal, restart with a new intention | Without the key the backend cannot produce a proposal, so the review and the live restart were not exercised against the real model; the restart route itself is covered by the SHIFU-91 server suites and the page behavior by EV-01/EV-03 mocks. Limitation recorded in Delivery |
| EV-09 | VM-02 / Visual / CA-01, CA-02, CA-06, CA-08, CA-11 | Passed | Same candidate, captures from EV-03 | Pencil `Export` at scale 1 (8 PNG in `design/`), `Get` with `ctx.problems` (0 problems in the 8 frames), captures in `design/captures/`, side-by-side images in `design/comparisons/` built with Pillow | After ACH-01 … ACH-04 the structure, column width, spacing, typography, tokens, copy, tree shape and zoom (100 %) match in all 8 pairs; remaining deviations are listed in `design/handoff.md` (single Skill icon, no progress bar or menu, centered tree, edge style, focus ring, shell extras) |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | The review rendered inside the 760 px column of the interview while its frames use a 1170 px column; the graph was 760 px wide and fell into the compact geometry on desktop (CA-01) | Medium | EV-09 | Resolved: `PlannerPage` widens the column to 1170 px for the `proposal` view only (D7); desktop captures redone |
| ACH-02 | ELK's horizontal placement offset the root and the converging node, so the fit zoom landed at 90–92 % instead of the drawn 100 % and the tree was not centered (CA-01, CA-11) | Medium | EV-09 | Resolved: every layer is centered on the widest one after the ELK pass and the tree hangs from the top inset at zoom 1 when it fits (D8); hook tests assert the centered positions |
| ACH-03 | Dialog captures were taken mid-animation (transparent content, no overlay) and tall frames were cut at the viewport height | Low | EV-09 | Resolved: captures fast-forward animations and use a viewport as tall as the document for the graph and list frames |
| ACH-04 | Mobile frame geometry (two 151 px nodes sharing the row, full-width root and converging node, icon above the name) was not reproduced by the fixed 360 px nodes | Medium | EV-09 | Resolved: the geometry follows the measured box width (D8) with per-layer widths; component test covers the compact case |
| ACH-05 | Esc fired `onClose` twice (`onEscapeKeyDown` plus `onOpenChange`) | Low | EV-01 | Resolved: a single `onOpenChange` path; widget test asserts one call per gesture |
| ACH-06 | Coverage gate: the dialog's focus-restore lines and the graph fallback branch were not exercised by Vitest, and the Learning graph widget (changed by the shared zoom controls) had no test in the CI coverage list | Low | EV-02 | Resolved: `restart-planning-dialog.test.tsx` and a fallback case added; Learning `goal-skill-graph.test.tsx` extended and listed in `web-app-ci.yaml` |
| ACH-07 | Two `status` live regions coexist on the review (zoom output and creation notice), which broke `getByRole('status')` queries | Low | EV-01 | Resolved in the tests: the notice is located by its text and its `output` element |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Measure the frames in Pencil (`Get` with `padding`, `gap`, sizes, `content` of text nodes) before coding a graph: layout engines do not reproduce a drawn tree by default | ACH-01, ACH-02, ACH-04 | Recorded in the handoff; spec decisions D7 … D9 |
| Capture dialogs with `animations: 'disabled'` and tall frames on a document-tall viewport | ACH-03 | Local to the suite |
| Promoting a Learning widget to `ui/shared` pulls the Learning consumers into the changed-file gate; their tests must be in the CI coverage list | ACH-06 | `web-app-ci.yaml` updated |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-93` on top of `feat/shifu-92` (`1180df3`): `e55b1bc` feature, `228c523` docs, then the delivery-state commit |
| Completed | CA-01 … CA-11 implemented; EV-01 … EV-07, EV-09 passed |
| Unfinished | VM-01 with the real model (needs `OPENROUTER_API_KEY`); `Criar objetivo` confirmation belongs to SHIFU-95 |
| Uncommitted work | None after the delivery commits |
| Active processes | Local FastAPI (7777) and Vite (7000) started for EV-03 may still be running; stop them when done |
| Blockers | None |
| Next action | Watch CI of #35; address review; rebase when #31, #32 and #34 merge; SHIFU-95 consumes `PlannerPage.onCreateGoal` |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-09; JN-07, JN-08 | RF-01 … RF-03, RF-10 / CA-01 … CA-03, CA-11 | EV-01, EV-03, EV-09 | implemented |
| RP-10; JN-09 | RF-04 … RF-07, RF-09 / CA-04 … CA-09 | EV-01, EV-03, EV-09 | partially_implemented: review, direct edits, restart and the creation contract delivered; the confirmation call is SHIFU-95; live model restart pending the OpenRouter key |
| RP-07; JN-12 | RF-07, RF-08 / CA-08 … CA-10 | EV-01, EV-03 | implemented |
| RP-12 | RF-10 / CA-11 | EV-03, EV-09 | implemented |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/35 | `228c523` (the docs commit that records this state follows) | Pending: CI queued; review pending | https://github.com/CtrI-Alt-Del/shifu/pull/35/checks |

| Field | Result |
| --- | --- |
| Publication | published: PR #35 opened against `main` on 2026-10-20 (stacked on #34, #32 and #31); SHIFU-93 moved to Code Review |
| Source verification | SHIFU-93 description (Jira) and PRD Intelligence v4 (Confluence 83099649) read on 2026-10-20; frames read and measured from `design/shifu.pen` through Pencil |
| Documentation Alignment | `spec.md` revision 2 (D6 … D9); `../planner-interview/spec.md` revision 2 (handoff replaced by the review); `design/handoff.md` manifest with 8 pairs; no rule change |
| Revision History | Spec revision 2 during implementation (frame measurements) |
| Limitations | Real-model review and restart not run locally (no `OPENROUTER_API_KEY`); one `graduation-cap` icon for every Skill; no progress bar or menu in the proposal nodes; tree centered instead of left-aligned on desktop |
