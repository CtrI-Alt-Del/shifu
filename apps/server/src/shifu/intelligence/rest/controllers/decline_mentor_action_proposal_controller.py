from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi import Response as FastApiResponse
from pydantic import TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import DeclineMentorActionProposalUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.pipes import SharedPipe

_ID_PATTERN = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'


class Response(MentorSessionSchemas.ActionItem):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class DeclineMentorActionProposalController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/mentor-sessions/{session_id}/action-proposals/{proposal_id}/decline',
            response_model=Response,
            status_code=200,
        )
        def _(
            session_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            proposal_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            access: Annotated[
                MentorAccessProvider,
                Depends(IntelligencePipe.get_mentor_access_provider),
            ],
        ) -> Response:
            item = DeclineMentorActionProposalUseCase(database, clock, access).execute(
                user.account_id, session_id, proposal_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(item, from_attributes=True)
