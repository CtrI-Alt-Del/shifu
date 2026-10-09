from typing import Annotated

from fastapi import APIRouter, Depends, Response as FastApiResponse, status
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, UUID4, field_validator

from shifu.intelligence.core.interfaces import (
    GenerateMentorTitleWorkflow,
    IntelligenceDatabase,
)
from shifu.intelligence.core.use_cases import CreateMentorSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.pipes import SharedPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    submission_key: UUID4
    first_message: str = Field(min_length=1)

    @field_validator('first_message')
    @classmethod
    def _require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('first_message must contain non-whitespace text')
        return value


class Response(BaseModel):
    session: MentorSessionSchemas.Session
    messages: MentorSessionSchemas.MessagesPage
    pending_learner_message_id: str | None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class CreateMentorSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/mentor-sessions',
            response_model=Response,
            status_code=status.HTTP_201_CREATED,
        )
        def _(
            request: Request,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            identifier_provider: Annotated[
                IdentifierProvider, Depends(IntelligencePipe.get_identifier_provider)
            ],
            clock_provider: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            title_workflow: Annotated[
                GenerateMentorTitleWorkflow,
                Depends(IntelligencePipe.get_generate_mentor_title_workflow),
            ],
        ) -> Response:
            result = CreateMentorSessionUseCase(
                database, identifier_provider, clock_provider, title_workflow
            ).execute(
                user.account_id, str(request.submission_key), request.first_message
            )
            response.status_code = (
                status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
            )
            return _RESPONSE_ADAPTER.validate_python(
                result.detail, from_attributes=True
            )
