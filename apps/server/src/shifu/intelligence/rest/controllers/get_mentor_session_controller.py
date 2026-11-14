from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.intelligence.core.domain.structures import MentorResponseSnapshot
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Response as FastApiResponse,
)
from pydantic import BaseModel, TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import GetMentorSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe


_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class Response(BaseModel):
    session: MentorSessionSchemas.Session
    messages: MentorSessionSchemas.MessagesPage
    pending_learner_message_id: str | None
    response: MentorResponseSnapshot | None = None
    summary: MentorSessionSchemas.SummaryState
    memory_items: list[MentorSessionSchemas.MemoryItem] = []
    action_items: list[MentorSessionSchemas.ActionItem] = []


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetMentorSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/mentor-sessions/{session_id}', response_model=Response, status_code=200
        )
        def _(
            session_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            response: FastApiResponse,
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
            cursor: str | None = None,
        ) -> Response:
            detail = GetMentorSessionUseCase(database, access).execute(
                user.account_id, session_id, cursor
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
