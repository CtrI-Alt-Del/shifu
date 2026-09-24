from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.get_diagnostic_use_case import GetDiagnosticUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class CompetencyResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    progress: float | None


class Response(BaseModel):
    status: str
    next_competency_id: str | None = Field(serialization_alias='nextCompetencyId')
    next_activity_id: str | None = Field(serialization_alias='nextActivityId')
    pending_attempt_id: str | None = Field(serialization_alias='pendingAttemptId')
    pending_attempt_status: str | None = Field(
        serialization_alias='pendingAttemptStatus'
    )
    focus_competency_id: str | None = Field(serialization_alias='focusCompetencyId')
    competencies: tuple[CompetencyResponse, ...]


class GetDiagnosticController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/diagnostic',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
        ) -> Response:
            overview = GetDiagnosticUseCase(database, curriculum, clock).execute(
                user.account_id, goal_id, skill_id
            )
            return Response(
                status=overview.status.value,
                next_competency_id=overview.next_competency_id,
                next_activity_id=overview.next_activity_id,
                pending_attempt_id=overview.pending_attempt_id,
                pending_attempt_status=(
                    overview.pending_attempt_status.value
                    if overview.pending_attempt_status is not None
                    else None
                ),
                focus_competency_id=overview.focus_competency_id,
                competencies=tuple(
                    CompetencyResponse(
                        competency_id=item.competency_id,
                        competency_name=item.competency_name,
                        progress=float(item.progress)
                        if item.progress is not None
                        else None,
                    )
                    for item in overview.competencies
                ),
            )
