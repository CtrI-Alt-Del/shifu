from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Response as FastApiResponse,
)
from pydantic import BaseModel, ConfigDict, TypeAdapter, field_validator

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import RenameMentorSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe


_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str

    @field_validator('title')
    @classmethod
    def _validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title or len(title) > 120:
            raise ValueError('title must contain between 1 and 120 code points')
        return title


class Response(MentorSessionSchemas.Session):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class RenameMentorSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.patch(
            '/mentor-sessions/{session_id}', response_model=Response, status_code=200
        )
        def _(
            session_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            request: Request,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            clock_provider: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
        ) -> Response:
            session = RenameMentorSessionUseCase(database, clock_provider).execute(
                user.account_id, session_id, request.title
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(session, from_attributes=True)
