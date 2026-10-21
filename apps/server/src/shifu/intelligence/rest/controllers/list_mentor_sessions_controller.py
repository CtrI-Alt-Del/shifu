from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response as FastApiResponse,
)
from pydantic import BaseModel, TypeAdapter

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import ListMentorSessionsUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.mentor_session_schemas import MentorSessionSchemas
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe


class Response(BaseModel):
    items: list[MentorSessionSchemas.Session]
    next_cursor: str | None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class ListMentorSessionsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/mentor-sessions', response_model=Response, status_code=200)
        def _(
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            search: str | None = None,
            cursor: str | None = None,
        ) -> Response:
            try:
                page = ListMentorSessionsUseCase(database).execute(
                    user.account_id, search, cursor
                )
            except (TypeError, ValueError) as error:
                raise HTTPException(
                    status_code=422,
                    detail={'code': 'validation_error', 'message': 'Cursor inválido.'},
                ) from error
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(page, from_attributes=True)
