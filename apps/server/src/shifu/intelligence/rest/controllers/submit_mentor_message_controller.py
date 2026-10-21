from typing import Annotated, Self

from fastapi import APIRouter, Depends
from fastapi import Response as FastApiResponse
from pydantic import UUID4, BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from shifu.intelligence.core.domain.structures import (
    MentorContextHint,
    MentorSubmission,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import SubmitMentorMessageUseCase
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
    content: str
    context_hint: MentorContextHintSchema | None = None
    attachment_batch_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode='after')
    def _require_message_or_attachments(self) -> Self:
        if not self.content.strip() and not self.attachment_ids:
            raise ValueError('Message must contain text or attachments')
        return self


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
                    attachment_batch_id=request.attachment_batch_id,
                    attachment_ids=tuple(request.attachment_ids),
                ),
            )
            response.status_code = 200 if use_case.replayed else 202
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
