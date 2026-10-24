from typing import Annotated

from fastapi import APIRouter, Depends, Response

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import RemoveGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe


class RemoveGoalController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            '/goals/{goal_id}',
            response_model=None,
            status_code=204,
        )
        def _(
            goal_id: str,
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            learning_database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
        ) -> Response:
            RemoveGoalUseCase(learning_database).execute(
                account_id=user.account_id,
                goal_id=goal_id,
            )
            return Response(status_code=204)
