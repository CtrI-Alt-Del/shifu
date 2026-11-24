import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import Field, TypeAdapter
from starlette.concurrency import run_in_threadpool

from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import (
    AiQuotaPolicy,
    MentorResponseEvent,
)
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
)
from shifu.intelligence.core.use_cases import (
    FailMentorResponseUseCase,
    FailStaleMentorResponseUseCase,
    ReadMentorResponseEventsUseCase,
)
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.errors import AppError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.core.interfaces import AccountActivityProvider
from shifu.shared.pipes import SharedPipe

_EVENT_ADAPTER = TypeAdapter[MentorResponseEvent](MentorResponseEvent)
_TERMINAL_STATUSES = (
    MentorResponseStatus.COMPLETED,
    MentorResponseStatus.FAILED,
    MentorResponseStatus.CANCELLED,
)
_POLL_SECONDS = 1.0
# Idle polls between two checks for an attempt that no live execution holds.
_RECOVERY_IDLE_POLLS = 15


class StreamMentorResponseController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/mentor-sessions/{session_id}/events', response_model=None, status_code=200
        )
        def _(
            session_id: Annotated[str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')],
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user_unscoped),
            ],
            activity: Annotated[
                AccountActivityProvider,
                Depends(SharedPipe.get_account_activity_provider),
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            quota_policy: Annotated[
                AiQuotaPolicy, Depends(IntelligencePipe.get_ai_quota_policy)
            ],
            quota_calendar: Annotated[
                AiQuotaCalendarProvider,
                Depends(IntelligencePipe.get_ai_quota_calendar_provider),
            ],
            after_sequence: Annotated[int, Query(ge=0)] = 0,
            last_event_id: Annotated[int | None, Header(ge=0)] = None,
        ) -> StreamingResponse:
            use_case = ReadMentorResponseEventsUseCase(database, access)
            recovery = FailStaleMentorResponseUseCase(
                database,
                FailMentorResponseUseCase(
                    database, clock, access, quota_policy, quota_calendar
                ),
            )
            cursor = last_event_id if last_event_id is not None else after_sequence
            with activity.activity(user.account_id, actor=user):
                initial = use_case.execute(user.account_id, session_id, cursor)
            return StreamingResponse(
                _stream(
                    use_case,
                    recovery,
                    activity,
                    user,
                    session_id,
                    cursor,
                    initial,
                ),
                media_type='text/event-stream',
                headers={
                    'Cache-Control': 'private, no-store',
                    'X-Accel-Buffering': 'no',
                },
            )


async def _stream(
    use_case: ReadMentorResponseEventsUseCase,
    recovery: FailStaleMentorResponseUseCase,
    activity: AccountActivityProvider,
    user: AuthenticatedUser,
    session_id: str,
    cursor: int,
    initial: tuple[MentorResponseEvent, ...],
) -> AsyncIterator[str]:
    """Poll the persisted events without holding a worker thread between polls."""
    account_id = user.account_id
    events = initial
    idle_polls = 0
    while True:
        if events:
            idle_polls = 0
            try:
                async with activity.async_activity(account_id, actor=user):
                    for event in events:
                        yield f'id:{event.sequence}\nevent:mentor.response\ndata:{_EVENT_ADAPTER.dump_json(event).decode()}\n\n'
                        cursor = event.sequence
                    if events[-1].status in _TERMINAL_STATUSES:
                        return
            except AppError:
                return
        else:
            yield ': heartbeat\n\n'
            idle_polls += 1
            if idle_polls % _RECOVERY_IDLE_POLLS == 0:
                await _recover_stale_attempt(recovery, activity, user, session_id)
            await asyncio.sleep(_POLL_SECONDS)
        try:
            async with activity.async_activity(account_id, actor=user):
                events = await run_in_threadpool(
                    use_case.execute, account_id, session_id, cursor
                )
        except AppError:
            return


async def _recover_stale_attempt(
    recovery: FailStaleMentorResponseUseCase,
    activity: AccountActivityProvider,
    user: AuthenticatedUser,
    session_id: str,
) -> None:
    """Close an orphaned attempt; its failed event arrives on the next poll."""
    try:
        async with activity.async_activity(user.account_id, actor=user):
            await run_in_threadpool(recovery.execute, user.account_id, session_id)
    except Exception:  # noqa: BLE001 - recovery is best effort and never ends the stream.
        return
