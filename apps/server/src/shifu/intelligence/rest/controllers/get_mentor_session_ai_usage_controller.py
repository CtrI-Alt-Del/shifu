from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Response as FastApiResponse
from pydantic import BaseModel, Field, TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import GetMentorSessionAiUsageUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.pipes import SharedPipe


class _Item(BaseModel):
    message_id: str
    attempt_id: str
    percentage: float


class Response(BaseModel):
    items: list[_Item]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetMentorSessionAiUsageController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/mentor-sessions/{session_id}/ai-usage',
            response_model=Response,
            status_code=200,
        )
        def _(
            session_id: Annotated[str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')],
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
        ) -> Response:
            usage = GetMentorSessionAiUsageUseCase(database, access).execute(
                user.account_id, session_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(usage, from_attributes=True)
