from typing import Annotated
from fastapi import APIRouter, Depends, Response as FastApiResponse
from pydantic import BaseModel, ConfigDict, UUID4, Field, TypeAdapter
from shifu.intelligence.core.domain.structures import MentorResponseSnapshot
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import CancelMentorResponseUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from shifu.shared.pipes import SharedPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    submission_key: UUID4


type Response = MentorResponseSnapshot
_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class CancelMentorResponseController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/mentor-sessions/{session_id}/responses/{attempt_id}/cancel',
            response_model=Response,
            status_code=200,
        )
        def _(
            session_id: Annotated[str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')],
            attempt_id: Annotated[str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')],
            request: Request,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Response:
            result = CancelMentorResponseUseCase(database, clock, access).execute(
                user.account_id, session_id, attempt_id, str(request.submission_key)
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(result)
