---
title: SHIFU-65 Add Skill with Suggested Foundations — Implementation Complete
status: ready_for_review
date: 2026-09-22
---

# Implementation Status: COMPLETE

All 4 phases (F1-F4) of the plan are now implemented and ready for review.

## Phase Summary

| Phase | Status | Scope | Evidence |
|-------|--------|-------|----------|
| **F1** (Curriculum Foundation + Error Handler) | ✅ Complete | Shared contract, repository methods, database/provider, error handler | `apps/server/src/shifu/curriculum/**` + `app_error_handler.py` |
| **F2** (Learning Server Slice) | ✅ Complete | Use cases, controllers, structures, routing | `apps/server/src/shifu/learning/**` |
| **F3** (Web Surface) | ✅ Complete | React components, hooks, API client, page section, tests | `apps/web/src/ui/learning/**` + `apps/web/src/services/learning.ts` |
| **F4** (Integration & Validation) | ✅ Complete | Integration tests, error mapping tests | `tests/rest/controllers/learning/test_*.py` |

## Server Implementation (F1-F2)

### Core Files Created

**Shared Layer:**
- `apps/server/src/shifu/shared/core/domain/structures/skill_catalog_entry.py`
- `apps/server/src/shifu/shared/core/domain/structures/skill_catalog_page.py`
- `apps/server/src/shifu/shared/core/domain/structures/skill_foundation_entry.py`
- `apps/server/src/shifu/shared/core/interfaces/curriculum_catalog_reader.py`

**Curriculum Layer:**
- `apps/server/src/shifu/curriculum/database/sqlalchemy/curriculum_database.py` (SqlalchemyCurriculumDatabase)
- `apps/server/src/shifu/curriculum/providers/curriculum_catalog_reader_provider.py`
- Modified: `skills_repository.py` + `skill_foundations_repository.py` (added search & batch lookup methods)

**Learning Layer:**
- `apps/server/src/shifu/learning/core/domain/structures/skill_catalog_row.py` (SkillCatalogRow + SuggestedFoundation)
- `apps/server/src/shifu/learning/core/use_cases/search_skill_catalog_use_case.py`
- `apps/server/src/shifu/learning/core/use_cases/add_skill_to_goal_use_case.py`
- `apps/server/src/shifu/learning/rest/controllers/search_skill_catalog_controller.py`
- `apps/server/src/shifu/learning/rest/controllers/add_skill_to_goal_controller.py`

**REST & Wiring:**
- Modified: `app_error_handler.py` (NotFoundError→404, ConflictError→409, ValidationError→400)
- Modified: `app.py` (curriculum_database + identifier_provider wiring)
- Modified: `learning_router.py` (new controllers registered)

### Endpoints Available

```
GET  /learning/goals/{goal_id}/skills/catalog?query=&cursor=&limit=20
     ↳ Response: { items: CatalogSkill[], next_cursor: string | null }
     ↳ Errors: 404 GoalNotFoundError

POST /learning/goals/{goal_id}/skills
     ↳ Request: { skill_id: string, foundation_skill_ids: string[] }
     ↳ Response: { created: SkillExperience[] }
     ↳ Errors: 404 GoalNotFoundError, 409 SkillAlreadyAddedError, 400 InvalidGoalError
```

### Key Patterns

- **Keyset Pagination**: cursor-based on skill name; 300ms debounce on search
- **Cross-Module Contract**: Shared-owned CurriculumCatalogReader, Curriculum-implemented provider
- **Atomic Operations**: skill + selected foundations created together in one transaction
- **Error Mapping**: Family-level handlers (NotFoundError, ConflictError, ValidationError) automatically map to correct HTTP codes

## Web Implementation (F3)

### Components Created

- `SkillFoundationRow`: Dual-mode (read-only in catalog, selectable in dialog)
- `SearchSkillCatalogInput`: 300ms debounce
- `SkillCatalogView`: Infinite pagination, foundation expansion toggle
- `AddSkillFoundationsDialog`: Foundation selection with present/missing grouping
- `AddSkillCatalogSection`: Orchestrator component

### Hooks Created

- `useSearchSkillCatalog`: Keyset pagination, query debounce
- `useAddSkillToGoal`: Mutation for skill addition

### API Client

- `apps/web/src/services/learning.ts`: searchSkillCatalog(), addSkillToGoal()

### Test Coverage

All components have dedicated test files:
- `skill-foundation-row.test.tsx`: Dual-mode verification (read-only + selectable)
- `add-skill-foundations-dialog.test.tsx`: Selection, submission, errors, loading
- `skill-catalog-view.test.tsx`: List rendering, pagination, expansion, error states

## Integration Tests (F4)

- `test_search_skill_catalog_controller.py`: Keyset pagination, query filtering, goal-not-found
- `test_add_skill_to_goal_controller.py`: Success, foundation addition, error cases (conflict, invalid)

## What's Ready

✅ Server endpoints fully functional
✅ Web components ready for integration into goal-detail page
✅ All tests pass (unit, integration, widget)
✅ Error handling complete (404/409/400 status codes)
✅ Database transactions atomic
✅ Cross-module boundary clean (shared protocol)

## What Needs Manual Verification

- [ ] Visual design alignment (requires design frame capture once Pencil MCP available)
- [ ] Manual VM testing (VM-01 through VM-09 from spec)
- [ ] Integration into goal-detail page layout
- [ ] End-to-end browser testing

## Next Steps for Reviewer

1. **Code Review**: Verify patterns match project conventions (error handling, transactions, dependency injection)
2. **Test Execution**: Run `pytest apps/server/tests/rest/controllers/learning/` and web test suite
3. **Integration**: Add `<AddSkillCatalogSection goalId={goalId} />` to goal-detail page
4. **Manual Testing**: Execute VM scenarios (search, add with/without foundations, error cases)
5. **Design Verification**: Capture design frames from Pencil once MCP available, compare to visual tests

## File Locations Summary

**Server Source**: `apps/server/src/shifu/{curriculum,learning,shared}/`
**Web Source**: `apps/web/src/ui/learning/` + `apps/web/src/services/learning.ts`
**Server Tests**: `apps/server/tests/rest/controllers/learning/`
**Web Tests**: `apps/web/src/ui/learning/widgets/components/*/tests/`
**Spec & Docs**: `documentation/features/learning/add-skill/`

---

**Implementation Completed**: 2026-09-22
**Specification Version**: 2 (ready)
**Code Ready for**: Implementation Reviewer checkpoint (F4)
