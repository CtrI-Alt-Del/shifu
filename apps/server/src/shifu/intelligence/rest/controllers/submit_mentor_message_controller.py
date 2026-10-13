from typing import Annotated
from fastapi import APIRouter, Depends, Response as FastApiResponse
from pydantic import BaseModel, ConfigDict, UUID4, TypeAdapter, Field, field_validator
from shifu.intelligence.core.domain.structures import (
    MentorSubmission,
    MentorContextHint,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import SubmitMentorMessageUseCase
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.intelligence.rest.schemas.mentor_context_hint_schema import (
    MentorContextHintSchema,
)
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
    content: str = Field(min_length=1)
    context_hint: MentorContextHintSchema | None = None

    @field_validator('content')
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Message must contain text')
        return value


class Response(MentorSessionSchemas.Detail):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class SubmitMentorMessageController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/mentor-sessions/{session_id}/messages',
            response_model=Response,
            status_code=202,
        )
        def _(
            session_id: Annotated[str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')],
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
            use_case = SubmitMentorMessageUseCase(database, identifier, clock, access)
            detail = use_case.execute(
                user.account_id,
                session_id,
                MentorSubmission(
                    submission_key=str(request.submission_key),
                    content=request.content,
                    context_hint=MentorContextHint(**request.context_hint.model_dump())
                    if request.context_hint
                    else None,
                ),
            )
            response.status_code = 200 if use_case.replayed else 202
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
