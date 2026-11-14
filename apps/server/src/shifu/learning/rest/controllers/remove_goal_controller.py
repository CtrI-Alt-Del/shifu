from typing import Annotated

from fastapi import APIRouter, Depends, Request as FastAPIRequest, Response, status

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import RemoveGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces.telemetry_provider import (
    TelemetryEventInput,
    TelemetryProvider,
)
from shifu.shared.pipes import SharedPipe
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe


class RemoveGoalController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            '/goals/{goal_id}',
            response_model=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def _(
            http_request: FastAPIRequest,
            goal_id: str,
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            learning_database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            telemetry_provider: Annotated[
                TelemetryProvider | None,
                Depends(TelemetryPipe.get_telemetry_provider),
            ],
        ) -> Response:
            RemoveGoalUseCase(learning_database).execute(
                account_id=user.account_id,
                goal_id=goal_id,
            )
            event: TelemetryEventInput = {
                'level': 'INFO',
                'event': 'learning.goal.deleted',
                'operation': 'goal.delete',
                'result': 'success',
            }
            request_id = TelemetryPipe.get_request_id(http_request)
            if request_id is not None:
                event['request_id'] = request_id
            TelemetryPipe.emit(telemetry_provider, event)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
