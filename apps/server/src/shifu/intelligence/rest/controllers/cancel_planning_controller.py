from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import Field

from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import CancelPlanningUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe


class CancelPlanningController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            '/planning-sessions/{planning_id}',
            response_model=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def _(
            planning_id: Annotated[
                str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
            ],
            response: Response,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            sessions: Annotated[
                PlanningSessionsRepository,
                Depends(IntelligencePipe.get_planning_sessions_repository),
            ],
        ) -> Response:
            CancelPlanningUseCase(sessions).execute(user.account_id, planning_id)
            response.headers['Cache-Control'] = 'private, no-store'
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
