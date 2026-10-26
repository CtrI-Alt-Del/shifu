import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import Field, TypeAdapter
from starlette.concurrency import run_in_threadpool

from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import (
    FailMentorResponseUseCase,
    FailStaleMentorResponseUseCase,
    ReadMentorResponseEventsUseCase,
)
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.errors import AppError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
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
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
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
            after_sequence: Annotated[int, Query(ge=0)] = 0,
            last_event_id: Annotated[int | None, Header(ge=0)] = None,
        ) -> StreamingResponse:
            use_case = ReadMentorResponseEventsUseCase(database, access)
            recovery = FailStaleMentorResponseUseCase(
                database, FailMentorResponseUseCase(database, clock, access)
            )
            cursor = last_event_id if last_event_id is not None else after_sequence
            initial = use_case.execute(user.account_id, session_id, cursor)
            return StreamingResponse(
                _stream(
                    use_case, recovery, user.account_id, session_id, cursor, initial
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
    account_id: str,
    session_id: str,
    cursor: int,
    initial: tuple[MentorResponseEvent, ...],
) -> AsyncIterator[str]:
    """Poll the persisted events without holding a worker thread between polls."""
    events = initial
    idle_polls = 0
    while True:
        if events:
            idle_polls = 0
            for event in events:
                yield f'id:{event.sequence}\nevent:mentor.response\ndata:{_EVENT_ADAPTER.dump_json(event).decode()}\n\n'
                cursor = event.sequence
            if events[-1].status in _TERMINAL_STATUSES:
                return
        else:
            yield ': heartbeat\n\n'
            idle_polls += 1
            if idle_polls % _RECOVERY_IDLE_POLLS == 0:
                await _recover_stale_attempt(recovery, account_id, session_id)
            await asyncio.sleep(_POLL_SECONDS)
        try:
            events = await run_in_threadpool(
                use_case.execute, account_id, session_id, cursor
            )
        except AppError:
            return


async def _recover_stale_attempt(
    recovery: FailStaleMentorResponseUseCase, account_id: str, session_id: str
) -> None:
    """Close an orphaned attempt; its failed event arrives on the next poll."""
    try:
        await run_in_threadpool(recovery.execute, account_id, session_id)
    except Exception:  # noqa: BLE001 - recovery is best effort and never ends the stream.
        return
