from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi import Response as FastApiResponse
from pydantic import UUID4, BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from shifu.intelligence.core.domain.structures import (
    MentorContextHint,
    MentorResponseSnapshot,
)
from shifu.intelligence.core.interfaces import (
    GenerateMentorTitleWorkflow,
    IntelligenceDatabase,
)
from shifu.intelligence.core.use_cases import CreateMentorSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_context_hint_schema import (
    MentorContextHintSchema,
)
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
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
    first_message: str = Field(min_length=1)
    context_hint: MentorContextHintSchema | None = None
    attachment_batch_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)

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
    response: MentorResponseSnapshot | None = None


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
            access_provider: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
            title_workflow: Annotated[
                GenerateMentorTitleWorkflow,
                Depends(IntelligencePipe.get_generate_mentor_title_workflow),
            ],
        ) -> Response:
            result = CreateMentorSessionUseCase(
                database,
                identifier_provider,
                clock_provider,
                title_workflow,
                access_provider,
            ).execute(
                user.account_id,
                str(request.submission_key),
                request.first_message,
                MentorContextHint(**request.context_hint.model_dump())
                if request.context_hint
                else None,
                request.attachment_batch_id,
                tuple(request.attachment_ids),
            )
            response.headers['Cache-Control'] = 'private, no-store'
            response.status_code = (
                status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
            )
            return _RESPONSE_ADAPTER.validate_python(
                result.detail, from_attributes=True
            )
