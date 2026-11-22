from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import (
    GetCompetencyDetailUseCase,
    GetSkillExperienceDetailUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class CompetencyResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    position: int
    progress: float | None
    status: str | None
    availability: str
    is_focus: bool = Field(serialization_alias='isFocus')
    coverage_complete: bool = Field(serialization_alias='coverageComplete')


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


class EvaluationResponse(BaseModel):
    evaluation_id: str = Field(serialization_alias='evaluationId')
    attempt_id: str = Field(serialization_alias='attemptId')
    activity_id: str = Field(serialization_alias='activityId')
    competency_id: str = Field(serialization_alias='competencyId')
    status: str


class CompletionCompetencyResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    position: int
    initial_progress: float | None = Field(serialization_alias='initialProgress')
    initial_coverage: str = Field(serialization_alias='initialCoverage')
    final_progress: float = Field(serialization_alias='finalProgress')
    mastered_on: date = Field(serialization_alias='masteredOn')


class CompletionReviewResponse(BaseModel):
    attempt_count: int = Field(serialization_alias='attemptCount')
    latest_score: float | None = Field(serialization_alias='latestScore')


class CompletionResponse(BaseModel):
    started_on: date = Field(serialization_alias='startedOn')
    completed_on: date = Field(serialization_alias='completedOn')
    duration_days: int = Field(serialization_alias='durationDays')
    completed_by_diagnosis: bool = Field(serialization_alias='completedByDiagnosis')
    learning_activity_count: int | None = Field(
        serialization_alias='learningActivityCount'
    )
    learning_attempt_count: int | None = Field(
        serialization_alias='learningAttemptCount'
    )
    initial_result: float | None = Field(serialization_alias='initialResult')
    initial_result_coverage: str = Field(serialization_alias='initialResultCoverage')
    final_result: float = Field(serialization_alias='finalResult')
    competencies: tuple[CompletionCompetencyResponse, ...]
    review: CompletionReviewResponse


class Response(BaseModel):
    goal_id: str = Field(serialization_alias='goalId')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    skill_status: str = Field(serialization_alias='skillStatus')
    overall_result: float | None = Field(serialization_alias='overallResult')
    focus_competency_id: str | None = Field(serialization_alias='focusCompetencyId')
    focus_competency_name: str | None = Field(serialization_alias='focusCompetencyName')
    competencies: tuple[CompetencyResponse, ...]
    recommendation: RecommendationResponse | None
    evaluation: EvaluationResponse | None
    overall_coverage_complete: bool = Field(
        serialization_alias='overallCoverageComplete'
    )
    recommendation_gap: str | None = Field(serialization_alias='recommendationGap')
    completion: CompletionResponse | None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetSkillExperienceDetailController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}',
            response_model=Response,
            status_code=200,
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
            curriculum_content_provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
        ) -> Response:
            detail = GetSkillExperienceDetailUseCase(
                database,
                curriculum_content_provider,
                GetCompetencyDetailUseCase(database, curriculum_content_provider),
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                user.time_zone,
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
