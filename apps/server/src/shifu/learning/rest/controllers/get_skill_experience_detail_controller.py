from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
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
    progress: float
    status: str
    availability: str
    is_focus: bool = Field(serialization_alias='isFocus')


class RecommendationResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    activity_id: str = Field(serialization_alias='activityId')
    activity_title: str = Field(serialization_alias='activityTitle')
    difficulty: str
    type: str


class EvaluationResponse(BaseModel):
    evaluation_id: str = Field(serialization_alias='evaluationId')
    attempt_id: str = Field(serialization_alias='attemptId')
    activity_id: str = Field(serialization_alias='activityId')
    competency_id: str = Field(serialization_alias='competencyId')
    status: str


class Response(BaseModel):
    goal_id: str = Field(serialization_alias='goalId')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    skill_status: str = Field(serialization_alias='skillStatus')
    overall_result: float = Field(serialization_alias='overallResult')
    focus_competency_id: str | None = Field(serialization_alias='focusCompetencyId')
    focus_competency_name: str | None = Field(serialization_alias='focusCompetencyName')
    competencies: tuple[CompetencyResponse, ...]
    recommendation: RecommendationResponse | None
    evaluation: EvaluationResponse | None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetSkillExperienceDetailController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}',
            response_model=Response,
            status_code=status.HTTP_200_OK,
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
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
