from shifu.shared.core.domain.errors import AppError
from collections.abc import Iterator
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import Field, TypeAdapter

from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import ReadMentorResponseEventsUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.pipes import SharedPipe

_EVENT_ADAPTER = TypeAdapter[MentorResponseEvent](MentorResponseEvent)


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
            after_sequence: Annotated[int, Query(ge=0)] = 0,
            last_event_id: Annotated[int | None, Header(ge=0)] = None,
        ) -> StreamingResponse:
            use_case = ReadMentorResponseEventsUseCase(database, access)
            cursor = last_event_id if last_event_id is not None else after_sequence
            initial = use_case.execute(user.account_id, session_id, cursor)
            return StreamingResponse(
                _stream(use_case, user.account_id, session_id, cursor, initial),
                media_type='text/event-stream',
                headers={
                    'Cache-Control': 'private, no-store',
                    'X-Accel-Buffering': 'no',
                },
            )


def _stream(
    use_case: ReadMentorResponseEventsUseCase,
    account_id: str,
    session_id: str,
    cursor: int,
    initial: tuple[MentorResponseEvent, ...],
) -> Iterator[str]:
    events = initial
    while True:
        try:
            events = use_case.execute(account_id, session_id, cursor)
        except AppError:
            return
        if not events:
            yield ': heartbeat\n\n'
            time.sleep(1)
            continue
        event = events[0]
        yield f'id:{event.sequence}\nevent:mentor.response\ndata:{_EVENT_ADAPTER.dump_json(event).decode()}\n\n'
        cursor = event.sequence
        if len(events) == 1 and event.status in (
            MentorResponseStatus.COMPLETED,
            MentorResponseStatus.FAILED,
            MentorResponseStatus.CANCELLED,
        ):
            return
