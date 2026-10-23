from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Response as FastApiResponse,
)
from pydantic import BaseModel, ConfigDict, TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import CreateMentorAttachmentBatchUseCase
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

    session_id: str | None = None


class Response(BaseModel):
    batch_id: str
    expires_at: datetime


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class CreateMentorAttachmentBatchController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/mentor-attachment-batches', response_model=Response, status_code=201
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
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Response:
            batch = CreateMentorAttachmentBatchUseCase(
                database, identifier_provider, clock_provider, access
            ).execute(user.account_id, request.session_id)
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(batch, from_attributes=True)
