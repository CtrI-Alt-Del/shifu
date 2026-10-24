from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Response as FastApiResponse,
)
from pydantic import BaseModel, Field, TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import GetMentorAttachmentBatchUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.pipes import SharedPipe

_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class Response(BaseModel):
    batch_id: str
    expires_at: datetime
    attachments: list[MentorSessionSchemas.Attachment] = Field(default_factory=list)


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetMentorAttachmentBatchController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/mentor-attachment-batches/{batch_id}',
            response_model=Response,
            status_code=200,
        )
        def _(
            batch_id: Annotated[str, Path(pattern=_ID_PATTERN)],
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
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Response:
            batch = GetMentorAttachmentBatchUseCase(
                database, clock_provider, access
            ).execute(user.account_id, batch_id)
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(batch, from_attributes=True)
