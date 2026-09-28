from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, status
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
    position: int
    progress: float | None
    coverage_complete: bool = Field(serialization_alias='coverageComplete')
    status: str | None
    is_focus: bool = Field(serialization_alias='isFocus')
    content_released: bool = Field(serialization_alias='contentReleased')


class RecommendationResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    activity_id: str = Field(serialization_alias='activityId')
    activity_title: str = Field(serialization_alias='activityTitle')
    difficulty: str
    type: str
    reason: str
    target_concept_name: str | None = Field(serialization_alias='targetConceptName')
    material_id: str | None = Field(serialization_alias='materialId')
    gap: str | None


class ActivitySequenceItemResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    activity_id: str = Field(serialization_alias='activityId')


class Response(BaseModel):
    status: str
    activity_sequence: tuple[ActivitySequenceItemResponse, ...] = Field(
        serialization_alias='activitySequence'
    )
    run_state: str = Field(serialization_alias='runState')
    ready_to_complete: bool = Field(serialization_alias='readyToComplete')
    next_competency_id: str | None = Field(serialization_alias='nextCompetencyId')
    next_activity_id: str | None = Field(serialization_alias='nextActivityId')
    pending_attempt_id: str | None = Field(serialization_alias='pendingAttemptId')
    pending_attempt_status: str | None = Field(
        serialization_alias='pendingAttemptStatus'
    )
    focus_competency_id: str | None = Field(serialization_alias='focusCompetencyId')
    initial_overall_result: float | None = Field(
        serialization_alias='initialOverallResult'
    )
    overall_coverage_complete: bool = Field(
        serialization_alias='overallCoverageComplete'
    )
    direct_completion: bool = Field(serialization_alias='directCompletion')
    initial_recommendation: RecommendationResponse | None = Field(
        serialization_alias='initialRecommendation'
    )
    initial_recommendation_gap: str | None = Field(
        serialization_alias='initialRecommendationGap'
    )
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
            diagnostic_run_id: Annotated[
                UUID | None,
                Header(alias='X-Diagnostic-Run-Id'),
            ] = None,
        ) -> Response:
            overview = GetDiagnosticUseCase(database, curriculum, clock).execute(
                user.account_id,
                goal_id,
                skill_id,
                str(diagnostic_run_id) if diagnostic_run_id is not None else None,
            )
            return Response(
                status=overview.status.value,
                activity_sequence=tuple(
                    ActivitySequenceItemResponse(
                        competency_id=competency_id, activity_id=activity_id
                    )
                    for competency_id, activity_id in overview.activity_sequence
                ),
                run_state=overview.run_state,
                ready_to_complete=overview.ready_to_complete,
                next_competency_id=overview.next_competency_id,
                next_activity_id=overview.next_activity_id,
                pending_attempt_id=overview.pending_attempt_id,
                pending_attempt_status=(
                    overview.pending_attempt_status.value
                    if overview.pending_attempt_status is not None
                    else None
                ),
                focus_competency_id=overview.focus_competency_id,
                initial_overall_result=(
                    float(overview.initial_overall_result)
                    if overview.initial_overall_result is not None
                    else None
                ),
                overall_coverage_complete=overview.overall_coverage_complete,
                direct_completion=overview.direct_completion,
                initial_recommendation=(
                    RecommendationResponse(
                        competency_id=overview.initial_recommendation.competency_id,
                        competency_name=overview.initial_recommendation.competency_name,
                        activity_id=overview.initial_recommendation.activity_id,
                        activity_title=overview.initial_recommendation.activity_title,
                        difficulty=overview.initial_recommendation.difficulty.value,
                        type=overview.initial_recommendation.type.value,
                        reason=overview.initial_recommendation.reason,
                        target_concept_name=(
                            overview.initial_recommendation.target_concept_name
                        ),
                        material_id=overview.initial_recommendation.material_id,
                        gap=overview.initial_recommendation.gap,
                    )
                    if overview.initial_recommendation is not None
                    else None
                ),
                initial_recommendation_gap=overview.initial_recommendation_gap,
                competencies=tuple(
                    CompetencyResponse(
                        competency_id=item.competency_id,
                        competency_name=item.competency_name,
                        position=item.position,
                        progress=float(item.progress)
                        if item.progress is not None
                        else None,
                        coverage_complete=item.coverage_complete,
                        status=item.status.value if item.status is not None else None,
                        is_focus=item.is_focus,
                        content_released=item.content_released,
                    )
                    for item in overview.competencies
                ),
            )
