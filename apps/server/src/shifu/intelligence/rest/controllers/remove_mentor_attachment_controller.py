from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Response as FastApiResponse,
)

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import RemoveMentorAttachmentUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.pipes import SharedPipe

_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class RemoveMentorAttachmentController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            '/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}',
            response_model=None,
            status_code=204,
        )
        def _(
            batch_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            attachment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
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
        ) -> FastApiResponse:
            RemoveMentorAttachmentUseCase(database, clock_provider, access).execute(
                user.account_id, batch_id, attachment_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            response.status_code = 204
            return response
