from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response as FastApiResponse,
)
from pydantic import BaseModel, TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import GetMentorSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe


class Response(BaseModel):
    session: MentorSessionSchemas.Session
    messages: MentorSessionSchemas.MessagesPage
    pending_learner_message_id: str | None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetMentorSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/mentor-sessions/{session_id}', response_model=Response, status_code=200
        )
        def _(
            session_id: str,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            cursor: str | None = None,
        ) -> Response:
            if not _is_ulid(session_id):
                raise HTTPException(
                    status_code=422,
                    detail={
                        'code': 'validation_error',
                        'message': 'Identificador inválido.',
                    },
                )
            try:
                detail = GetMentorSessionUseCase(database).execute(
                    user.account_id, session_id, cursor
                )
            except (TypeError, ValueError) as error:
                raise HTTPException(
                    status_code=422,
                    detail={'code': 'validation_error', 'message': 'Cursor inválido.'},
                ) from error
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)


def _is_ulid(value: str) -> bool:
    return (
        len(value) == 26
        and value[0] <= '7'
        and all(character in '0123456789ABCDEFGHJKMNPQRSTVWXYZ' for character in value)
    )
