---
title: Objectives Home and Planner entry
status: ready
revision: 1
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-60
scope:
  - apps/web
  - apps/server
  - documentation/features/learning/objectives-home
last_updated_at: 2026-09-22
---

# 1. Context and scope

## Objective and source

Deliver `SHIFU-60`: replace the authenticated root route (`/`) with the Objectives
Home, so an individual learner sees their existing Objectives, can start an
AI-assisted planning session from a free-form intention, or go to manual Objective
creation. This is a **complete** Spec: it crosses `apps/web` and `apps/server`,
three business modules (Learning, Intelligence, Identity), introduces new
persistence and a new cross-module authentication composition, and delivers
multiple UI states. The independent Spec Reviewer is required.

Canonical product authority:

| PRD | Content ID | Version | Retrieved | URL |
| --- | --- | --- | --- | --- |
| Intelligence | `83099649` | 1 | 2026-09-20 | https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83099649/Shifu+PRD+Intelligence |
| Learning | `83066881` | 1 | 2026-09-20 | https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB |

Delivery request: [SHIFU-60](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-60),
traced to the User Story [SHIFU-42](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-42)
and depending on the not-yet-implemented [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54)
(AI quota tracking) and [SHIFU-34](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-34)
(manual Objective creation), which SHIFU-60 blocks per Jira issue links.

## Current behavior and product gap

`/` currently renders the shared, static `DashboardPage` placeholder (no data).
Learning already has the `Goal` and `SkillExperience` domain entities, SQLAlchemy
models, mappers and repositories, but no use case, no `LearningDatabase`
composition class, and no REST surface — `learning/core/use_cases` and
`learning/rest` are empty stubs. Intelligence has no domain, no persistence and no
REST surface at all. Only Identity can currently authenticate a request
(`IdentityPipe`, `JwksJwtAuthenticationProvider`); Learning and Intelligence cannot
depend on Identity's module internals (`apps/server/tach.toml` allows each business
module to depend only on `shifu.shared`), so neither module has any way to obtain
the authenticated user today. No route exists yet for manual Objective creation,
Objective detail, or a Planner page.

## Scope and product alignment

| Area | In scope | Out of scope |
| --- | --- | --- |
| Home content | Intent field, "Criar manualmente" action, Objectives list, loading/error/empty/populated states, at `/` | The shared `AppLayout` header/nav (already implemented) and its dropdown-menu state |
| Objectives listing | Query all Objectives owned by the authenticated account; project id/title/description/skill count/updated_at; order by most-recent update; no pagination | Objective progress, mastery, situação, conclusão, or per-skill status on the card (explicit PRD/Jira exclusion) |
| Planner entry | Validate a non-empty free-form intent, start a temporary Intelligence planning session, navigate to a Planner placeholder route | The interview/question-batch flow (T15), proposal generation/validation (T16), and any AI call |
| AI quota (Intelligence RP-02) | None | **Deferred by explicit product decision.** SHIFU-54 does not exist yet; this delivery does not gate "Planejar com IA" on quota. The button is always enabled. |
| Manual creation entry | Navigate to a placeholder manual-creation route | The actual creation form/experience (T11 / SHIFU-34) |
| Objective detail entry | Navigate to a placeholder detail route | The actual Objective page (T12) |
| Destination placeholders | Three minimal "Em preparação"-style stub pages/routes (manual creation, Objective detail, Planner), created so Home's own navigation is real and testable | Any business logic inside those stubs; they exist only so this Spec's own criteria are verifiable, and are explicitly for future tickets to replace, not extend |
| Cross-module authentication | A shared, module-neutral way for Learning and Intelligence to authenticate a request | Changing Identity's own `IdentityPipe` or its already-`completed` sign-in Spec |

| Source requirement | Delivery | Notes |
| --- | --- | --- |
| Intelligence `RP-07` | full for the start-only slice | Entry screen, validation, temporary session start, and navigation are delivered; the interview/proposal/confirmation parts of RP-07 are not (T15/T16). |
| Intelligence `RP-02` | deferred | No quota gating in this slice; explicit product decision recorded below. |
| Intelligence `RP-12` | full for delivered surfaces | Responsive/keyboard/pt-BR/no-color-only requirements apply to Home and the three placeholders. |
| Learning `RP-01` | partial | The manual-creation *entry point* and the Objectives list/card are delivered; the manual-creation *screen* itself (T11) is not. |
| Learning `RP-02` | deferred | Proposal confirmation and Objective creation from Intelligence are not part of this slice (T16 + future Learning work). |
| Learning `RP-25` | full for delivered surfaces | Responsive/keyboard/pt-BR/no-color-only requirements apply to Home and the placeholders. |

#
# Product decisions and assumptions

- **AI quota is out of scope for this delivery.** The Jira acceptance criterion
  "com a cota de IA em 100%, o campo assistido fica indisponível" is not
  implemented; "Planejar com IA" is always enabled. This was an explicit product
  decision (not a repository-fixed fact) because `SHIFU-54` does not exist yet.
  Re-adding quota gating is a future amendment once `SHIFU-54` lands.
- **The temporary planning session is backend-generated and Postgres-backed.**
  `planejamento_id` (SHIFU-42's data table) is minted by a new Intelligence
  "start planning" endpoint and stored in a new, Intelligence-only table. Rows are
  not confirmed into anything; an abandoned session is simply an orphaned row with
  no further product meaning, consistent with "o planejamento é temporário".
  A cache-backed ephemeral session was considered and rejected: the row is a
  durable handoff that the future interview/proposal work (T15/T16) builds on,
  not a disposable cache entry, so Postgres keeps it inspectable and consistent
  with every other module's persistence. (At authoring time no Redis was
  provisioned in this repository; SHIFU-58 later added Redis-backed rate
  limiting, which does not change this reasoning.)
- **Three placeholder routes are created now.** Manual creation, Objective detail,
  and the Planner page do not exist yet and are explicitly out of scope to
  implement, but Home's own acceptance criteria require real navigation targets.
  Each stub renders a minimal "Em preparação" message, matching the existing
  `/intelligence` page convention, and is explicitly a placeholder for a future
  ticket to replace (not extend).
- **The shared header/nav is out of scope.** `AMF1e`'s header matches the already
  implemented `AppLayout`/`use-app-layout.ts` exactly (nav labels "Objetivos /
  Progresso / Mentor"). The header's dropdown-menu state (`LO4Z3`) is shared
  navigation behavior, not Home content, and is not touched by this Spec.
  `documentation/design.md` §3.6 narratively describes a lateral icon rail shell;
  the approved frame and the current implementation both use a top navbar instead.
  This is a stale-documentation note, not a conflict this Spec resolves.
- **No mobile Pencil frame exists for Home.** Narrow-viewport behavior is resolved
  from `documentation/design.md` §3.6 breakpoints and the existing repository
  pattern (stack a multi-column grid to one column below `sm`), not a dedicated
  design reference.

# 2. Implementation Contract

| ID | RP/JN coverage | Required behavior |
| --- | --- | --- |
| RF-01 | Intelligence RP-07, Learning RP-01 | Authenticated `/` renders, in this order: the free-form intent field, the "Criar manualmente" action, and the Objectives list. |
| RF-02 | Learning RP-01, RP-25 | The Objectives list contains only Objectives owned by the authenticated account, projected to id, title, description, skill count and updated-at, ordered by most-recent update, with no pagination. |
| RF-03 | Learning RP-01, frame `AMF1e` | Each Objective card shows only title, description and skill count — never status, progress, mastery or per-skill state. |
| RF-04 | Intelligence RP-07 (navigation), Jira AC | Selecting an Objective card navigates to the Objective-detail placeholder route; this Spec does not implement the detail page itself (T12). |
| RF-05 | Learning RP-01, Jira AC | Selecting "Criar manualmente" navigates to the manual-creation placeholder route; this Spec does not implement the creation screen itself (T11). |
| RF-06 | Intelligence RP-07, JN-07, JN-08 | Submitting a non-empty intent starts a temporary Intelligence planning session (persisted, system-generated id) and navigates to the Planner placeholder route carrying that id. No Objective or Skill is created. |
| RF-07 | Intelligence RP-07 (experience rules) | Submitting an empty or whitespace-only intent is rejected before any request is sent, with a clear, non-color-only validation message; no session is started and no navigation occurs. |
| RF-08 | Intelligence RP-07, JN-12 | Leaving, canceling, or reloading Home before submitting a valid intent discards any in-progress text; nothing is persisted for an unsubmitted intent. |
| RF-09 | Learning RP-25, Intelligence RP-12 | Home has four distinct states for the Objectives list: loading, recoverable error (with retry), empty, and populated. |
| RF-10 | Jira AC | In the empty state, the intent field and "Criar manualmente" remain visible and usable. |
| RF-11 | Learning RP-25, Intelligence RP-12 | Home and the three placeholder pages work on desktop and mobile, are fully keyboard-operable, and never communicate state by color alone. |

| ID | RF coverage | Requirement | Given | When | Then | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Home layout order | an authenticated learner opens `/` | the page renders | the intent field, then "Criar manualmente", then the Objectives list appear in that order | `home-page.test.ts` (Playwright) |
| CA-02 | RF-02, RF-11 | Account isolation | two accounts each own Objectives | account A requests the Objectives list | only account A's Objectives are returned, ordered by most-recent `updated_at` first | `test_list_home_goals_use_case.py`; `test_get_home_goals_controller.py` |
| CA-03 | RF-03 | Card content | an account has an Objective with 3 Skill experiences | the card renders | it shows the title, the description and "3 Habilidades" only — no status/progress | `goals-list-section.test.tsx` |
| CA-04 | RF-04 | Card navigation | the Objectives list is populated | the learner selects a card (pointer or keyboard) | the browser navigates to `/learning/goals/$goalId` for that Objective | `home-page.test.ts` |
| CA-05 | RF-05 | Manual-creation navigation | Home is rendered | the learner selects "Criar manualmente" | the browser navigates to `/learning/goals/new` | `home-page.test.ts` |
| CA-06 | RF-06 | Valid intent starts planning | the intent field has non-empty text | the learner submits "Planejar com IA" | a planning session is persisted with that text and the browser navigates to `/intelligence/planner/$planningId` with the returned id; no Goal/SkillExperience row is created | `test_start_planning_use_case.py`; `test_start_planning_controller.py`; `home-page.test.ts` |
| CA-07 | RF-07 | Empty intent is rejected | the intent field is empty or whitespace-only | the learner submits | no request is sent, a validation message appears, and focus stays on the field | `planning-intent-composer.test.tsx` |
| CA-08 | RF-08 | Abandoning discards input | the learner typed an intent but did not submit | the learner reloads or navigates away | the unsent text is gone on return; no planning session exists for it | `planning-intent-composer.test.tsx` |
| CA-09 | RF-09 | Loading state | Home is requested | the Objectives query is in flight | a distinct loading state renders (not the empty or error state) | `goals-list-section.test.tsx` |
| CA-10 | RF-09 | Recoverable error state | the Objectives query fails | Home renders | a recoverable error state with a retry action renders | `goals-list-section.test.tsx` |
| CA-11 | RF-09, RF-10 | Empty state | the account has zero Objectives | Home renders | an empty-state message renders and the intent field + "Criar manualmente" remain visible/usable | `goals-list-section.test.tsx` |
| CA-12 | RF-11 | Keyboard and narrow viewport | Home is rendered at a 375px viewport | the learner tabs through the page | the intent field, "Criar manualmente", "Planejar com IA" and every card are reachable and operable by keyboard, with no state conveyed by color alone | `home-page.test.ts` (narrow viewport + keyboard pass) |

## Design Contract

Saved authority: [`design/handoff.md`](design/handoff.md), sourced from
`design/shifu.pen` frame `AMF1e` ("03 Home"), inspected via the Pencil CLI
(`pen interactive`) on 2026-09-20 and exported to
[`design/AMF1e.png`](design/AMF1e.png) at 1440×900, scale 1.

| Reference | Route/surface/state | Viewport | Screenshot | Validation target |
| --- | --- | --- | --- | --- |
| Home populated | `/`, populated | 1440 × 900 | `design/AMF1e.png` | CA-01, CA-03 |
| Home narrow | `/`, populated | 375 × viewport height | none (no mobile Pencil frame; see below) | CA-12 |

The shared `AppLayout` header shown in the frame is out of scope (already
implemented, matches `use-app-layout.ts` exactly). The frame's dropdown-menu state
(`LO4Z3`) is shared-header behavior and is excluded. No mobile Home frame exists;
the narrow-viewport layout is a **recommended, not required**, supplemental capture
— it is deferred to runtime Playwright validation against `documentation/design.md`
§3.6 breakpoints and the existing single-column-stack pattern already used by
`apps/web/src/ui/intelligence/widgets/pages/intelligence-page`, rather than a second
Pencil export, because no approved narrow-viewport composition exists to compare
against.

# 3. Technical Contract

## Current technical state

| Evidence | Current responsibility | Gap |
| --- | --- | --- |
| `apps/web/src/routes/index.tsx`, `ui/shared/widgets/pages/dashboard-page` | Renders a static placeholder at `/` | No data, no intent field, no navigation |
| `apps/server/src/shifu/learning/core/domain/entities/goal.py`, `skill_experience.py` | Domain entities exist | No use case consumes them for a list/summary read |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/goals_repository.py` | `find_many_by_account_id` orders by `created_at` | Home needs ordering by `updated_at` (most-recent update first) |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/skill_experiences_repository.py` | Can only fetch experiences one goal at a time | No aggregate way to count experiences per goal across many goals without N+1 |
| `apps/server/src/shifu/learning/database/sqlalchemy/__init__.py` | Empty | No `LearningDatabase` composition class exists (repositories are never wired into a transaction unit of work) |
| `apps/server/src/shifu/learning/core/use_cases`, `rest/controllers`, `rest/schemas` | Empty stubs | No Learning REST surface exists at all |
| `apps/server/src/shifu/intelligence/core/**`, `database/**`, `rest/**` | Empty stubs everywhere | No Intelligence domain, persistence or REST surface exists at all |
| `apps/server/src/shifu/identity/pipes/identity_pipe.py` | Only Identity can build an `AuthenticatedUser` from a bearer token | `apps/server/tach.toml` forbids Learning/Intelligence from depending on `shifu.identity`; neither module has any way to authenticate a request today |
| `apps/server/src/shifu/app.py` | Registers `app.state.identity_database` only | No shared `AuthenticationProvider` instance, `learning_database`, or `intelligence_database` is registered on `app.state` |
| `apps/web/package.json` | No `@tanstack/react-query` dependency | `documentation/architecture.md` documents TanStack Query as the web app's server-state/cache technology, but no feature has needed it until now |
| `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`, `middlewares/enter-main-page-middleware.ts` | The bearer access token only exists server-side (BFF); it is never exposed to the browser | A page needing FastAPI data must fetch it through a TanStack Start server function, not a browser-side bearer call |
| `apps/web/src/constants/routes.ts` | Only static, flat routes | No entries for the new manual-creation, detail, or planner destinations |
| `apps/web/tests/shared/dashboard-page.test.ts` | Tests the old static dashboard heading | Must be replaced once `/` renders real content |

## Solution and runtime flow

**Authentication composition (fixes the cross-module gap).** `FastAPIApp.register`
constructs one `JwksJwtAuthenticationProvider` (already legitimate today, since
composition is allowed to depend on every module) and stores it as
`app.state.authentication_provider: AuthenticationProvider` (the `shifu.shared`
contract type). A new `shifu.shared.pipes.SharedPipe.get_authenticated_user`
FastAPI dependency extracts the `Bearer` token from the request and calls
`request.app.state.authentication_provider.authenticate(token)`, raising the same
`401` shape as `IdentityPipe` on `AuthorizationError`. Learning and Intelligence
controllers depend on `SharedPipe`, not on Identity, keeping Tach's module graph
intact. Identity's own `IdentityPipe` is unchanged (its Spec is `completed`).

**Objectives list (Learning, synchronous read).** `GET /learning/goals` →
`GetHomeGoalsController` → `SharedPipe.get_authenticated_user` for the account id
→ `LearningPipe.get_database` for a `LearningDatabase` → `ListHomeGoalsUseCase`
opens one transaction, reads `goals.find_many_by_account_id(account_id)` (modified
to order by `updated_at desc`), reads
`skill_experiences.count_many_by_goal_ids(goal_ids)` (new aggregate method, one
query) and returns `GoalSummary` structures (id, title, description, skill_count,
updated_at). No write occurs; the transaction commits trivially.

**Start planning (Intelligence, synchronous write).**
`POST /intelligence/planning-sessions` → `StartPlanningController` →
`SharedPipe.get_authenticated_user` → `IntelligencePipe.get_database` →
`StartPlanningUseCase` mints an id via `IdentifierProvider`, persists a
`PlanningSession(id, account_id, initial_intent, created_at)` row in one
transaction, and returns it. The Pydantic request schema strips and requires
non-empty `initial_intent` (FastAPI returns `422` automatically on violation,
matching the existing `SignInController` convention); no new domain error or
exception handler is introduced. No AI call happens; no Objective or Skill is
touched.

**Web composition.** The route stays thin: `src/routes/index.tsx` keeps
`enterMainPageMiddleware` and renders `HomePage` (replacing `DashboardPage`).
`HomePage` (`ui/shared`, matching the precedent that a cross-module landing page
already lived there) is pure layout: it renders the Intelligence-owned
`PlanningIntentComposer` layout above the Learning-owned `GoalsListSection`
layout. Neither module imports the other's widgets — `ui/shared` is the
composition boundary, matching `documentation/architecture.md`'s "Cross-module
interaction happens through explicit shared contracts... or application
composition."

`GoalsListSection` owns a colocated `useHomeGoalsQuery` hook. Per
`documentation/rules/ui-layer-rules.md` ("Query hooks, action hooks and query keys
that exist only for that page stay within the same page boundary" / "A hook that
is exclusive to one component widget remains colocated with that widget"), and
because this query has exactly one consumer, it lives inside the widget directory
itself (`goals-list-section/use-home-goals-query.ts`), not in the module-level
`ui/learning/hooks/`. It defines a TanStack Start `createServerFn` (mirroring
`enterMainPageMiddleware`'s pattern: read the current access server-side via
`getBetterAuthProvider().getCurrentAccess(...)`, call
`LearningService(restClient).getGoals(accessToken)`) and wraps it in a TanStack
Query `useQuery`. This is the first real usage of TanStack Query in the
repository; `QueryClientProvider` is mounted directly in `RootLayout` (not wrapped
in a Shifu-named context) with a `QueryClient` created once per app instance —
unlike `RestContext`/`AuthContext`, it exposes no Shifu-specific typed service to
hide, so a wrapper context would add a file without adding a contract.
`PlanningIntentComposer` owns a colocated `usePlanningIntentComposer` hook that
validates the intent client-side, and on valid submit calls a colocated
`useStartPlanningAction` hook (`planning-intent-composer/use-start-planning-action.ts`,
same single-consumer placement rule, a `createServerFn` + `useMutation` pair
following the same BFF pattern) then navigates via the router to
`/intelligence/planner/$planningId`.

## Affected layer contracts

### Domain (Learning)

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/core/domain/structures/goal_summary.py` | Create | `GoalSummary` structure: `id: str`, `title: str`, `description: str`, `skill_count: int`, `updated_at: datetime` | Read-only projection; no framework/persistence types | `ListHomeGoalsUseCase` produces it; `GetHomeGoalsController` maps it | Covered by `test_list_home_goals_use_case.py` |

### Domain (Intelligence)

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/intelligence/core/domain/entities/planning_session.py` | Create | `PlanningSession` entity: `id: str`, `account_id: str`, `initial_intent: str`, `created_at: datetime` | No framework/persistence types; immutable record of one temporary session | `StartPlanningUseCase` creates it; repository persists it | Covered by `test_start_planning_use_case.py` |

### Interfaces (Learning)

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/core/interfaces/goals_repository.py` | Modify | `find_many_by_account_id` | Now documented and implemented to order results by `updated_at desc` (was `created_at`) | `SqlalchemyGoalsRepository`; `ListHomeGoalsUseCase` | `test_list_home_goals_use_case.py` (fake repository) |
| `apps/server/src/shifu/learning/core/interfaces/skill_experiences_repository.py` | Modify | Add `count_many_by_goal_ids(goal_ids: list[str]) -> dict[str, int]` | Returns a count per goal id for exactly the ids requested; ids with zero experiences may be absent from the mapping | `SqlalchemySkillExperiencesRepository`; `ListHomeGoalsUseCase` | `test_list_home_goals_use_case.py` (fake repository) |

### Interfaces (Intelligence)

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/intelligence/core/interfaces/planning_sessions_repository.py` | Create | `PlanningSessionsRepository` protocol: `add`, `find_by_id`, `remove_all` | Mirrors the existing Learning repository protocol shape | `SqlalchemyPlanningSessionsRepository`; `StartPlanningUseCase` | `test_start_planning_use_case.py` (fake repository) |
| `apps/server/src/shifu/intelligence/core/interfaces/intelligence_database.py` | Create | `IntelligenceDatabaseRepositories` structure (`planning_sessions`, `events`); `IntelligenceDatabase.transaction()` | Sole transaction boundary for one Intelligence operation, mirroring `LearningDatabase` | `SqlalchemyIntelligenceDatabase`; `StartPlanningUseCase` | — |

### Use cases

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/core/use_cases/list_home_goals_use_case.py` | Create | `ListHomeGoalsUseCase(database).execute(account_id: str) -> list[GoalSummary]` | One transaction; read-only; ordered by `updated_at desc`; no pagination | `GetHomeGoalsController` | `apps/server/tests/core/learning/use_cases/test_list_home_goals_use_case.py` |
| `apps/server/src/shifu/intelligence/core/use_cases/start_planning_use_case.py` | Create | `StartPlanningUseCase(database, id_provider).execute(account_id: str, initial_intent: str) -> PlanningSession` | One transaction; mints id; persists one row; no AI call, no Learning write | `StartPlanningController` | `apps/server/tests/core/intelligence/use_cases/test_start_planning_use_case.py` |

### REST

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/shared/pipes/shared_pipe.py` | Create | `SharedPipe.get_authenticated_user(request, credentials) -> AuthenticatedUser` | Reads `request.app.state.authentication_provider`; `401` on missing/invalid bearer, mirroring `IdentityPipe._unauthorized` | Learning and Intelligence controllers | Exercised indirectly by controller integration tests |
| `apps/server/src/shifu/learning/pipes/learning_pipe.py` | Create | `LearningPipe.get_database(request) -> LearningDatabase` | Reads `request.app.state.learning_database` | `GetHomeGoalsController` | — |
| `apps/server/src/shifu/intelligence/pipes/intelligence_pipe.py` | Create | `IntelligencePipe.get_database(request) -> IntelligenceDatabase` | Reads `request.app.state.intelligence_database` | `StartPlanningController` | — |
| `apps/server/src/shifu/learning/rest/controllers/get_home_goals_controller.py` | Create | `GET /learning/goals` → `Response(goals: list[GoalItem])` | `GoalItem`: `id, title, description, skill_count, updated_at` (ISO string) | `LearningRouter` | `apps/server/tests/rest/controllers/learning/test_get_home_goals_controller.py` |
| `apps/server/src/shifu/intelligence/rest/controllers/start_planning_controller.py` | Create | `POST /intelligence/planning-sessions` with `Request(initial_intent: str, min_length=1, stripped)` → `Response(id, created_at)` | `422` on empty/whitespace-only intent (Pydantic validator); `401` via `SharedPipe` | `IntelligenceRouter` | `apps/server/tests/rest/controllers/intelligence/test_start_planning_controller.py` |
| `apps/server/src/shifu/learning/rest/router.py` | Modify | Register `GetHomeGoalsController` | — | `FastAPIApp._register_routers` | — |
| `apps/server/src/shifu/intelligence/rest/router.py` | Modify | Register `StartPlanningController` | — | `FastAPIApp._register_routers` | — |
| `apps/server/rest-client/learning/learning.rest` | Create | One labeled request for `GET /learning/goals` | Reusable non-secret variables; no credentials | Manual/API exploration | — |
| `apps/server/rest-client/intelligence/intelligence.rest` | Create | One labeled request for `POST /intelligence/planning-sessions` | Reusable non-secret variables; no credentials | Manual/API exploration | — |

### Database

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/goals_repository.py` | Modify | `find_many_by_account_id` orders by `GoalModel.updated_at.desc()` | Behavior-only change; no schema change | `ListHomeGoalsUseCase` | `test_list_home_goals_use_case.py` |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/skill_experiences_repository.py` | Modify | Add `count_many_by_goal_ids`: one grouped `SELECT goal_id, COUNT(*) ... WHERE goal_id IN (...) GROUP BY goal_id` | Avoids N+1 across goals | `ListHomeGoalsUseCase` | `test_list_home_goals_use_case.py` |
| `apps/server/src/shifu/learning/database/sqlalchemy/learning_database.py` | Create | `SqlalchemyLearningDatabase.transaction()` yielding `LearningDatabaseRepositories` (all five existing repositories + `events`) | Mirrors `SqlalchemyIdentityDatabase`: commit on success, rollback on exception | `app.py` composition | Exercised by `test_get_home_goals_controller.py` |
| `apps/server/src/shifu/learning/database/sqlalchemy/__init__.py` | Modify | Export `SqlalchemyLearningDatabase` | — | `app.py` | — |
| `apps/server/src/shifu/intelligence/database/sqlalchemy/models/planning_session_model.py` | Create | `PlanningSessionModel` (`__tablename__ = 'intelligence_planning_sessions'`): `id String(26) PK`, `account_id String(26) nullable=False` (no foreign key), `initial_intent String(4000)`, `created_at DateTime(timezone=True)` | Mirrors `GoalModel`'s exact column conventions, including the deliberate absence of a cross-module foreign key: every existing model keeps `account_id` as a plain column, and Identity's account-deletion participation is a module-owned mechanism, not a DB cascade | `SqlalchemyPlanningSessionsRepository` | — |
| `apps/server/src/shifu/intelligence/database/sqlalchemy/mappers/planning_session_mapper.py` | Create | `PlanningSessionMapper.to_domain` / `.to_model` | — | Repository | — |
| `apps/server/src/shifu/intelligence/database/sqlalchemy/repositories/planning_sessions_repository.py` | Create | `SqlalchemyPlanningSessionsRepository`: `add`, `find_by_id`, `remove_all` | Mirrors `SqlalchemyGoalsRepository`'s shape | `SqlalchemyIntelligenceDatabase` | `test_start_planning_controller.py` |
| `apps/server/src/shifu/intelligence/database/sqlalchemy/intelligence_database.py` | Create | `SqlalchemyIntelligenceDatabase.transaction()` yielding `IntelligenceDatabaseRepositories` | Mirrors `SqlalchemyIdentityDatabase` | `app.py` composition | Exercised by `test_start_planning_controller.py` |
| `apps/server/migrations/versions/<new_revision>_add_intelligence_planning_sessions.py` | Create | `op.create_table('intelligence_planning_sessions', ...)`, chained after `down_revision = 'c4d82f1e7a30'` | Columns/constraints as in the model above; `downgrade()` drops the table | Applied by `uv run poe db:upgrade` | Exercised by any integration test hitting the new table via Testcontainers |

### Provision / Composition

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/app.py` | Modify | Construct one `JwksJwtAuthenticationProvider` and set `app.state.authentication_provider`; construct and set `app.state.learning_database = SqlalchemyLearningDatabase(...)` and `app.state.intelligence_database = SqlalchemyIntelligenceDatabase(...)` | Composition-only change; no new runtime dependency direction violated (`shifu.app` already depends on every module) | `SharedPipe`, `LearningPipe`, `IntelligencePipe` | Exercised indirectly by the two new controller integration tests |

### UI

Widget hierarchy:

| Widget | Kind | Parent/entry | Direct children | Public contract | Behavior owner |
| --- | --- | --- | --- | --- | --- |
| `HomePage` | Page (`ui/shared/widgets/pages/home-page`) | `src/routes/index.tsx` | `PlanningIntentComposer`, `GoalsListSection` | none (no props) | Pure layout; no hook |
| `PlanningIntentComposer` | Layout (`ui/intelligence/widgets/layouts/planning-intent-composer`) | `HomePage` | shared `Textarea`, `Button` (×2), `Icon` | none | `use-planning-intent-composer.ts` |
| `GoalsListSection` | Layout (`ui/learning/widgets/layouts/goals-list-section`) | `HomePage` | `ObjectiveCard` (×N), shared `Anchor` | none | `use-goals-list-section.ts` |
| `ObjectiveCard` | Component (`ui/learning/widgets/components/objective-card`) | `GoalsListSection` | shared `Icon` | `{ id, title, description, skillCount }` | Pure renderer |
| `GoalCreatePlaceholderPage` | Page (`ui/learning/widgets/pages/goal-create-placeholder-page`) | `src/routes/learning/goals/new/index.tsx` | none | none | Pure renderer, no hook |
| `GoalDetailPlaceholderPage` | Page (`ui/learning/widgets/pages/goal-detail-placeholder-page`) | `src/routes/learning/goals/$goalId/index.tsx` | none | `{ goalId }` | Pure renderer, no hook |
| `PlannerPlaceholderPage` | Page (`ui/intelligence/widgets/pages/planner-placeholder-page`) | `src/routes/intelligence/planner/$planningId/index.tsx` | none | `{ planningId }` | Pure renderer, no hook |

Expected file tree for the affected UI paths:

```text
apps/web/src/
├── constants/
│   └── routes.ts                                                    (Modify)
├── routes/
│   ├── index.tsx                                                    (Modify)
│   ├── learning/
│   │   └── goals/
│   │       ├── new/index.tsx                                        (Create)
│   │       └── $goalId/index.tsx                                    (Create)
│   └── intelligence/
│       └── planner/
│           └── $planningId/index.tsx                                (Create)
├── rest/services/
│   ├── learning-service.ts                                          (Create)
│   └── intelligence-service.ts                                      (Create)
└── ui/
    ├── shared/widgets/
    │   ├── pages/
    │   │   ├── home-page/index.tsx                                  (Create)
    │   │   └── dashboard-page/                                      (Remove)
    │   └── layouts/root-layout/
    │       ├── index.tsx                                            (Modify)
    │       └── use-root-layout.ts                                   (Modify)
    ├── learning/
    │   └── widgets/
    │       ├── layouts/goals-list-section/
    │       │   ├── index.tsx                                        (Create)
    │       │   ├── use-goals-list-section.ts                        (Create)
    │       │   ├── use-home-goals-query.ts                          (Create)
    │       │   └── tests/goals-list-section.test.tsx                (Create)
    │       ├── components/objective-card/index.tsx                  (Create)
    │       ├── pages/goal-create-placeholder-page/index.tsx         (Create)
    │       └── pages/goal-detail-placeholder-page/index.tsx         (Create)
    └── intelligence/
        └── widgets/
            ├── layouts/planning-intent-composer/
            │   ├── index.tsx                                        (Create)
            │   ├── use-planning-intent-composer.ts                  (Create)
            │   ├── use-start-planning-action.ts                     (Create)
            │   └── tests/planning-intent-composer.test.tsx          (Create)
            └── pages/planner-placeholder-page/index.tsx             (Create)
```

Both `use-home-goals-query.ts` and `use-start-planning-action.ts` are colocated
with their single consuming widget rather than placed in a module-level `hooks/`
directory, per `documentation/rules/ui-layer-rules.md`'s single-consumer
placement rule.

Playwright suites, per `documentation/rules/widget-testing-rules.md` ("Shared
application shells and layouts belong under `tests/shared`"; "Every routed Page
and Layout owns one module-scoped browser integration file"):

```text
apps/web/tests/
├── shared/
│   └── home-page.test.ts                                            (Create; replaces dashboard-page.test.ts)
├── learning/
│   ├── goal-create-placeholder-page.test.ts                         (Create)
│   └── goal-detail-placeholder-page.test.ts                         (Create)
└── intelligence/
    └── planner-placeholder-page.test.ts                             (Create)
```

`package.json` / `pnpm-lock.yaml` (Modify): add `@tanstack/react-query` — this is
the first feature needing cached server-list state; `documentation/architecture.md`
already names TanStack Query as the web app's server-state technology.

`apps/web/src/routeTree.gen.ts` (Generate, via `pnpm --filter web generate-routes`):
regenerate after adding `src/routes/index.tsx`'s new component and the three new
route files (`learning/goals/new`, `learning/goals/$goalId`,
`intelligence/planner/$planningId`). This file is tool-owned and must not be
edited manually.

## Technical decisions

| Decision | Chosen approach | Alternative considered | Reason | Accepted trade-off |
| --- | --- | --- | --- | --- |
| Cross-module authentication | New `shifu.shared.pipes.SharedPipe` backed by one `AuthenticationProvider` instance registered on `app.state` | Give Learning/Intelligence their own JWKS provider instances, or relax Tach to let them import Identity | Keeps the module graph intact (`shifu.tach.toml`) and avoids duplicating JWKS/JWT logic | Identity's own `IdentityPipe.get_authentication_provider` is left unchanged and keeps constructing its own independent `JwksJwtAuthenticationProvider` per request (its own JWKS key cache); the new `app.state` instance is a second, separate provider used only by Learning/Intelligence. This dual lifecycle is an accepted, explicitly recorded divergence, not something this Spec unifies |
| Temporary planning session storage | New Postgres table `intelligence_planning_sessions` | Redis-backed ephemeral cache (SHIFU-58 later provisioned Redis for rate limiting, after this decision was made) | The row is a durable handoff for the future interview/proposal work (T15/T16), not a disposable cache entry; Postgres keeps it inspectable and consistent with every other module's persistence | Abandoned sessions become orphaned rows with no automatic expiry; acceptable since they hold no sensitive derived state and a future cleanup job can be added independently |
| AI quota gating | Deferred entirely for this slice | Build a minimal real quota read now | Explicit product decision; `SHIFU-54` doesn't exist yet | The literal Jira AC about 100%-quota blocking is not delivered; recorded as `deferred` in the scope table, not silently dropped |
| Home/Planner composition boundary | `HomePage` lives in `ui/shared`, composing one Learning and one Intelligence layout | Let Learning own the whole Home page and import an Intelligence widget directly | Business modules must not import each other's widgets (`documentation/architecture.md`); `ui/shared` is the existing precedent for a cross-module landing page (this is exactly why `DashboardPage` already lived there) | `ui/shared` now owns one more page-shaped file, though it stays a pure layout with zero business logic |
| Web server-state technology | Introduce `@tanstack/react-query`, wired through a new `use-home-goals-query.ts`/`use-start-planning-action.ts` pair that calls a colocated `createServerFn` | Keep the existing `useState`-based hook style used by sign-in | `documentation/architecture.md` already names TanStack Query as the chosen technology; sign-in's pattern fit a one-shot mutation, not a cached list read | Adds a new dependency and the app's first `QueryClientProvider`; no SSR prefetch is added (client-only fetch), so Home briefly shows its loading state on every navigation |

# 4. Validation Contract

| Test file | Test type | Target | Coverage goal |
| --- | --- | --- | --- |
| `apps/server/tests/core/learning/use_cases/test_list_home_goals_use_case.py` | unit | `ListHomeGoalsUseCase` | Ordering by `updated_at`, skill-count aggregation, account isolation, empty result |
| `apps/server/tests/core/intelligence/use_cases/test_start_planning_use_case.py` | unit | `StartPlanningUseCase` | Persists one row with the minted id and trimmed intent; no side effect on Learning |
| `apps/server/tests/rest/controllers/learning/test_get_home_goals_controller.py` | integration | `GET /learning/goals` | `401` without a token; `200` with the projected shape; isolation across two seeded accounts |
| `apps/server/tests/rest/controllers/intelligence/test_start_planning_controller.py` | integration | `POST /intelligence/planning-sessions` | `401` without a token; `422` on empty/whitespace intent; `201`/`200` persists a row and returns its id |
| `apps/web/src/ui/learning/widgets/layouts/goals-list-section/tests/goals-list-section.test.tsx` | component | `GoalsListSection` | Loading, recoverable-error (+retry), empty (+intent field/manual-creation still usable), populated (card content and count pluralization) states |
| `apps/web/src/ui/intelligence/widgets/layouts/planning-intent-composer/tests/planning-intent-composer.test.tsx` | component | `PlanningIntentComposer` | Empty-submit validation (CA-07), successful submit triggers navigation with the returned id, abandon/reload discards text (CA-08) |
| `apps/web/tests/shared/home-page.test.ts` | manual (Playwright) | `/` route end-to-end | Layout order, the three navigation destinations, keyboard traversal, narrow viewport, console/network inspection. `HomePage` lives in `ui/shared`, so its Playwright suite belongs under `tests/shared` per `widget-testing-rules.md`, not under a business module |
| `apps/web/tests/learning/goal-create-placeholder-page.test.ts` | manual (Playwright) | `/learning/goals/new` route | Renders the placeholder for an authenticated session; redirects an anonymous visitor |
| `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` | manual (Playwright) | `/learning/goals/$goalId` route | Renders the placeholder with the routed `goalId` for an authenticated session; redirects an anonymous visitor |
| `apps/web/tests/intelligence/planner-placeholder-page.test.ts` | manual (Playwright) | `/intelligence/planner/$planningId` route | Renders the placeholder with the routed `planningId` for an authenticated session; redirects an anonymous visitor |

`apps/web/tests/shared/dashboard-page.test.ts` (Remove): superseded by
`apps/web/tests/shared/home-page.test.ts` once `/` no longer renders
`DashboardPage`.

| Acceptance | Automated boundary | Manual scenario | Evidence target |
| --- | --- | --- | --- |
| CA-01 | `home-page.test.ts` (shared) | VM-01 | `evaluation.md` |
| CA-02 | `test_list_home_goals_use_case.py`, `test_get_home_goals_controller.py` | — | `evaluation.md` |
| CA-03 | `goals-list-section.test.tsx` | VM-01 | `evaluation.md` |
| CA-04 | `home-page.test.ts` (shared), `goal-detail-placeholder-page.test.ts` (learning) | VM-02 | `evaluation.md` |
| CA-05 | `home-page.test.ts` (shared), `goal-create-placeholder-page.test.ts` (learning) | VM-02 | `evaluation.md` |
| CA-06 | `test_start_planning_use_case.py`, `test_start_planning_controller.py`, `home-page.test.ts` (shared), `planner-placeholder-page.test.ts` (intelligence) | VM-02 | `evaluation.md` |
| CA-07 | `planning-intent-composer.test.tsx` | VM-03 | `evaluation.md` |
| CA-08 | `planning-intent-composer.test.tsx` | VM-03 | `evaluation.md` |
| CA-09 | `goals-list-section.test.tsx` | — | `evaluation.md` |
| CA-10 | `goals-list-section.test.tsx` | — | `evaluation.md` |
| CA-11 | `goals-list-section.test.tsx` | VM-01 | `evaluation.md` |
| CA-12 | `home-page.test.ts` (shared) | VM-03 | `evaluation.md` |

**VM-01 — Visual comparison against `design/AMF1e.png`.** Preconditions: seeded
account with six Objectives (varying skill counts), FastAPI + web running per
`documentation/tooling.md`. Steps: 1) sign in as the seeded account; 2) land on
`/`; 3) compare the full page at 1440×900 against `design/AMF1e.png`; 4) resize to
375×812 and confirm the grid stacks to one column with no clipping; 5) sign in as
an account with zero Objectives and confirm the empty state keeps the intent field
and "Criar manualmente" visible. Expected: layout, copy and card content match;
no console errors; no failed requests. Evidence: `evaluation.md` + fresh
screenshots. Cleanup: none (read-only).

**VM-02 — The three navigation destinations.** Preconditions: same seeded account.
Steps: 1) select an Objective card, confirm the URL becomes
`/learning/goals/<id>` and the placeholder renders; 2) go back, select "Criar
manualmente", confirm the URL becomes `/learning/goals/new`; 3) go back, type a
non-empty intent, submit "Planejar com IA", confirm a `POST
/intelligence/planning-sessions` request fires, the URL becomes
`/intelligence/planner/<id>`, and querying the database shows exactly one new
`intelligence_planning_sessions` row for that account. Expected: no Goal/SkillExperience
row is created by step 3. Evidence: `evaluation.md`. Cleanup: delete the seeded
planning-session row.

**VM-03 — Keyboard, narrow viewport and validation.** Preconditions: same seeded
account. Steps: 1) at 375×812, tab from the intent field through "Criar
manualmente", "Planejar com IA" and every visible card, confirming a visible focus
ring at each stop; 2) submit the intent field empty, confirm a non-color-only
validation message appears and focus remains on the field; 3) type an intent,
reload the page, confirm the field is empty again. Expected: no state is
conveyed by color alone; no console errors. Evidence: `evaluation.md`.

Real commands:

```bash
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
```

# 5. Documentation alignment and revision history

| Document | Authority for | State | Required change/confirmation |
| --- | --- | --- | --- |
| Intelligence PRD (`83099649`, v1) | RP-07, RP-02, RP-12 | confirmed | RP-02 explicitly recorded as `deferred` for this slice, not silently dropped |
| Learning PRD (`83066881`, v1) | RP-01, RP-02, RP-25 | confirmed | RP-02 recorded as `deferred`; RP-01 recorded as `partial` |
| `documentation/modules.md` | Module ownership | confirmed | Learning owns Objectives/listing; Intelligence owns the Planner entry; no boundary change needed |
| `documentation/architecture.md` | Web layers, TanStack Query | confirmed | This Spec is the first to actually adopt TanStack Query, per the already-documented choice |
| `documentation/design.md` §3.6 | Shell/breakpoints | discrepancy noted, not resolved | Narrative lateral-rail shell description is stale versus the approved frame and current `AppLayout`; out of this Spec's scope to fix |
| `design/shifu.pen` (`AMF1e`) | Home visual reference | confirmed | Inspected directly via Pencil CLI on 2026-09-20; see `design/handoff.md` |
| This Spec's own "Temporary planning session storage" rationale (§3) | Technical decision justification | corrected | `origin/main` merged SHIFU-58 (Redis-backed rate limiting) during implementation, making the original "no Redis is provisioned" rationale factually stale; corrected to the durability rationale that was always the real reason, per `evaluation.md`'s F6 merge entry. The decision itself (Postgres, not Redis) is unchanged |

| Rule | Applies to | Evaluated revision |
| --- | --- | --- |
| `documentation/rules/python-conventions-rules.md` | `apps/server/**/*.py` | 2026-09-20 |
| `documentation/rules/core-layer-rules.md` | Learning/Intelligence `core/**` | 2026-09-20 |
| `documentation/rules/use-case-testing-rules.md` | `core/use_cases`, `tests/core/**` | 2026-09-20 |
| `documentation/rules/rest-layer-rules.md` | `**/rest/**`, `apps/web/src/rest/**` | 2026-09-20 |
| `documentation/rules/controllers-testing-rules.md` | `apps/server/tests/rest/controllers/**` | 2026-09-20 |
| `documentation/rules/database-layer-rules.md` | `**/database/**`, `apps/server/migrations/**` | 2026-09-20 |
| `documentation/rules/provision-layer-rules.md` | `apps/server/**/pipes/**`, `app.py` | 2026-09-20 |
| `documentation/rules/server-app-layer-rules.md` | `apps/server/src/shifu/app.py` | 2026-09-20 |
| `documentation/rules/ui-layer-rules.md` | `apps/web/src/ui/**`, `apps/web/src/rest/**` | 2026-09-20 |
| `documentation/rules/web-app-routing-rules.md` | `apps/web/src/routes/**`, `constants/routes.ts` | 2026-09-20 |
| `documentation/rules/widget-testing-rules.md` | `apps/web/src/**/*.test.tsx`, `apps/web/tests/**` | 2026-09-20 |
| `documentation/rules/typescript-conventions-rules.md` | `apps/web/**` | 2026-09-20 |

| Revision | Date | Material change | Reason |
| --- | --- | --- | --- |
| 1 | 2026-09-20 | Created Spec | SHIFU-60 Dev Task |
