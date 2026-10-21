---
title: Ditado nativo do navegador para o Mentor — evaluation
status: ready
spec: ../../../../.specs/features/shifu-105-mentor-dictation/plan.md
last_updated_at: 2026-10-13
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for AC-01–AC-35 in the TLC plan revision10. |
| Automated checks | 39/39 active checks passed; C34 is retired by the user's revision9 decision. |
| Type / lint / complexity | TypeScript, lint, architecture and build commands passed. Lint reported seven warnings and the existing missing `apps/web/scripts` directory diagnostic. No quantitative complexity or changed-code coverage gate is configured for this delivery; changed-code coverage enforcement was removed at the user's request. |
| Manual checks | Browser CLI happy path is represented by current page/FAB desktop/mobile captures with controlled native recognition events. No real speech-quality claim is made. |
| Visual checks | Pass: 12 captures across page/FAB, 1440/390 widths and recording/transcribing/review states, checked against the six approved Pencil references. |
| Independent review | Current independent verification report: `.specs/features/shifu-105-mentor-dictation/verification.md`; 39/39 checks pass. |
| Blockers | None. Browser-provider ZDR eligibility is outside this feature's scope by explicit user decision and is not a PRD v9 condition for browser-managed recognition. |
| Candidate | [PR #24](https://github.com/CtrI-Alt-Del/shifu/pull/24), branch `feat/shifu-105`; use the live PR head as the current delivery SHA. The implementation and acceptance evidence remains anchored to `fca644557f5f829a340578074b46bfc63748a466`; the earlier documentation handoff was `e84221787c4386f2ac42d3ecbac965511e9a14ce`. Local unrelated changes are excluded. |

# Progress

The TLC contract uses AC/C identifiers rather than RF/CA. Implementation and
verification below map to those exact identifiers; no second requirement set is
introduced.

| AC | RP coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| AC-01 | RP-06 | Complete | Passed | C1 / EV-01, EV-02 | None |
| AC-02 | RP-06 | Complete | Passed | C2 / EV-01 | None |
| AC-03 | RP-06, RP-12 | Complete | Passed | C3 / EV-01, EV-02, EV-03 | None |
| AC-04 | RP-06 | Complete | Passed | C4 / EV-01 | None |
| AC-05 | RP-06 | Complete | Passed | C5 / EV-01 | None |
| AC-06 | RP-06, RP-12 | Complete | Passed | C6 / EV-01, EV-03 | None |
| AC-07 | RP-06 | Complete | Passed | C7 / EV-01 | None |
| AC-08 | RP-06, JN-01 | Complete | Passed | C8 / EV-01 | None |
| AC-09 | RP-06 | Complete | Passed | C9 / EV-01 | None |
| AC-10 | RP-03, RP-06 | Complete | Passed | C10 / EV-01 | None |
| AC-11 | RP-06 | Complete | Passed | C11 / EV-01 | None |
| AC-12 | RP-06 | Complete | Passed | C12 / EV-01 | None |
| AC-13 | RP-06 | Complete | Passed | C13 / EV-01 | None |
| AC-14 | RP-06 | Complete | Passed | C14 / EV-01 | None |
| AC-15 | RP-06 | Complete | Passed | C15 / EV-01 | None |
| AC-16 | RP-06 | Complete | Passed | C16 / EV-01 | None |
| AC-17 | RP-06 | Complete | Passed | C17 / EV-01 | None |
| AC-18 | RP-06 | Complete | Passed | C18 / EV-01 | None; conditional attachment collection is absent in this base. |
| AC-19 | RP-03, RP-06, RP-11 | Complete | Passed | C19 / EV-01 | None |
| AC-20 | RP-03, RP-06 | Complete | Passed | C20 / EV-01 | None |
| AC-21 | RP-06 | Complete | Passed | C21 / EV-01 | None |
| AC-22 | RP-06 | Complete | Passed | C22 / EV-01 | None |
| AC-23 | RP-06 | Complete | Passed | C23 / EV-01 | None |
| AC-24 | RP-06, RP-13 | Complete | Passed | C24 / EV-01 | None; proof establishes zero Shifu/OpenRouter audio payloads. |
| AC-25 | RP-06, RP-11 | Complete | Passed | C25 / EV-01 | None; proof establishes no Shifu audio files/blobs/records. |
| AC-26 | RP-06 | Complete | Passed | C26 / EV-01 | None |
| AC-27 | RP-06, RP-12 | Complete | Passed | C27 / EV-01, EV-02 | None |
| AC-28 | RP-06 | Complete | Passed | C28 / EV-01 | None; conditional local-mode hook regression only. |
| AC-29 | RP-06 | Complete | Passed | C29 / EV-01 | None; conditional local-mode hook regression only. |
| AC-30 | RP-06 | Complete | Passed | C30 / EV-01 | None; conditional local-mode hook regression only. |
| AC-31 | RP-06 | Complete | Passed | C31 / EV-01 | None; conditional local-mode hook regression only. |
| AC-32 | RP-12 | Complete | Passed | C32 / EV-01, EV-02 | None |
| AC-33 | RP-06, RP-12 | Complete | Passed | C33 / EV-02, EV-03 | None |
| AC-34 | RP-06 | Complete | Passed | C35 / EV-01 | None; C34 is retired and is not this criterion. |
| AC-35 | RP-06 | Complete | Passed | C40 / EV-01, EV-02, EV-03 | None; cloud-processing disclosure remains required. |

# Check Results

| EV | Check / type / coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | Unit/component / Automated / AC-01–AC-35 | Passed | `fca644557f5f829a340578074b46bfc63748a466`, 2026-10-13; controlled native API | `cd apps/web && pnpm test:unit src/ui/intelligence/contexts/mentor-context/tests/mentor-dictation-consumer.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/use-composer.test.ts --reporter=verbose` | 80 tests across three files passed. Tests cover both page/FAB consumer behavior and the shared hook; they do not establish real recognition accuracy or browser-provider privacy. |
| EV-02 | Browser integration / Automated / AC-01, AC-03, AC-27, AC-32, AC-33, AC-35 | Passed | `fca644557f5f829a340578074b46bfc63748a466`, 2026-10-13; page/FAB, 1440/390 and no-local-language-pack cases | `cd apps/web && pnpm test:integration tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts --grep 'renders native dictation states'` | Six browser cases passed. Recognition events are controlled; this proves the routed UI flow and unavailable-language fallback, not real speech processing. |
| EV-03 | Visual / Visual / AC-03, AC-06, AC-33, AC-35 | Passed | `fca644557f5f829a340578074b46bfc63748a466`, captures from 2026-10-13 | `python3 .specs/features/shifu-105-mentor-dictation/verify-evidence.py --filter visual` from repository root | Twelve page/FAB captures at 1440/390 for recording/transcribing/review pass the six saved Pencil references. Artifacts: `.specs/features/shifu-105-mentor-dictation/visual-evidence.json` and `apps/web/.playwright-cli/screenshots/shifu-105-cli-{page,fab}-{1440,390}-{recording,transcribing,review}.png`. |
| EV-04 | TypeScript / Automated baseline | Passed | `fca644557f5f829a340578074b46bfc63748a466`, 2026-10-13 | `cd apps/web && pnpm check:types` | Exit 0. |
| EV-05 | Lint and configured complexity rules / Automated baseline | Passed with warnings | `fca644557f5f829a340578074b46bfc63748a466`, 2026-10-13 | `cd apps/web && pnpm check:lint` | Exit 0; seven warnings and the existing missing `apps/web/scripts` directory diagnostic. No separate quantitative complexity score is claimed. |
| EV-06 | Dependency architecture / Automated baseline | Passed | `fca644557f5f829a340578074b46bfc63748a466`, 2026-10-13 | `cd apps/web && pnpm check:architecture` | Exit 0; 438 modules and 1,479 dependencies reported. |
| EV-07 | Production build / Automated baseline | Passed | `fca644557f5f829a340578074b46bfc63748a466`, 2026-10-13 | `cd apps/web && pnpm build` | Exit 0; client and SSR output completed. |
| EV-08 | TLC plan/check/evidence gates / Automated documentation | Passed | Current worktree, 2026-10-13 | `python3 .agents/skills/tlc-spec-lean/scripts/validate_plan.py shifu-105-mentor-dictation`; `python3 .agents/skills/tlc-spec-lean/scripts/validate_checks.py shifu-105-mentor-dictation`; `python3 .agents/skills/tlc-spec-lean/scripts/validate_verification.py shifu-105-mentor-dictation` | All exit 0. `validate_checks.py` retains four documented selector warnings for command-level type/lint/architecture/build checks. |
| EV-09 | Commit message validation / Automated documentation | Repository commitlint passed; TLC checker conflict retained | Current worktree, 2026-10-13 | `python3 .agents/skills/tlc-spec-lean/scripts/check_commit.py --message 'docs: SHIFU-105 reconcile dictation contract with PRD v9'`; `printf '%s\n' 'docs: SHIFU-105 reconcile dictation contract with PRD v9' \| pnpm exec commitlint` from repository root | `check_commit.py` rejects the uppercase Jira key as sentence case; `commitlint` accepts the repository-required format. No hook was bypassed. |

# Findings

| ACH | Problem / evidence / affected AC | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Review comment [#4264512675](https://github.com/CtrI-Alt-Del/shifu/pull/24#discussion_r4264512675) found that the Candidate field's historical commit SHAs could be mistaken for the current PR head. | P3 metadata | None; no product or implementation check is affected. | Resolved by anchoring the current candidate to the live PR #24 head and labeling the implementation/handoff SHAs as evidence provenance. Verified against the PR head and check run before this metadata-only update; no Spec or code change. |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Keep the delivery candidate linked to the live PR, and label older SHAs as evidence provenance. | ACH-01; review comment [#4264512675](https://github.com/CtrI-Alt-Del/shifu/pull/24#discussion_r4264512675). | Applied to this Evaluation; no global rule change because the correction is specific to its publication handoff. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | [PR #24](https://github.com/CtrI-Alt-Del/shifu/pull/24), branch `feat/shifu-105`; the live PR ref identifies the current head. Latest `origin/main` is an ancestor. |
| Completed | AC-01–AC-35 and 39 active checks; independent verification and visual evidence are recorded above. PR #24 was read back; its checked head `e1a1e4693b52bc6b976d5e37b526ee0e9987e229` passed all CI checks, including the mutation summary and real Inngest tests. ACH-01 is corrected below. |
| Unfinished | None for this review-feedback pass. |
| Uncommitted work | The `.specs/STATE.md` deletion is included to honor the feature-scoped memory decision; preserve only the unrelated `design/shifu.pen` edit outside staging. |
| Active processes | None started for this conclusion. |
| Blockers | None for feature behavior. Provider ZDR eligibility is outside this feature's scope; Shifu-managed AI inference continues to follow RP-13. |
| Next action | Commit and push the Evaluation metadata correction, reply to and resolve ACH-01 after read-back, then confirm PR #24's current-head checks and review state. |

# Delivery

| RP/JN | AC coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-06 / JN-01 | AC-01–AC-35 | EV-01–EV-08 | Implemented for browser-native dictation. Recognition requires explicit user action, review and explicit send; browser-managed cloud processing is disclosed. Real transcription quality is not claimed; the six-sample quality obligation was explicitly retired. |
| RP-01 / RP-03 / RP-11 / RP-12 / RP-13 | Related isolation, lifecycle, accessibility and privacy criteria | EV-01–EV-08 | Implemented for the scoped behaviors. No audio is sent to Shifu/OpenRouter or stored by Shifu. ZDR eligibility of the browser's speech provider is outside this feature's scope; this does not alter RP-13 for Shifu-managed inference. |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| [PR #24](https://github.com/CtrI-Alt-Del/shifu/pull/24) | Live head on PR #24; checked pre-feedback head `e1a1e4693b52bc6b976d5e37b526ee0e9987e229` | All checks passed at the checked head; ACH-01 metadata conversation is corrected by this update. Verify the post-update head through the live PR checks. | [Server CI](https://github.com/CtrI-Alt-Del/shifu/actions/runs/38430497476), [Web CI](https://github.com/CtrI-Alt-Del/shifu/actions/runs/38430497492) |

| Field | Result |
| --- | --- |
| Publication | Published as PR #24; metadata-only review correction in progress. |
| Source verification | Jira SHIFU-105; Intelligence PRD content ID 83099649, v9; Privacy Policy content ID 100106241, v4. PRD reread in full; disclosure rule verified on read-back. |
| Documentation Alignment | PRD v9 requires prior disclosure and says Shifu receives/stores no browser-managed dictation audio. User's decision excludes browser-provider ZDR eligibility from this feature; RP-13 remains applicable to Shifu-managed AI inference. No Jira or Privacy Policy write was made. |
| Revision History | TLC plan revision10 reconciles PRD v9; behavior/check criteria unchanged from revision9 except current source alignment. |
| Limitations | No real speech-quality claim; browser API/service support varies. C34 quality check remains retired. Post-update current-head CI is to be checked on PR #24; no blocking product or implementation review finding is open. |
