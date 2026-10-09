from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases import RemoveMentorSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe


class RemoveMentorSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            '/mentor-sessions/{session_id}',
            response_model=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def _(
            session_id: str,
            response: Response,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            clock_provider: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
        ) -> Response:
            if not _is_ulid(session_id):
                raise HTTPException(
                    status_code=422,
                    detail={
                        'code': 'validation_error',
                        'message': 'Identificador inválido.',
                    },
                )
            RemoveMentorSessionUseCase(database, clock_provider).execute(
                user.account_id, session_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            response.status_code = status.HTTP_204_NO_CONTENT
            return response


def _is_ulid(value: str) -> bool:
    return (
        len(value) == 26
        and value[0] <= '7'
        and all(character in '0123456789ABCDEFGHJKMNPQRSTVWXYZ' for character in value)
    )
