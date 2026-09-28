from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Response, status

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import AbandonDiagnosticUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe

_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class AbandonDiagnosticController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/diagnostic/abandon',
            response_model=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            diagnostic_run_id: Annotated[
                UUID,
                Header(alias='X-Diagnostic-Run-Id'),
            ],
        ) -> Response:
            AbandonDiagnosticUseCase(database, clock).execute(
                user.account_id,
                goal_id,
                skill_id,
                str(diagnostic_run_id),
            )
            return Response(status_code=status.HTTP_204_NO_CONTENT)
