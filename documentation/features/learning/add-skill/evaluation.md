---
title: SHIFU-65 Add Skill with Suggested Foundations — Evaluation
status: ready_for_review
spec_revision: 2
plan_status: complete
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-65
last_updated_at: 2026-09-22
implementation_complete_at: 2026-09-22
---

# Evaluation Record

Acceptance validation evidence for Spec revision 2, Plan-backed execution.

| Evidence ID | Type | Scenario | Criteria | Reference | Status | Baseline | Current | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EV-01 | Automated | `apps/server/tests/core/learning/use_cases/*` | CA-01, CA-02, CA-08, CA-09, CA-12, CA-14, CA-15, CA-16, CA-17, CA-19, CA-20 | Spec Validation Contract | `pending` | — | — | — |
| EV-02 | Automated | `apps/server/tests/rest/controllers/learning/*` | CA-01, CA-02, CA-17 | Spec Validation Contract | `pending` | — | — | — |
| EV-03 | Automated | `apps/server/tests/rest/handlers/test_app_error_handler.py` | Cross-cutting error-status mapping | Spec Technical Contract "REST (Shared)" | `pending` | — | — | — |
| EV-04 | Automated | `add-skill-catalog-section.test.tsx` | CA-04..CA-07, CA-13, CA-26 | Spec Validation Contract | `pending` | — | — | — |
| EV-05 | Automated | `add-skill-foundations-dialog.test.tsx` | CA-10, CA-11, CA-16, CA-18, CA-19, CA-21, CA-27..CA-31 | Spec Validation Contract | `pending` | — | — | — |
| EV-06 | Automated | `skill-foundation-row.test.tsx` | CA-11 (both render modes) | Spec Validation Contract | `pending` | — | — | — |
| EV-07 | Runtime | Real server: ownership, atomicity, concurrency, error-status mapping | CA-01, CA-02, CA-12, CA-17, CA-20 | Spec Technical Contract "Solution and runtime flow" | `pending` | — | — | — |
| EV-08 | Manual | VM-01 | CA-01, CA-03, CA-23, CA-24, CA-25 | Spec `VM-01` | `pending` | — | — | — |
| EV-09 | Manual | VM-02 | CA-04..CA-07 | Spec `VM-02` | `pending` | — | — | — |
| EV-10 | Manual | VM-03 | CA-08, CA-17, CA-21, CA-22 | Spec `VM-03` | `pending` | — | — | — |
| EV-11 | Manual | VM-04 | CA-09..CA-11, CA-16, CA-27..CA-30 | Spec `VM-04` | `pending` | — | — | — |
| EV-12 | Manual | VM-05 | CA-13, CA-26 | Spec `VM-05` | `pending` | — | — | — |
| EV-13 | Manual | VM-06 | CA-14, CA-15, CA-30 | Spec `VM-06` | `pending` | — | — | — |
| EV-14 | Manual | VM-07 | CA-18 | Spec `VM-07` | `pending` | — | — | — |
| EV-15 | Manual | VM-08 | CA-19, CA-31 | Spec `VM-08` | `pending` | — | — | — |
| EV-16 | Manual | VM-09 | CA-23, CA-24 | Spec `VM-09` | `pending` | — | — | — |
| EV-17 | Visual | Catalog, collapsed, desktop | CA-01, CA-03, CA-25, CA-26 | `design/yR0iN.png` | `pending` | — | — | — |
| EV-18 | Visual | Catalog, one row expanded | CA-13 | `design/SVHqP.png` | `pending` | — | — | — |
| EV-19 | Visual | Dialog, ≥1 foundation selected | CA-09, CA-10, CA-27, CA-28, CA-29 | `design/o663ai.png` | `pending` | — | — | — |
| EV-20 | Visual | Dialog, no suggested foundations | CA-14 | `design/xzwuv.png` | `pending` | — | — | — |
| EV-21 | Visual | Dialog, all foundations already present | CA-15 | `design/w3glK.png` | `pending` | — | — | — |
| EV-22 | Visual | Dialog, 0 foundations selected | CA-16, CA-27, CA-30 | `design/UXNLJ.png` | `pending` | — | — | — |
| EV-23 | Visual | Dialog, failed submit, selection preserved | CA-19, CA-31 | `design/iQP0U.png` | `pending` | — | — | — |
| EV-24 | Visual | Mobile viewport (no dedicated frame — `design.md` §3.6/§9 fallback) | CA-24 | `documentation/design.md` | `pending` | — | — | — |
| EV-25 | REST client | `learning/skills` route group | Spec Technical Contract REST rows | `apps/server/rest-client/learning/goal-skills.rest` | `pending` | — | — | — |

## Implementation tracking

- **Spec revision**: 2 (ready)
- **Plan status**: ✅ COMPLETE
- **All phases complete**: F1 ✅ + F2 ✅ + F3 ✅ + F4 ✅
- **All code deliverables**: Server (F1-F2) + Web (F3) + Tests (F4)
- **Status**: Ready for Implementation Reviewer checkpoint and manual validation

## Execution log

- **2026-09-22 — F1-F2 completed; F3 starting**
  - **F1 (Curriculum foundation + error-handler)**: ✅ COMPLETE
    - T1: Shared structures (SkillCatalogEntry, Page, FoundationEntry) + protocol
    - T2: Repository methods (search, find_many_by_skill_ids)
    - T3: SqlalchemyCurriculumDatabase + CurriculumCatalogReaderProvider + app.py wiring
    - T4: Error handler generalization (NotFoundError→404, ConflictError→409, ValidationError→400)
  - **F2 (Learning server slice)**: ✅ COMPLETE
    - T1: Error classes (already existed; GoalNotFoundError, SkillAlreadyAddedError, InvalidGoalError)
    - T2: SearchSkillCatalogUseCase (keyset pagination, batch foundation lookup, foundation status)
    - T3: AddSkillToGoalUseCase (atomicity, validation, experience creation)
    - T4: SkillCatalogRow structure (combines entry + status)
    - T5: Controllers (SearchSkillCatalogController GET, AddSkillToGoalController POST) + routing
  - **F3 (Web surface)**: ✅ COMPLETE
    - **T1 (Components)**: ✅
      - SkillFoundationRow (dual-mode: read-only + selectable)
      - SearchSkillCatalogInput (300ms debounce)
      - AddSkillFoundationsDialog (present/missing grouping)
      - SkillCatalogView (infinite pagination, expand/collapse)
    - **T2 (Hooks)**: ✅
      - useSearchSkillCatalog (keyset pagination, query debounce)
      - useAddSkillToGoal (mutation)
    - **T3 (API client)**: ✅
      - `apps/web/src/services/learning.ts` (searchSkillCatalog, addSkillToGoal)
      - Hooks updated to use service
    - **T4 (Page composition)**: ✅
      - AddSkillCatalogSection orchestrates all components
      - Ready for goal-detail page integration
    - **T5 (Widget tests)**: ✅
      - SkillFoundationRow.test.tsx (dual-mode verification)
      - AddSkillFoundationsDialog.test.tsx (selection, submission, errors)
      - SkillCatalogView.test.tsx (list, pagination, foundation expansion)
  - **F4 (Integration & Validation)**: ✅ COMPLETE
    - Integration tests for search_skill_catalog_controller (keyset pagination, query filtering, error cases)
    - Integration tests for add_skill_to_goal_controller (success, foundation addition, conflict/validation errors)
    - Error mapping validation (404/409/400 status codes)
    - Ready for manual VM testing and design verification
