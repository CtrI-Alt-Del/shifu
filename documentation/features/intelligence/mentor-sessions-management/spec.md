---
title: Mentor sessions management
status: completed
revision: 8
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-99
scope:
  - intelligence
  - authenticated-web-shell
last_updated_at: 2026-10-09
---

# Verification Contract Amendment

| Revision | Approval | Contract change |
| --- | --- | --- |
| 7 | User approval in this task, 2026-10-08 | Add narrowly scoped Web transport/route/server-function tests and one PostgreSQL-backed Intelligence adapter test to CI-04/CI-10. The changed-code coverage thresholds remain 85% statements/functions/lines and 80% branches. Product behavior and feature scope do not change. |

# Objective

Deliver private, persistent Mentor conversation management through the existing
Intelligence page and an authenticated application-wide FAB. Opening a draft creates
no database record; accepting its first message creates a conversation with a
definitive title. Learners can find, reopen, rename and permanently delete their
own conversations.

Mode: **complete**, because this delivery introduces private persistence, external
title inference, idempotency, concurrent deletion and Web/Server contracts.
The current Intelligence page is a placeholder; the Server only implements
PlanningSession. MentorSession is a separate Intelligence aggregate.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Authenticated learner | First-message acceptance; persistent history; title search; rename; confirmed conversation deletion; page/FAB continuity | Empty conversation creation; individual message editing/deletion; regeneration; export; sharing; restoration |
| Titles | One bounded synchronous generation attempt, deterministic fallback, final title at creation, subsequent manual renaming | Background title jobs; automatically replacing a created title |
| Response persistence | Internal update-only completion contract; one response per learner message; deletion/concurrency guards | Response generation, dispatch, workers, subsequent learner-message submission, cancellation and retry processing |
| Privacy | Existing active-account authentication, account isolation, protected transport, title inference privacy, conversation content deletion | **Account closure and its integration**, account-purge events/jobs, account-erasure deadlines and rights-request orchestration |
| Other Mentor capabilities | Attachment/audio controls remain visible but disabled on page/FAB; disabled Memories/quota controls remain on the dedicated page and are omitted from the FAB to match yXJ3I/tMGjt/PdJCw, with accessible unavailability text for rendered controls | Their operations, shared usage-quota enforcement/accounting for auxiliary title inference, fabricated quota values, summaries, contextual consultation and action cards |
| UI | pt-BR, desktop/mobile, keyboard, page search parameter, fresh reads without response-cache reuse | Browser storage of conversations/drafts, periodic polling, changes to Learning outcomes or existing PlanningSession behavior |

The bounded product disposition is RP-03 **partial** (conversation management
delivered; the complete conversational capability depends on later messaging),
RP-04 **partial** (access from other areas, without contextual consultation),
RP-06 **partial** (accepted pending message and safe response persistence),
RP-02 **partial** (auxiliary title inference has no usage-quota enforcement/accounting
in this slice),
RP-12 **partial** (the affected surfaces), RP-13 **partial** (title privacy and
individual deletion); RP-11/account-lifecycle parts of RP-13 and JN-16 are
**deferred**. RP-14–RP-17 and audio dictation are deferred. JN-01 is partial;
JN-14 is delivered for the content types owned by this slice. These dispositions
do not amend or mark the canonical PRD implemented.

The single visual inventory is [design/handoff.md](design/handoff.md), including
saved references and explicitly approved mobile assumptions.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | RP-03, RP-06; JN-01; SHIFU-99 | Opening Nova conversa is transient. Accepting a non-whitespace first message atomically persists the session, definitive title and exact original message, including indentation/newlines. History begins at acceptance, without waiting for a generated answer. |
| RF-02 | RP-03, RP-02, RP-13 | Generate a title using only the first 1,000 Unicode code points of the first message, one attempt with a total 3-second deadline and no automatic retries. Use fixed GPT-6 Luna through OpenRouter. Validate structured title output; missing configuration, unavailable privacy-compliant routing, timeout, failure or invalid output uses the normalized first-message prefix, capped at 120 code points. This slice does not check, debit or account for shared monthly AI usage quota for title inference. Never automatically change the title afterward. |
| RF-03 | RP-03, RP-06 | The client creates a UUIDv4 submission key and preserves it for retries of that first send. Matching replay returns the existing active conversation; a changed exact message under the same key conflicts. Concurrent matching requests persist exactly one session and learner message. No claim of exactly one inference call under simultaneous requests. Replaying an excluded conversation's key cannot recreate it. |
| RF-04 | RP-03; JN-01 | Unlimited conversation count; fresh Server reads. List active owned sessions by last message/response activity descending, then ID descending, in fixed batches of 30. Opening/renaming does not reorder activity. Load subsequent batches automatically near the list end. Search title by literal substring, ignoring case and diacritics, after 300 ms; reset pagination and reject stale results when the search changes. |
| RF-05 | RP-03, RP-06 | Reopen only an owned active conversation. Load its 30 newest messages, display chronologically, and automatically fetch older pages on upward scrolling without moving the reading position. Show accepted unanswered messages as pending; do not imply a running generator or fabricate answers. No second learner-message submission is delivered by this slice. |
| RF-06 | RP-03 | Rename an owned active session to a trimmed, nonempty title of at most 120 code points. Do not silently truncate manual input. Update its search representation atomically. Last valid concurrent write wins; no optimistic version contract. Opening a draft offers no rename/delete operation. |
| RF-07 | RP-03, RP-13, RP-14; JN-14 | Cancel/close confirmation has no effects. Confirmed deletion makes the session immediately unavailable and irreversibly removes its title, search text, content fingerprint, messages and other content owned by this slice in the same transaction. Retain only session ID, account ID, submission key and deletion timestamp, without automatic expiry in this delivery. Owned repeat deletion succeeds; unknown/foreign IDs have the same private 404. Independent Memories are not deleted or copied; their future origin links resolve to unavailable. |
| RF-08 | RP-03, RP-06, RP-13 | Response completion targets an existing owned active session and an existing learner message. One response per learner message; exact-content replay succeeds, divergent replay conflicts. Completion never creates/upserts a session. Delete and completion use the same session-first lock order. A deleted/missing target produces no write and cannot be resurrected by late work. |
| RF-09 | RP-03, RP-04, RP-12, RP-13 | Server authorization derives only from the authenticated active account, never submitted IDs/e-mail. List/search/detail/rename/delete/completion isolate accounts. Browser receives no bearer credential, prompts, provider traces or hidden reasoning. On logout, scope change or teardown, discard Mentor state and ignore late results. Revalidate asynchronously on focus; keep the application interactive while private Mentor content waits for scope confirmation. |
| RF-10 | RP-03, RP-04, RP-12 | Page and FAB share selection and unsent draft in memory. Page URL is /intelligence?session=<ULID>; a draft has no session parameter. FAB keeps the originating URL; expand navigates to the selected page URL. Re-fetch on open, selection, page/FAB transition and focus, without reusing previous response caches or periodic polling. Reload loses unsent draft/key; accepted messages remain retrievable from history. |
| RF-11 | RP-03, RP-12 | Rename/delete change the visible state only after Server success. Disable duplicate in-flight actions, preserve inputs on recoverable failure and offer retry. Deleting the selected conversation returns to an unsaved new conversation, removes its URL parameter and keeps the FAB/history reachable. Infinite scrolling also has an accessible keyboard-operable recovery/load action. |
| RF-12 | RP-12; SHIFU-99 | Use approved semantic tokens/shared primitives, 566 px desktop panel and mobile fullscreen Mentor. Essential actions have pt-BR labels, visible focus and keyboard operation; dialogs trap/restore focus and support cancel/Escape. Keep rendered future controls visibly disabled with Indisponível no momento, without fictitious percentages or active destinations. Memories/quota placeholders remain on the dedicated page and are omitted from the FAB per the user-requested yXJ3I/tMGjt/PdJCw design; attachment/audio remain disabled on both surfaces. Honor reduced motion, readable wrapping and mobile hit targets. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-10 | Authenticated learner, no selected session | Open/close draft; then accept a first message | No empty rows; one session and exact message persist together; title/history/page selection reflect accepted IDs | CI-01, CI-03, CI-04, CI-05, VM-01 |
| CA-02 | RF-02 | Valid first message | Eligible title inference succeeds, fails, times out or yields invalid output | Only the allowed prefix is sent; deadline/retry/privacy rules hold; quota state is neither read nor mutated; creation uses validated title or deterministic fallback | CI-01, CI-02, CI-03 |
| CA-03 | RF-03 | A stable submission key | Replay matching/different content, submit concurrently, lose the response or replay after deletion | Same active IDs/current title or typed conflict/private 404; no duplicate or resurrected content | CI-01, CI-03, CI-06 |
| CA-04 | RF-04 | More than 30 owned sessions, ties, mixed accents, foreign/deleted records | Browse/search/rename/open | Stable scoped cursor pages; literal case/diacritic-insensitive search; automatic loading; only message activity changes order | CI-01, CI-03, CI-04, CI-05, VM-01 |
| CA-05 | RF-05, RF-08 | Owned history with more than 30 messages and an unanswered learner message | Open/load older history; complete/replay response | Chronological display, preserved reading position, pending state and exactly one persisted response | CI-01, CI-03, CI-04, CI-05, CI-12 |
| CA-06 | RF-06, RF-11 | Active owned session or unsaved draft | Rename valid/invalid title, race renames or encounter failure | Manual title/search update together, last valid write wins, no activity reorder; draft cannot rename; failure preserves input | CI-01, CI-03, CI-04, CI-05, VM-01 |
| CA-07 | RF-07, RF-11 | Selected owned session | Cancel, confirm, repeat deletion or replay an old send | Cancel has no effects; confirmation purges owned content and leaves only the minimal reservation; private not-found behavior and new-draft UI | CI-01, CI-03, CI-04, CI-05, CI-06, VM-01 |
| CA-08 | RF-08 | Completion and deletion contend for the same session | Execute in either order, including duplicate/divergent completion | Consistent locking, no orphan response/deadlock/resurrection, one response maximum | CI-01, CI-06, CI-12 |
| CA-09 | RF-09, RF-10 | Two active accounts and changed/expired authentication | Access foreign IDs, switch scope, refocus, finish stale requests | No foreign data/effects, trusted auth each call, state cleared, stale results ignored, no browser secrets/cache reuse | CI-01, CI-02, CI-03, CI-04, CI-05, CI-12, VM-01 |
| CA-10 | RF-10, RF-11, RF-12 | Page/FAB on desktop/mobile | Navigate, expand, send, search, rename/delete and use keyboard | Correct URL/selection, real fresh requests, recoverable loading/error states, accessible automatic paging, focus and responsive composition | CI-04, CI-05, VM-01, VM-02 |
| CA-11 | RF-12 | Approved Pencil references | Render required happy-path states | Token/primitive hierarchy and approved deviations match the handoff; future controls disabled, without fabricated capabilities/data | CI-04, CI-05, VM-02 |

# Technical Contract

## Architecture Mapping

Owner: Intelligence. Shared provides technical clocks/IDs/authentication/settings;
Identity and Learning retain their ownership. Rule Pack and conflicts are recorded
in Documentation Alignment. The paths below are **planned**, except explicitly
identified existing modifications.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Intelligence Core | apps/server/src/shifu/intelligence/core/domain/{entities,enums,structures,errors}/mentor_* | Session/message/page/submission/result declarations and typed errors below; export through owning barrels. |
| Create | Intelligence Core ports/use cases | core/interfaces/mentor_sessions_repository.py; mentor_messages_repository.py; generate_mentor_title_workflow.py; core/use_cases/create_mentor_session_use_case.py; list_mentor_sessions_use_case.py; get_mentor_session_use_case.py; rename_mentor_session_use_case.py; remove_mentor_session_use_case.py; finalize_mentor_response_use_case.py | Framework-free contracts and six owning operations. |
| Modify | Intelligence transaction | core/interfaces/intelligence_database.py; database/sqlalchemy/intelligence_database.py | Add both Mentor repositories to the existing repository structure and sole transaction owner; preserve planning_sessions/events. |
| Create | Intelligence SQLAlchemy | apps/server/src/shifu/intelligence/database/sqlalchemy/{models,mappers,repositories}/mentor_* | Models, mappings, account-scoped reads, cursor paging, submission/session locks, content purge and constraints below. |
| Modify/Create | Schema registration/migration | intelligence/database/sqlalchemy/models/__init__.py; apps/server/migrations/versions/ | Export new models for existing Alembic metadata discovery. Generate one reviewed additive migration from the actual current head; do not invent a revision filename or alter existing data. |
| Create/Modify | Intelligence REST | apps/server/src/shifu/intelligence/rest/controllers/*_mentor_session_controller.py; list_mentor_sessions_controller.py; rest/controllers/__init__.py; rest/router.py | Register five protected operations below, serialization, safe errors and no-store headers; no public finalization endpoint. |
| Create | Intelligence AI | apps/server/src/shifu/intelligence/ai/generative/agno/{agents/mentor_title_agent.py,outputs/mentor_title_output.py,workflows/agno_generate_mentor_title_workflow.py} | One native Agent and minimal Workflow specialization, structured title output, no tools/history/storage or domain persistence. |
| Create/Modify | Model composition | intelligence/providers/openrouter/mentor_title_model_provider.py; intelligence/pipes/intelligence_pipe.py; apps/server/src/shifu/app.py | Resolve fixed title profile, manage client lifecycle, inject Core workflow protocol; request-local agent/workflow state; preserve existing Jev assessment composition. |
| Modify | Dependencies | apps/server/pyproject.toml; apps/server/uv.lock | Add Agno and its required OpenRouter/OpenAI client dependency through uv, using official docs for the resolved version. Neither is currently installed in the manifest. |
| Create | REST examples | apps/server/rest-client/intelligence/mentor-sessions.rest | Non-secret examples of first send/replay, pages/search/detail, rename/delete and safe failures. No credentials or account-ID authorization inputs. |
| Modify/Create | Web contracts/REST | apps/web/src/rest/services/intelligence-service.ts; apps/web/src/core/intelligence/{types,enums}/ | Add Mentor service methods/DTO mapping while preserving startPlanning; extend the existing service composition/type, not a parallel HTTP stack. |
| Create | Web state/operations | apps/web/src/ui/intelligence/contexts/mentor-context/; hooks/use-mentor-context.ts; five query/action hooks in the approved tree below | Mandatory context directory/provider hook/value type/tests. Selection/draft/display state only; no QueryClient response-cache reuse, local/session storage or persisted query cache. Operations call authenticated server functions. |
| Modify/Create | Web page/routing | apps/web/src/ui/intelligence/widgets/pages/intelligence-page/; apps/web/src/routes/intelligence/index.tsx | Keep existing IntelligencePage widget/name and integration file, replace placeholder with Mentor; validate optional session search parameter; generate route metadata if needed. |
| Create/Modify | FAB/shared composition | apps/web/src/ui/intelligence/widgets/components/{mentor-chat,mentor-fab}/; apps/web/src/ui/shared/widgets/layouts/app-layout/index.tsx; shared Icon/primitives as needed | Mount Intelligence-owned context/MentorFab in protected AppLayout, keeping its existing props; page and FAB reuse MentorChat with its owned children below. Compose shared Button/Input/Textarea/DropdownMenu/AlertDialog and shared dialog primitive where absent; no feature-native control forks. |
| Modify | Design authority | documentation/design.md | Align desktop Mentor width to 566 px, as explicitly approved; keep unrelated product sections unchanged. |
| Create/Modify | Tests | Verification Contract selections | Existing page/shell and feature/widget tests plus the revision 7 bounded route, REST-service, server-function and PostgreSQL adapter selectors. No provider/query/action suites or unrelated database/repository tests. |

**Approved title-agent file tree.** These paths make the existing architecture
mapping explicit; they introduce no additional agent or behavior. New paths are
planned `[N]`; existing composition is modified `[M]`. Include owning package
exports as required by the Rule Pack.

~~~text
apps/server/src/shifu/intelligence/
├── ai/generative/agno/
│   ├── agents/
│   │   └── mentor_title_agent.py                       [N]
│   ├── outputs/
│   │   └── mentor_title_output.py                      [N]
│   └── workflows/
│       └── agno_generate_mentor_title_workflow.py       [N]
├── core/interfaces/
│   └── generate_mentor_title_workflow.py                [N]
├── providers/openrouter/
│   └── mentor_title_model_provider.py                  [N]
└── pipes/
    └── intelligence_pipe.py                            [M]

apps/server/tests/intelligence/ai/generative/agno/workflows/
└── test_agno_generate_mentor_title_workflow.py           [N]
~~~

The Core port remains framework-free. The native Agno agent owns title
instructions/output; the workflow implements that port; the OpenRouter provider
owns model/client configuration and the Intelligence pipe injects the composition.
The composed workflow test is CI-02; the provider has no dedicated test suite.
Only the title agent is included. Conversation-response generation remains deferred.

**Approved Mentor context and operation-hook tree.** All paths below are
planned `[N]`, owned by Intelligence. The context is mounted in protected
AppLayout above both the routed IntelligencePage and MentorFab.

~~~text
apps/web/src/ui/intelligence/
├── contexts/mentor-context/                            [N]
│   ├── index.tsx
│   ├── types/
│   │   └── mentor-context-value.ts
│   ├── use-mentor-context-provider.ts
│   └── tests/
│       └── use-mentor-context-provider.test.ts
└── hooks/                                              [N files below]
    ├── use-mentor-context.ts
    ├── use-mentor-sessions-query.ts
    ├── use-mentor-session-query.ts
    ├── use-create-mentor-session-action.ts
    ├── use-rename-mentor-session-action.ts
    └── use-remove-mentor-session-action.ts
~~~

The context provider hook consumes the two query hooks and three action hooks;
use-mentor-context is the sole raw-context consumer boundary exposed to widgets.
Operation hooks obtain transport/authentication dependencies from existing
application boundaries and call the authenticated server functions; they must
not consume MentorContext themselves, which would create a provider cycle.

use-mentor-sessions-query owns fresh list/search/cursor reads;
use-mentor-session-query owns fresh detail/older-message cursor reads. Query is
a domain read responsibility, not permission to reuse root QueryClient responses.
Both preserve RF-10's fresh-fetch triggers, expose domain-named results/status/
read operations and support superseded-result rejection. They keep only the
current display/request lifecycle required by the provider, without a separate
reusable response cache or duplicate session store.

use-create-mentor-session-action owns first-send request lifecycle, using the
provider's stable submission key for retries; it does not create empty sessions.
use-rename-mentor-session-action and use-remove-mentor-session-action own their
respective request lifecycles. They expose domain operations and pending/error
states; the provider coordinates accepted results, selection, scoped state and
fresh reads after success. Widget hooks own local form/focus/scroll interactions.
No finalization or subsequent-message action is introduced.

Query/action hooks have no dedicated test files. CI-04 covers their consuming
context/widget behavior and CI-05 covers route/transport wiring. Keep the
existing planned context-provider suite; do not mirror these hooks with new tests.

**Approved Web widget ownership tree.** All new directories below are planned;
IntelligencePage and AppLayout already exist. MentorChat owns history, conversation
and dialogs; MentorFab owns the floating trigger/container and its open/close/expand
presentation. IntelligencePage owns page composition and URL synchronization.

~~~text
apps/web/src/ui/intelligence/widgets/
├── pages/intelligence-page/                         [M]
│   ├── index.tsx
│   ├── use-intelligence-page.ts
│   └── tests/
└── components/
    ├── mentor-fab/                                  [N]
    │   ├── index.tsx
    │   ├── use-mentor-fab.ts
    │   └── tests/
    └── mentor-chat/                                 [N]
        ├── index.tsx
        ├── use-mentor-chat.ts
        ├── header/index.tsx
        ├── session-history/
        │   ├── index.tsx
        │   ├── use-session-history.ts
        │   ├── session-item/index.tsx
        │   └── tests/
        ├── conversation/
        │   ├── index.tsx
        │   ├── use-conversation.ts
        │   ├── empty-state/index.tsx
        │   ├── message-list/
        │   │   ├── index.tsx
        │   │   └── message-item/index.tsx
        │   ├── composer/
        │   │   ├── index.tsx
        │   │   ├── use-composer.ts
        │   │   └── tests/
        │   └── tests/
        ├── rename-session-dialog/
        │   ├── index.tsx
        │   ├── use-rename-session-dialog.ts
        │   └── tests/
        ├── remove-session-dialog/
        │   ├── index.tsx
        │   ├── use-remove-session-dialog.ts
        │   └── tests/
        └── tests/
~~~

The context remains the sole owner of shared selection, draft/submission key,
request state and operations. Widget hooks consume it and own only their local
interaction/presentation: history search/paging controls, conversation scroll
anchoring, composer submission interaction and dialog validation/focus. They do
not create duplicate session stores, transport stacks or request orchestration.
Header, session item, empty state and message renderers have explicit props and
remain pure renderers; add an owning hook if behavior later requires one.
Internal structural children are exercised through their owning composition;
children with substantial independent controls have the owning tests in CI-04.
No response generation, subsequent-message sending or other scope is added.

~~~typescript
export type MentorChatProps = {
  surface: 'page' | 'fab'
}
~~~

MentorChat's surface selects the approved presentation and header controls;
IntelligencePage supplies page and MentorFab supplies fab. MentorFab has no
feature-specific public props; both widgets use the scoped Mentor context.

**Core public declarations.** Use repository entity/structure decorators and
owning exports. Imports/bodies are omitted; these are complete contracted members
for new values. Existing ClockProvider, IdentifierProvider and AuthenticationProvider
remain unchanged.

~~~python
class MentorMessageRole(StrEnum):
    LEARNER = 'learner'
    MENTOR = 'mentor'

@entity
class MentorSession:
    id: str
    account_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime

@frozen_entity
class MentorMessage:
    id: str
    session_id: str
    role: MentorMessageRole
    content: str
    created_at: datetime
    in_reply_to_message_id: str | None

@structure
class MentorSubmissionRecord:
    session_id: str
    content_fingerprint: str | None
    deleted_at: datetime | None

@structure
class MentorSessionsPage:
    items: list[MentorSession]
    next_cursor: str | None

@structure
class MentorMessagesPage:
    items: list[MentorMessage]
    next_cursor: str | None

@structure
class MentorSessionDetail:
    session: MentorSession
    messages: MentorMessagesPage
    pending_learner_message_id: str | None

@structure
class CreateMentorSessionResult:
    detail: MentorSessionDetail
    created: bool

class GenerateMentorTitleWorkflow(Protocol):
    def generate(self, first_message: str) -> str: ...

class MentorSessionsRepository(Protocol):
    def find_submission(self, account_id: str, submission_key: str) -> MentorSubmissionRecord | None: ...
    def find_submission_by_session_id(self, account_id: str, session_id: str) -> MentorSubmissionRecord | None: ...
    def lock_submission(self, account_id: str, submission_key: str) -> None: ...
    def find_by_id(self, account_id: str, session_id: str) -> MentorSession | None: ...
    def find_by_id_for_update(self, account_id: str, session_id: str) -> MentorSession | None: ...
    def find_many(self, account_id: str, search: str | None, cursor: str | None) -> MentorSessionsPage: ...
    def add(self, session: MentorSession, submission_key: str, content_fingerprint: str) -> None: ...
    def rename(self, session: MentorSession) -> None: ...
    def record_activity(self, session: MentorSession) -> None: ...
    def remove(self, session: MentorSession, deleted_at: datetime) -> None: ...

class MentorMessagesRepository(Protocol):
    def find_many(self, account_id: str, session_id: str, cursor: str | None) -> MentorMessagesPage: ...
    def find_by_id(self, account_id: str, session_id: str, message_id: str) -> MentorMessage | None: ...
    def find_response(self, account_id: str, session_id: str, learner_message_id: str) -> MentorMessage | None: ...
    def find_pending_learner_message_id(self, account_id: str, session_id: str) -> str | None: ...
    def add(self, message: MentorMessage) -> None: ...
    def remove_by_session_id(self, session_id: str) -> None: ...

# Scoped additions; existing planning_sessions and events remain unchanged.
@structure
class IntelligenceDatabaseRepositories:
    planning_sessions: PlanningSessionsRepository
    events: EventsRepository
    mentor_sessions: MentorSessionsRepository
    mentor_messages: MentorMessagesRepository

class CreateMentorSessionUseCase:
    def __init__(self, database: IntelligenceDatabase, identifier_provider: IdentifierProvider, clock_provider: ClockProvider, title_workflow: GenerateMentorTitleWorkflow) -> None: ...
    def execute(self, account_id: str, submission_key: str, first_message: str) -> CreateMentorSessionResult: ...
class ListMentorSessionsUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None: ...
    def execute(self, account_id: str, search: str | None = None, cursor: str | None = None) -> MentorSessionsPage: ...
class GetMentorSessionUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None: ...
    def execute(self, account_id: str, session_id: str, cursor: str | None = None) -> MentorSessionDetail: ...
class RenameMentorSessionUseCase:
    def __init__(self, database: IntelligenceDatabase, clock_provider: ClockProvider) -> None: ...
    def execute(self, account_id: str, session_id: str, title: str) -> MentorSession: ...
class RemoveMentorSessionUseCase:
    def __init__(self, database: IntelligenceDatabase, clock_provider: ClockProvider) -> None: ...
    def execute(self, account_id: str, session_id: str) -> None: ...
class FinalizeMentorResponseUseCase:
    def __init__(self, database: IntelligenceDatabase, identifier_provider: IdentifierProvider, clock_provider: ClockProvider) -> None: ...
    def execute(self, account_id: str, session_id: str, learner_message_id: str, content: str) -> bool: ...
~~~

Finalize returns true for insertion or exact replay, false for deleted/missing
session/message; foreign targets also return false without revealing existence.
Existing active non-learner targets and divergent responses raise typed conflicts.
All consumers receive domain results only. Define MentorSessionNotFoundError
(NotFoundError), MentorSubmissionConflictError/MentorResponseConflictError
(ConflictError), and MentorInputInvalidError (ValidationError), with pt-BR safe
messages. Existing handlers supply statuses; controllers do not catch/map domain
errors. The title workflow translates unavailable/provider/invalid-output failures
to MentorTitleUnavailableError (ServiceUnavailableError) or
MentorTitleOutputInvalidError (ValidationError); creation alone applies fallback.

**HTTP and Web contracts.** All five endpoints require the current protected
authentication boundary (SharedPipe.get_authenticated_user), derive account_id
from it, and return private, no-store responses. Unexpected body fields are rejected.

| Method / full path | Request | Success |
| --- | --- | --- |
| POST /intelligence/mentor-sessions | JSON: submission_key UUIDv4; first_message string with at least one non-whitespace character; preserve exact content | 201 on creation / 200 on replay; MentorSessionDetail |
| GET /intelligence/mentor-sessions | Optional search string and opaque cursor; fixed page size 30 | 200; MentorSessionsPage |
| GET /intelligence/mentor-sessions/{session_id} | ULID path; optional older-message cursor; fixed page size 30 | 200; MentorSessionDetail |
| PATCH /intelligence/mentor-sessions/{session_id} | JSON: title, trimmed nonempty string, 1–120 code points | 200; MentorSession |
| DELETE /intelligence/mentor-sessions/{session_id} | No body | 204, including owned tombstone replay |

Transport DTOs omit account_id, submission key, fingerprint and deletion metadata.
Serialize timestamps as timezone-aware ISO-8601. Message role values are learner
and mentor. Detail and page nesting follows the Core structures with snake_case
field names. Errors use existing {code, message}: 401 missing/invalid authentication,
404 missing/foreign/deleted target, 409 changed-content submission or response
conflict, 400 domain validation, 422 malformed transport/title/UUID/ULID/cursor,
503 safe infrastructure failure. No title-inference error prevents valid creation
when the fallback can be saved.

Session cursors carry the ordering tuple and normalized search context; message
cursors carry session and chronological tuple. They are opaque, validated,
account-scoped seek positions, not authorization credentials. A mismatched search,
session or malformed cursor is rejected; changing search starts a new first page.
Escape SQL wildcard characters so user % and _ remain literal. The normalized
title/search uses case folding and Unicode decomposition with diacritics removed;
display/title storage preserves the original manual/generated title.

~~~typescript
export type MentorSession = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  lastActivityAt: string
}
export type MentorMessage = {
  id: string
  sessionId: string
  role: 'learner' | 'mentor'
  content: string
  createdAt: string
  inReplyToMessageId: string | null
}
export type MentorSessionsPage = {
  items: MentorSession[]
  nextCursor: string | null
}
export type MentorMessagesPage = {
  items: MentorMessage[]
  nextCursor: string | null
}
export type MentorSessionDetail = {
  session: MentorSession
  messages: MentorMessagesPage
  pendingLearnerMessageId: string | null
}
export type CreateMentorSessionInput = {
  submissionKey: string
  firstMessage: string
}
// Scoped additions to the existing IntelligenceService type:
createMentorSession(accessToken: string, input: CreateMentorSessionInput): Promise<MentorSessionDetail>
listMentorSessions(accessToken: string, input: { search?: string; cursor?: string }): Promise<MentorSessionsPage>
getMentorSession(accessToken: string, sessionId: string, cursor?: string): Promise<MentorSessionDetail>
renameMentorSession(accessToken: string, sessionId: string, title: string): Promise<MentorSession>
removeMentorSession(accessToken: string, sessionId: string): Promise<void>
~~~

These service methods are server-only consumers in this feature. Authenticated
TanStack server functions obtain getCurrentAccess(getRequest()) each time, construct
the server-configured REST client and pass the bearer token only Server-to-Server.
Client calls carry the expected in-memory account e-mail as a scope guard; compare
it to trusted current access before returning data. It never selects/authorizes
the API account. A mismatch discards results and revalidates/remounts the scope.
Use local transport/search validators; do not create a reusable validation package.
Count title lengths consistently by Unicode code points, including Web validation.
Use existing route/navigation wrappers and protected middleware; session search
validation adds no new public path or manually edited routeTree.

The Mentor context owns selectedSessionId, unsent draft/submission key, current
displayed session/list/message pages, search/cursors, panel/history/dialog state,
request errors/pending flags and generation counters for stale-result suppression.
Provider props are children and trusted accountEmail; IntelligencePage consumes it
without changing its existing public page name. MentorFab consumes it without
feature-specific props from AppLayout. MentorChat is the shared conversation-management
composition, rendered by both IntelligencePage and MentorFab. Public operations cover opening/closing/
expanding, new/select session, send/retry first message, set search/load more/older,
rename/remove and refresh. Context value types expose domain names rather than
generic library result objects.

~~~typescript
export type MentorContextProviderProps = PropsWithChildren<{
  accountEmail: string
}>
export type MentorContextValue = {
  selectedSessionId: string | null
  sessionDetail: MentorSessionDetail | null
  sessionsPage: MentorSessionsPage
  draft: string
  search: string
  isPanelOpen: boolean
  panelView: 'conversation' | 'history'
  activeDialog: 'rename' | 'remove' | null
  dialogSessionId: string | null
  isValidatingScope: boolean
  isReadingHistory: boolean
  isReadingMessages: boolean
  isSubmittingFirstMessage: boolean
  isRenamingSession: boolean
  isRemovingSession: boolean
  scopeError: string | null
  historyError: string | null
  conversationError: string | null
  submissionError: string | null
  renameError: string | null
  removalError: string | null
  openPanel(): void
  closePanel(): void
  showPanelHistory(): void
  showPanelConversation(): void
  expandConversation(): void
  startNewConversation(): void
  selectSession(sessionId: string): Promise<void>
  setDraft(value: string): void
  setSearch(value: string): void
  sendFirstMessage(): Promise<void>
  loadMoreSessions(): Promise<void>
  loadOlderMessages(): Promise<void>
  openRenameDialog(sessionId: string): void
  openRemoveDialog(sessionId: string): void
  closeDialog(): void
  renameSession(title: string): Promise<void>
  removeSession(): Promise<void>
  refresh(): Promise<void>
}
~~~

List row actions can target an unselected owned session through dialogSessionId.
Deleting that row does not discard a different selected conversation. Error handling
uses the existing shared feedback convention and accessible owning-field/dialog text.
Deletion invalidates in-flight reads/first-send confirmations for the removed target,
so an older response cannot restore its visible content or selected URL.

This is current-screen state, not a reusable response cache: no Mentor queries in
the persistent root QueryClient. Use domain-owned request hooks/server functions,
abort/ignore superseded requests, and fetch again on the approved triggers.
Do not deduplicate writes by dropping the stable submission key. No localStorage,
sessionStorage or conversation persistence in router/query state beyond the selected
public session ID. Do not carry content across account scopes. Visible mutations
wait for Server success; after success re-fetch affected current views.

**Persistence and transaction guarantees.** Add intelligence_mentor_sessions and
intelligence_mentor_messages. Session rows contain active domain fields plus
submission_key, content_fingerprint, normalized_title and nullable deleted_at.
Unique (account_id, submission_key) applies to active rows and tombstones.
Use an active-session index on account_id/last_activity_at/id and message ordering
index on session_id/created_at/id. The account ID is an ownership key without a new
cross-module ORM relationship.

Messages reference the session, and optional in_reply_to_message_id references
a learner message in that same session. Enforce one response per referenced
message, role/reply consistency and referential integrity; repository/use-case
checks plus database constraints cannot permit cross-session replies. A learner
has no reply target. Use timezone-aware timestamps and injected ULIDs/clocks.

Deletion explicitly removes messages and clears every content-bearing field,
created_at/updated_at/last_activity_at included, leaving only RF-07's four fields.
Tombstones never hydrate as active domain entities. Constraints distinguish valid
active rows from cleared tombstones. No automatic retention job is introduced.
Do not extend account closure, account deleted events or unrelated seeders.

All repository methods operate within IntelligenceDatabase.transaction(); only
that context manager commits/rolls back. Repositories never commit or retain
sessions. Use parameter-bound PostgreSQL transaction advisory locking for the
account/submission key (an existing technical pattern in Identity), uniqueness as
the final guard, and SELECT FOR UPDATE on active sessions for mutations.
Complete/delete/rename acquire the session lock before message operations.
Never hold a transaction/lock during model inference.

Generate the migration with the existing db:migrate task, inspect metadata/imports,
upgrade/downgrade/re-upgrade and drift on a disposable database. It adds empty
tables, so no existing-data backfill is needed; preserve PlanningSession data.
Downgrade removes only these new objects and is destructive for their data;
exercise it only in the disposable validation environment.

**Title composition and future integration.** Resolve the fixed title model
profile to openai/gpt-6-luna through OpenRouter, independently of the existing
Jev Decisions assessment provider. Agent instructions treat message text as
untrusted data, ask only for a short pt-BR title and expose no tools.
MentorTitleOutput is a strict Pydantic object with only title (1–120 code points).
MentorTitleAgent subclasses native Agent and accepts a resolved native Model;
AgnoGenerateMentorTitleWorkflow subclasses Workflow, keeps native run semantics,
and implements the Core generate method to map validated output to str.
No Agno types reach Core. Model/client construction belongs to the provider/pipe,
not agent definitions; lifespan closes owned clients, with no cross-user agent
history, SDK retries, provider fallback models, storage, tracing or prompt logging.

~~~python
class MentorTitleOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=120)

class MentorTitleAgent(Agent):
    def __init__(self, model: Model) -> None: ...

class AgnoGenerateMentorTitleWorkflow(Workflow):
    def __init__(self, agent: MentorTitleAgent) -> None: ...
    def generate(self, first_message: str) -> str: ...
~~~

Dependency construction must not reject a valid first send before its fallback
can run. Missing credentials/privacy capability is reported by the injected
workflow when generate is invoked, as a typed title-unavailable failure. Lazy
construction or an unavailable implementation of the same Core port may supply
this condition; neither performs inference or escapes the creation fallback.

Require provider.zdr=true, provider.data_collection=deny and support for requested
structured-output parameters; disable automatic provider fallbacks for the approved
single attempt. Aggregator prompt logging must separately be disabled and verified;
ZDR alone is insufficient. If compliant configuration cannot be established,
refuse external inference and use fallback. Never relax privacy to obtain a title.
Only account-free minimal input and validated output cross the workflow boundary.

The public internal FinalizeMentorResponseUseCase is implemented now, but has
**no production publisher/worker or public REST endpoint in this slice**. A later
response delivery supplies trusted account/session/learner-message IDs and content,
checks its quota/pedagogical permissions and uses this operation instead of writing
repositories/upserting sessions. No event/outbox message, Inngest registration,
cancellation worker, Memory adapter or account-purge integration is added here.
Until that delivery, show Mensagem salva. A resposta ainda não está disponível.
Keep subsequent-send controls unavailable; do not claim a queued/running job.

## Runtime Flow

1. Protected AppLayout mounts the Intelligence context and FAB with trusted account
   scope. Page reads optional session from the validated URL; FAB leaves the
   originating route unchanged. Draft/open/search/list actions perform fresh reads.
2. First send preserves exact text, validates non-whitespace input and stable UUID,
   then enters a short preflight read. Matching active submission returns its current
   detail (including any manual rename); a tombstone returns private not-found and
   mismatched content conflicts before inference.
3. Without any open transaction, run the bounded title attempt on the allowed prefix
or choose fallback. A simultaneous matching request can also reach this stage.
4. The write transaction locks account/submission, rereads and applies the same
   replay/conflict/deletion rules. Only the winning request mints/persists active
   session plus learner message; repository/commit failures roll back both.
5. HTTP 201/200 confirms acceptance. The UI clears the sent draft, selects the
   persisted ID, synchronizes the page URL if applicable, and fetches history.
   Lost responses preserve the in-memory key/text for retry. Reload recovery uses
   history; it does not promise recovery of a discarded unsent key/draft.
6. Read/search cursors always include authenticated ownership/deleted filtering.
   Auto-loading appends distinct IDs; search/scope/selection changes abort or ignore
   older completions. Opening/renaming does not modify last_activity_at.
7. Rename locks/rechecks ownership and updates title/search/updated_at together.
   Delete locks the same session, removes messages, clears content and retains the
   reservation. Success clears selected display/URL; failure preserves confirmation
   state. A racing late response either commits before deletion and is removed,
   or sees the absent active target and does nothing.
8. Future completion locks session, checks the learner message and existing reply,
   applies RF-08, persists one reply and updates activity atomically. No branch
   inserts a session. Logout/unmount/focus scope change clears UI state and late
   completions cannot expose or reselect an old account's conversation.

# Verification Contract

## Shared setup

All new test paths below are **planned**, not existing/executed evidence.
At implementation kickoff create evaluation.md; first reconcile filenames against
the actual declarations/diff and runner discovery. Invoke only existing files and
actual test names. A missing planned file, empty selection, skip or unavailable
dependency is not a pass. Do not create tests solely to satisfy this inventory.
All Server tests use Test<Subject> classes; use-case ports use autospec mocks.
Web widget tests mock only the owning behavior hook and render real internal children;
hook/context/route tests cover the actual state and transport wiring.

Existing Server prerequisites: tests/conftest.py, tests/fixtures/postgres_fixture.py
(PostgreSQL 17, Alembic head, injected engine, per-test cleanup) and
tests/fixtures/redis_fixture.py (ordinary pytest autouse disposable Redis).
Use AccountFaker from src/shifu/fakers/identity/entities/account_faker.py for two
valid active accounts. Controller auth doubles/SharedPipe overrides exercise
trusted ownership, not real JWT verification; VM-01 supplies the real auth proof.
Use disposable databases only for automated persistence/concurrency/migration checks.
Core mutation excludes global conftest and requires no Docker.

Existing Web composition: tests/playwright.ts, tests/fixtures/identity-module-fixture.ts
and the BFF fixture; retain function-specific request matching rather than
intercepting all server functions with one response. Browser suites use their
existing isolated/mocked transport and prove rendered route contracts; they do not
prove real authentication or Server persistence.

VM-01 uses the existing local actor documented under Tooling's local seed section;
resolve its password privately there, never copy credentials or auth state here.
Load apps/web/.playwright-cli/states/shifu-auth-state.json without printing it;
use visible login if expired. Missing account/services are diagnosed setup blockers,
not permission to reseed/reset shared data. Start only needed services via documented
commands, verify docker compose ps, the configured API GET /health and web login,
and record actual ports. Defaults: Web 7000, API 7777. No Inngest is required.
Use a unique task marker and clean up only conversations created by this journey.
Close only task-started sessions/processes; leave shared Docker services running.

## Automated

### CI-01 — Core acceptance, isolation and safe transitions

**Criteria:** CA-01–CA-09.
**Proof:** planned files under apps/server/tests/intelligence/core/use_cases/:
test_create_mentor_session_use_case.py, test_list_mentor_sessions_use_case.py,
test_get_mentor_session_use_case.py, test_rename_mentor_session_use_case.py,
test_remove_mentor_session_use_case.py, test_finalize_mentor_response_use_case.py.
One mirrored file per use case, mocks only; no database/provider-owned tests.
From apps/server:

~~~bash
uv run pytest tests/intelligence/core/use_cases/test_create_mentor_session_use_case.py tests/intelligence/core/use_cases/test_list_mentor_sessions_use_case.py tests/intelligence/core/use_cases/test_get_mentor_session_use_case.py tests/intelligence/core/use_cases/test_rename_mentor_session_use_case.py tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py tests/intelligence/core/use_cases/test_finalize_mentor_response_use_case.py
~~~

**Passing condition:** exact message preservation; no empty record; title failure/
fallback, rollback, ownership, replay/conflict/tombstone, pending/completion and
mutation guards all asserted. Include empty/whitespace/code/multiline/Unicode/emoji/
long text; title lengths 0/1/119/120/121; prefix lengths 999/1000/1001; page counts
0/1/29/30/31/61 and timestamp ties; literal %, _, slash/backslash; diacritics and
mixed case; missing/foreign/deleted records; exact/divergent response replays.
Do not claim mocks prove real uniqueness, locks or commits.

### CI-02 — Composed title inference boundary

**Criteria:** CA-02, CA-09.
**Proof:** planned apps/server/tests/intelligence/ai/generative/agno/workflows/test_agno_generate_mentor_title_workflow.py
plus consuming creation tests in CI-01/CI-03. From apps/server:

~~~bash
uv run pytest tests/intelligence/ai/generative/agno/workflows/test_agno_generate_mentor_title_workflow.py
~~~

**Passing condition:** deterministic model/HTTP doubles verify native Agent/Workflow
composition, strict output, prefix-only input, no tools/history/raw traces, fixed
OpenRouter model/profile, privacy routing and suppression of aggregator logging
unless verified disabled; one attempt within the deadline and typed failures. No
usage-quota enforcement, accounting or persistence is introduced for this auxiliary
title call, per the explicit task scope.
Provider adapters have no dedicated suite. Real inference is opt-in with synthetic
input, verified eligible routing/logging and no production data; title integration
cannot be claimed from a mocked core workflow alone.

### CI-03 — HTTP persistence, pagination and concurrent requests

**Criteria:** CA-01–CA-07 and CA-09; response-finalization proof is CI-12.
**Proof:** planned apps/server/tests/intelligence/server/controllers/
test_create_mentor_session_controller.py, test_list_mentor_sessions_controller.py,
test_get_mentor_session_controller.py, test_rename_mentor_session_controller.py,
test_remove_mentor_session_controller.py. From apps/server:

~~~bash
uv run pytest tests/intelligence/server/controllers/test_create_mentor_session_controller.py tests/intelligence/server/controllers/test_list_mentor_sessions_controller.py tests/intelligence/server/controllers/test_get_mentor_session_controller.py tests/intelligence/server/controllers/test_rename_mentor_session_controller.py tests/intelligence/server/controllers/test_remove_mentor_session_controller.py
~~~

**Passing condition:** real registered HTTP routes, database transactions/constraints,
serialization, private no-store headers, validation/auth/error mapping, scoped search/
cursor pages and commits/rollback. Two concurrent TestClients share the disposable
engine. Assert matching/different-key races, retry after lost response, rename order,
delete/repeated-delete and post-delete send replay without duplicate rows.
Controller suites exercise registered HTTP operations only; they do not directly
invoke use cases, including the internal response finalizer. Verify HTTP-observable
constraints, private reads and deletion effects through these owning routes. CI-12
provides the otherwise unobservable finalizer persistence/locking evidence.
No artificial completion endpoint, repository suite or database test module.

### CI-04 — Context, route, transport and owning widgets

**Criteria:** CA-01, CA-04–CA-07, CA-09–CA-11.
**Proof:** planned context, IntelligencePage, MentorChat, MentorFab and the
behavior-owning MentorChat child tests below; existing AppLayout
test is modified. From repository root, after planned files exist:

~~~bash
pnpm --filter web exec vitest run src/routes/intelligence/tests/-intelligence-route.test.ts src/rest/services/tests/intelligence-service.test.ts src/ui/intelligence/hooks/tests/mentor-server-functions.test.ts src/ui/intelligence/contexts/mentor-context/tests/use-mentor-context-provider.test.ts src/ui/intelligence/widgets/pages/intelligence-page/tests/intelligence-page.test.tsx src/ui/intelligence/widgets/pages/intelligence-page/tests/use-intelligence-page.test.ts src/ui/intelligence/widgets/components/mentor-chat/tests/mentor-chat.test.tsx src/ui/intelligence/widgets/components/mentor-chat/tests/use-mentor-chat.test.ts src/ui/intelligence/widgets/components/mentor-fab/tests/mentor-fab.test.tsx src/ui/intelligence/widgets/components/mentor-fab/tests/use-mentor-fab.test.ts src/ui/intelligence/widgets/components/mentor-chat/session-history/tests/session-history.test.tsx src/ui/intelligence/widgets/components/mentor-chat/session-history/tests/use-session-history.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/conversation.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/use-conversation.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/use-composer.test.ts src/ui/intelligence/widgets/components/mentor-chat/rename-session-dialog/tests/rename-session-dialog.test.tsx src/ui/intelligence/widgets/components/mentor-chat/rename-session-dialog/tests/use-rename-session-dialog.test.ts src/ui/intelligence/widgets/components/mentor-chat/remove-session-dialog/tests/remove-session-dialog.test.tsx src/ui/intelligence/widgets/components/mentor-chat/remove-session-dialog/tests/use-remove-session-dialog.test.ts src/ui/shared/widgets/layouts/app-layout/tests/app-layout.test.tsx src/ui/learning/widgets/components/add-skill-foundations-dialog/tests/add-skill-foundations-dialog.test.tsx
~~~

**Passing condition:** all exposed context actions/states; real child composition;
draft/page/FAB continuity, fresh reads/no cache, pending acceptance, recoverable
failures, idempotent retries, 300 ms search debounce, automatic pagination/older
history scroll anchoring, rename/delete confirmation and pessimistic visible updates.
Cover keyboard, disabled future controls, scope changes/async focus validation and
stale results. Use fake timers/request promises for timing, not real sleeps.

**Revision 7 coverage supplement:** add these three focused boundary suites to
measure eligible changed route/service/server-function lines that the consumer
tests cannot execute under Vitest:

- `src/routes/intelligence/tests/-intelligence-route.test.ts` checks the route's
  registered search validator and authentication callback. It uses a mocked
  `createFileRoute`; CI-05 remains the proof of real route behavior.
- `src/rest/services/tests/intelligence-service.test.ts` checks Mentor HTTP
  method/path/query/header/body mapping, DTO mapping and failures with a fake
  `RestClient`; it performs no network requests.
- `src/ui/intelligence/hooks/tests/mentor-server-functions.test.ts` invokes the
  registered handler callbacks through a mocked server-function builder and
  mocked request/auth/provider boundaries. It verifies request access, account
  scope and operation forwarding without invoking unsupported TanStack Start
  request-context internals; CI-05 and the production build remain runtime
  integration evidence.

These are the only new Web boundary-test exceptions for this feature. Query and
action hooks, React Query, provision adapters and unrelated REST services still
receive no dedicated tests.

### CI-05 — Routed page and authenticated-shell integration

**Criteria:** CA-01, CA-04–CA-07, CA-09–CA-11.
**Proof:** existing apps/web/tests/intelligence/intelligence-page.test.ts and
apps/web/tests/shared/app-layout.test.ts, extended without renaming the page.
From repository root:

~~~bash
pnpm --filter web exec playwright test tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts
~~~

**Passing condition:** real route/hook composition, protected redirect, optional
session URL validation and final URLs, outgoing method/path/query/body, visible
history/draft/pending/rename/delete outcomes, no cache reuse, page/FAB continuation,
account-change rejection and desktop/mobile keyboard flows. Mocked transport is
explicit; persistence/real auth remain CI-03/VM-01. Do not run unrelated full suites.

### CI-06 — Targeted mutation of correctness-critical use cases

**Criteria:** CA-03, CA-07–CA-09.
**Required:** yes, for ownership/replay/deletion/once-only response guards. From apps/server:

~~~bash
uv run poe test:mutation --core --files src/shifu/intelligence/core/use_cases/create_mentor_session_use_case.py src/shifu/intelligence/core/use_cases/remove_mentor_session_use_case.py src/shifu/intelligence/core/use_cases/finalize_mentor_response_use_case.py --tests tests/intelligence/core/use_cases/test_create_mentor_session_use_case.py tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py tests/intelligence/core/use_cases/test_finalize_mentor_response_use_case.py
~~~

**Passing condition:** verified intended targets/tests, at least Tooling's 70%
changed-file gate, and no surviving non-equivalent mutant weakening these critical
guards. Review inverted/removed comparisons, missing early returns, wrong account/
message targets, duplicate insertion and removed deletion checks. Record exact
targets, elapsed time, killed/survived/uncovered/timeout/error outcomes and reasoned
equivalence dispositions in Evaluation; errors or unexecuted required proof block.
Other use cases use direct exhaustive acceptance assertions; do not broaden mutation
to them, other layers, whole packages or --all without separate authorization.
Full-module baseline regression is remote CI evidence, not inferred from this
local subset. Web mutation is not applicable: no configured runner.

### CI-07 — Types and architecture

**Scope:** both affected apps and their consumers. From repository root:

~~~bash
pnpm --filter web check:types
pnpm --filter web check:architecture
~~~

From apps/server:

~~~bash
uv run poe check:types
uv run poe check:architecture
~~~

**Passing condition:** strict types, lawful imports/exports/registration, no new
dependency cycle, and framework-free Core. Preserve existing Jev/PlanningSession
contracts. Source changes are required during implementation; authoring does not
claim these checks have run.

### CI-08 — Scoped lint and formatting

**Scope:** actual changed supported Web/source/test/config files and Python files
from this Spec, including directly affected shared consumers. Use exact verified
paths; below are executable initial directory selections for the planned boundaries.
From repository root:

~~~bash
pnpm exec biome check apps/web/src/ui/intelligence apps/web/src/rest/services/intelligence-service.ts apps/web/src/routes/intelligence/index.tsx apps/web/src/ui/shared/widgets/layouts/app-layout apps/web/tests/intelligence/intelligence-page.test.ts apps/web/tests/shared/app-layout.test.ts
~~~

From apps/server:

~~~bash
uv run ruff check --no-fix src/shifu/intelligence tests/intelligence src/shifu/app.py
uv run ruff format --check src/shifu/intelligence tests/intelligence src/shifu/app.py
~~~

**Passing condition:** no errors or formatting failures; include the actual generated
migration and any additionally changed primitive/settings/contracts in the exact
selection once their filenames exist. Never run a mutating fixer as validation.

### CI-09 — Complexity disposition

**Scope:** submission/replay/deletion/completion branching, title boundary and Web
state/focus/pagination coordination.
**Proof:** CI-08's Ruff C90 (McCabe maximum 10, current default; configuration does
not override it) and configured Biome complexity diagnostics; inspect changed logic.
**Passing condition:** no Ruff C90 failures; record Biome warning diagnostics and
their disposition. No dedicated quantitative metrics runner/baseline is configured;
independent metrics are not applicable, and no numerical complexity pass is claimed.

### CI-10 — Local changed-code coverage

**Scope:** every eligible changed production file in both apps, including indirect
adapter/model files, using permitted consumer/AI/controller/widget tests and the
revision 7 purpose-limited Web and Intelligence adapter supplements.
Use the verified kickoff base (authoring HEAD f5dc8f29fd39a7c6c08df494d077d35bfda66c4e;
reconcile if the implementation starts on a different base) and the actual CI-01–
CI-05 selections. After the planned files exist, the initial exact Web command,
from repository root, is:

~~~bash
pnpm --filter web test:coverage:changed --base f5dc8f29fd39a7c6c08df494d077d35bfda66c4e -- src/routes/intelligence/tests/-intelligence-route.test.ts src/rest/services/tests/intelligence-service.test.ts src/ui/intelligence/hooks/tests/mentor-server-functions.test.ts src/ui/intelligence/contexts/mentor-context/tests/use-mentor-context-provider.test.ts src/ui/intelligence/widgets/pages/intelligence-page/tests/intelligence-page.test.tsx src/ui/intelligence/widgets/pages/intelligence-page/tests/use-intelligence-page.test.ts src/ui/intelligence/widgets/components/mentor-chat/tests/mentor-chat.test.tsx src/ui/intelligence/widgets/components/mentor-chat/tests/use-mentor-chat.test.ts src/ui/intelligence/widgets/components/mentor-fab/tests/mentor-fab.test.tsx src/ui/intelligence/widgets/components/mentor-fab/tests/use-mentor-fab.test.ts src/ui/intelligence/widgets/components/mentor-chat/session-history/tests/session-history.test.tsx src/ui/intelligence/widgets/components/mentor-chat/session-history/tests/use-session-history.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/conversation.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/use-conversation.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/use-composer.test.ts src/ui/intelligence/widgets/components/mentor-chat/rename-session-dialog/tests/rename-session-dialog.test.tsx src/ui/intelligence/widgets/components/mentor-chat/rename-session-dialog/tests/use-rename-session-dialog.test.ts src/ui/intelligence/widgets/components/mentor-chat/remove-session-dialog/tests/remove-session-dialog.test.tsx src/ui/intelligence/widgets/components/mentor-chat/remove-session-dialog/tests/use-remove-session-dialog.test.ts src/ui/shared/widgets/layouts/app-layout/tests/app-layout.test.tsx src/ui/learning/widgets/components/add-skill-foundations-dialog/tests/add-skill-foundations-dialog.test.tsx
~~~

Initial exact Server command, from apps/server:

~~~bash
uv run poe test:changed-coverage --base f5dc8f29fd39a7c6c08df494d077d35bfda66c4e --tests tests/intelligence/core/use_cases/test_create_mentor_session_use_case.py --tests tests/intelligence/core/use_cases/test_list_mentor_sessions_use_case.py --tests tests/intelligence/core/use_cases/test_get_mentor_session_use_case.py --tests tests/intelligence/core/use_cases/test_rename_mentor_session_use_case.py --tests tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py --tests tests/intelligence/core/use_cases/test_finalize_mentor_response_use_case.py --tests tests/intelligence/ai/generative/agno/workflows/test_agno_generate_mentor_title_workflow.py --tests tests/intelligence/server/controllers/test_create_mentor_session_controller.py --tests tests/intelligence/server/controllers/test_list_mentor_sessions_controller.py --tests tests/intelligence/server/controllers/test_get_mentor_session_controller.py --tests tests/intelligence/server/controllers/test_rename_mentor_session_controller.py --tests tests/intelligence/server/controllers/test_remove_mentor_session_controller.py --tests tests/intelligence/adapters/test_mentor_persistence_adapters.py --tests tests/core/intelligence/use_cases/test_start_planning_use_case.py --tests tests/rest/controllers/intelligence/test_start_planning_controller.py
~~~

**Passing condition:** per eligible file, at least 85% statements/functions/lines and
80% branches; an unmeasured changed file fails. Record base/head, exact tests/counts,
per-file metrics, elapsed time and report paths in Evaluation. Expand only to a
demonstrably affected permitted consumer if coverage is missing. Revision 7
authorizes only the single added module-scoped PostgreSQL adapter test above to
exercise the tombstone mapper guard and internal response lookup methods that no
registered feature route exposes. Do not create a generic database/repository test
suite or include unrelated dirty source. A coverage execution can replace an
identical earlier test run; no duplicate full run.

### CI-11 — Migration compatibility and affected build gates

**Proof:** CI-03 uses current Alembic head; additionally use a disposable database
for upgrade, downgrade to the new revision's actual parent, re-upgrade and drift.
From apps/server, with that disposable URL:

~~~bash
uv run alembic upgrade head
uv run alembic check
uv run poe build
~~~

Generate using uv run poe db:migrate "add mentor sessions"; use the generated actual
revision/parent for downgrade, never a fabricated filename or a shared-data reset.
From repository root:

~~~bash
pnpm --filter web generate-routes
pnpm --filter web build
~~~

**Passing condition:** new constraints/indexes and model registration match migration,
no schema drift or PlanningSession loss, reversible new schema in disposable setup,
and affected builds succeed. Route generation applies only when route inputs change.
For the shared transaction's existing consumer, run the unchanged verified
tests/core/intelligence/use_cases/test_start_planning_use_case.py and
tests/rest/controllers/intelligence/test_start_planning_controller.py from apps/server;
do not extend their legacy locations. No Inngest/job test is required without a new job.
Local checks are scoped; publication, if separately requested, requires current-head
applicable aggregates from the existing Web/Server CI workflows.

### CI-12 — Disposable evidence for internal response persistence

**Criteria:** CA-05, CA-08 and the internal completion portion of CA-09.
**Type:** Automated delivery check, outside pytest/controller suites. The Database
Rule Pack permits focused disposable-environment evidence when the primitive
cannot be adequately observed through an existing application boundary. This slice
has no completion endpoint or job; do not invent one for testing.

**Proof:** at implementation, create a reproducible temporary check script at
apps/server/test-results/mentor-response-persistence-check.py (verified ignored;
planned runtime artifact, not an existing test file or a committed database suite).
Record its exact source or reproducible procedure, invocation and results in
Evaluation. Run only after the script and production declarations exist, from
apps/server:

~~~bash
uv run python test-results/mentor-response-persistence-check.py
~~~

**Setup and procedure:** use the existing Postgres fixture's construction recipe,
not a direct call to its pytest fixture: own a disposable PostgreSQL 17 container,
apply actual Alembic head and inject its engine into the real Intelligence database.
Use valid synthetic actors, real identifiers/clock, the production creation/read/
completion/removal use cases and a deterministic title-workflow double, without
external inference. Seed longer history solely inside this owned environment as
needed to exercise message pagination. Use explicit assertions and synchronized
threads/barriers, not sleep timing, for completion-before-delete and
delete-before-completion, exact/divergent duplicate completions and foreign actors.
Dispose the engine and stop only this owned container in finally cleanup; never
truncate or reset a shared database.

**Passing condition:** persisted response/read mapping and message cursors are
correct; one response per learner message, exact replay success and divergent
replay conflict; foreign/missing/deleted targets have no write; both lock orders
finish without deadlock, orphan content or resurrection. After deletion, verify
only the four approved reservation fields remain and all owned content is purged.
Record actual assertions/results and any failures; mocked Core tests or an
unexecuted script cannot substitute for this real persistence evidence.

## Manual

### VM-01 — Real private conversation management, page and FAB

**Type:** Manual. **Criteria:** CA-01, CA-04, CA-06, CA-07, CA-09, CA-10.
**Tool:** Playwright CLI from apps/web; named task-owned session; Shared setup.
Inspect installed CLI help before selecting supported snapshot/state/viewport/
screenshot commands. Initial documented command:

~~~bash
playwright-cli -s=mentor-sessions open http://127.0.0.1:7000/login
~~~

**Procedure:** authenticate using the existing valid local actor/state; use desktop
1440×900. Open a new draft and verify no POST/empty history entry. Send a unique
benign multiline message, observe successful POST, definitive title, real persisted
pending message and page session URL. Reload and verify the same IDs/content.
Rename to an accented task marker, find it without accents, move to an existing
protected area, reopen the same session via FAB and expand to its page URL.
Cancel deletion once, then confirm and reload/search to verify absence.
Repeat the narrow happy path at 390×844, including essential keyboard navigation,
dialog focus/Escape/cancel/restore and FAB fullscreen behavior.

**Passing condition:** actual authenticated Server requests and persisted visible
effects after reload, correct final URLs, fresh requests on transitions, disabled
future controls and truthful pending state; no relevant unhandled console errors.
Use a second independently authenticated browser scope only if testing foreign access
manually is necessary to close an automation gap; CI-03 owns systematic isolation.
Keep artifacts under apps/web/.playwright-cli/{screenshots,snapshots,logs}/, auth
state under states/, and record actual paths/results in Evaluation. Delete only
task-created sessions; retain no credentials or runtime captures in Git.

## Visual

### VM-02 — Required Mentor states against approved design references

**Type:** Visual. **Criteria:** CA-10, CA-11.
**Reference:** the sole design/handoff.md inventory and its eight inspected exports.
Reuse VM-01 happy-path captures: desktop page draft/accepted conversation, FAB
draft/history/selected conversation, rename/delete confirmation, and mobile
fullscreen/new/history/selected conversation/dialogs. Dialog screenshots may be
cropped from their full-viewport capture. Compare at the handoff's stated viewport
sizes; mobile session-management states use the explicitly approved visual assumption.

**Passing condition:** inspect each capture for typography, semantic surfaces,
borders, spacing, panel/sidebar/composer hierarchy, 566 px desktop panel, focus,
disabled controls, wrapping/scrolling and mobile viewport fit. Differences are
limited to the handoff's accepted deviations and actual runtime content.
Saving images without inspecting them is not a visual pass. Negative/loading/error/
recovery matrices remain automated and do not create extra manual journeys.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Shifu — PRD — Intelligence](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83099649), content 83099649, v7, updated 2026-10-05T12:12:33.092Z; retrieved in full 2026-10-08 21:47 UTC and revalidated with identical full content at 22:59 UTC; parent PRD's 82804737 under Shifu 82509992 | RP-02/03/04/06/11/12/13/14; JN-01/14/16/17 | Preserve canonical meaning and record bounded disposition; first accepted send establishes history as approved | No Confluence write. Response and account-lifecycle outcomes remain partial/deferred as stated in Scope. |
| [Privacy and data lifecycle policy](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/100106241), content 100106241, v4, updated 2026-10-08T01:07:15.769Z; retrieved in full 2026-10-08 and revalidated with identical full content at 22:59 UTC | Title inference and owned content | Verify ZDR route and aggregator logging disabled; synchronous deletion of owned conversation content with approved minimal anti-replay metadata | Policy leaves individual-conversation purge deadline open; this slice does not import the account-erasure 24-hour deadline or implement account closure. |
| [SHIFU-99](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-99), Implementar gestão de conversas do Mentor; issue 12609; parent SHIFU-29; updated 2026-10-08T18:44:44.799-0300 | Delivery source | Account-closure requirement explicitly excluded by user; generation deferred; approved persistence finalizer included | Jira is unchanged. Do not claim all issue criteria delivered. |
| [Architecture](../../../architecture.md), [Modules](../../../modules.md), [SDD](../../../sdd.md), [Tooling](../../../tooling.md) | Ownership, lifecycle and checks | Preserve Intelligence ownership, planning/Jev consumers and scoped testing; create Evaluation only at implementation kickoff | CodeGraph queries verified Intelligence/Shared composition, submission/lock patterns, controller error mapping and existing tests; current authoring HEAD recorded in CI-10. |
| [Modules — account lifecycle](../../../modules.md) | Global Identity deletion participation requirement | **Explicit user-authorized scope exception:** account closure and its integration are excluded from this bounded delivery, despite the general module requirement | Preserve the global requirement and canonical PRD unchanged. This Spec claims neither completed account erasure nor future account-purge fencing; existing active-account authorization remains required. The exception does not add a delivery dependency or authorize retaining this data after a future account-purge implementation. |
| Explicit user clarification, 2026-10-08 | Delivery scope | Usage-quota enforcement/accounting and account deletion are out of scope; title inference does not read or mutate quota state | This task-specific scope governs the bounded implementation. The general module lifecycle and AI quota requirements remain unchanged for other work. |
| [Rules router](../../../rules.md) and Rule Pack: Python conventions; Core; Use-case testing; REST; Controller testing; Database; Server app; Provision; AI; TypeScript conventions; UI; Web routing; Widget testing | All affected layers | Read complete selected rules and reselect if scope expands; no messaging/job rule obligation without a producer/job | Test placement conflict: the more specific Widget Testing rule requires widget tests in tests/, despite UI's general direct-colocation paragraph; current Vitest discovery agrees. |
| [Design](../../../design.md), [Pencil](../../../../design/shifu.pen), [handoff](design/handoff.md) | Visual implementation | Update only the approved desktop width from 400 to 566 px; respect shared dialog/focus/border rules and accepted mobile assumption | Pencil remains unchanged by this authoring task. Design section 6.6's historical v6/v3 references are not current authority; this Spec uses PRD v7/policy v4. |
| [OpenRouter GPT-6 Luna](https://openrouter.ai/openai/gpt-6-luna), [ZDR routing](https://openrouter.ai/docs/guides/features/zdr), official Agno docs via Context7 | Fixed model, privacy parameters, native SDK primitives | Recheck installed/resolved APIs when adding dependencies; no automatic alternative model/privacy downgrade | Missing compliant live configuration uses fallback; it does not authorize a less-private route. |

Rule files are under documentation/rules/ with these exact names:
python-conventions-rules.md, core-layer-rules.md, use-case-testing-rules.md,
rest-layer-rules.md, controllers-testing-rules.md, database-layer-rules.md,
server-app-layer-rules.md, provision-layer-rules.md, ai-layer-rules.md,
typescript-conventions-rules.md, ui-layer-rules.md, web-app-routing-rules.md,
widget-testing-rules.md. No reusable Web validation package is introduced.

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-08 | Initial complete contract with approved scope, fixed OpenRouter Luna title inference, synchronous final title, idempotency/tombstones, private completion boundary, fresh reads, automatic paging and required checkers | SHIFU-99, Intelligence v7, privacy policy v4 and explicit in-chat design approval; account closure/integration excluded by user |
| 2 | 2026-10-08 | Separate internal-finalizer persistence evidence from HTTP controller suites; explicitly record the user-authorized account-lifecycle scope exception | Independent Spec review; Database/Controller testing rules and prior explicit user exclusion |
| 3 | 2026-10-08 | Replace MentorPanel with MentorFab; share MentorChat between page/FAB and specify its owned history, conversation/composer and dialog children with permitted test boundaries | User-approved widget composition (Q50); shared context and behavior remain unchanged |
| 4 | 2026-10-08 | Show the approved title-agent file tree, including its Core port, Agno agent/output/workflow, OpenRouter provider, composition pipe and CI-02 test path | Explicit user request and approval; existing contracts and scope unchanged |
| 5 | 2026-10-08 | Show MentorContext and the two query/three action hooks, their provider-consumer direction, fresh-read semantics and consumer-owned verification | User approval after Q51/context clarification; existing operations and no-cache behavior preserved |
| 6 | 2026-10-08 | Explicitly exclude shared usage-quota enforcement/accounting for auxiliary title inference and reaffirm account deletion as out of scope | User clarification during implementation readiness review; no account-lifecycle or quota capability is added to this delivery |
| 7 | 2026-10-08 | Add narrowly scoped Web route/transport/server-function tests and one PostgreSQL-backed Intelligence adapter test to CI-04/CI-10; retain the 85% statement/function/line and 80% branch thresholds | Explicit user approval during implementation; no product behavior or feature scope changed |

| 8 | 2026-10-09 | Reconcile user-requested FAB reference layout: omit Memories/quota placeholders from FAB, retain disabled controls on page; include panel entrance and reduced-motion handling; verify the directly affected Learning dialog consumer using its existing test | User requested reference alignment and authorized readiness corrections/local conclusion; no quota/account-deletion operation added |
