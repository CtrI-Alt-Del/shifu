from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, PlainSerializer, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetLearningPanoramaUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import SharedPipe


def _utc_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


Instant = Annotated[datetime, PlainSerializer(_utc_instant, return_type=str)]


class StageDistributionResponse(BaseModel):
    not_started: int = Field(serialization_alias='notStarted')
    diagnosing: int
    learning: int
    completed: int
    goal_count: int = Field(serialization_alias='goalCount')


class ResumeItemResponse(BaseModel):
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    goal_id: str = Field(serialization_alias='goalId')
    goal_title: str = Field(serialization_alias='goalTitle')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    status: str
    focus_competency_name: str | None = Field(serialization_alias='focusCompetencyName')
    last_submitted_at: Instant | None = Field(serialization_alias='lastSubmittedAt')


class WeeklyCountResponse(BaseModel):
    week_start: date = Field(serialization_alias='weekStart')
    count: int


class EvolutionOptionResponse(BaseModel):
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    goal_title: str = Field(serialization_alias='goalTitle')
    skill_name: str = Field(serialization_alias='skillName')
    status: str


class CompletedSkillResponse(BaseModel):
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    goal_id: str = Field(serialization_alias='goalId')
    goal_title: str = Field(serialization_alias='goalTitle')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    final_result: float | None = Field(serialization_alias='finalResult')
    completed_on: date = Field(serialization_alias='completedOn')


class RecentMasteryResponse(BaseModel):
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    goal_id: str = Field(serialization_alias='goalId')
    goal_title: str = Field(serialization_alias='goalTitle')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    mastered_on: date = Field(serialization_alias='masteredOn')


class Response(BaseModel):
    has_goals: bool = Field(serialization_alias='hasGoals')
    completed_skill_count: int = Field(serialization_alias='completedSkillCount')
    mastered_competency_count: int = Field(
        serialization_alias='masteredCompetencyCount'
    )
    stage_distribution: StageDistributionResponse = Field(
        serialization_alias='stageDistribution'
    )
    resume_items: list[ResumeItemResponse] = Field(serialization_alias='resumeItems')
    weekly_evaluated_activities: list[WeeklyCountResponse] = Field(
        serialization_alias='weeklyEvaluatedActivities'
    )
    evolution_options: list[EvolutionOptionResponse] = Field(
        serialization_alias='evolutionOptions'
    )
    default_evolution_skill_experience_id: str | None = Field(
        serialization_alias='defaultEvolutionSkillExperienceId'
    )
    completed_skills: list[CompletedSkillResponse] = Field(
        serialization_alias='completedSkills'
    )
    recent_masteries: list[RecentMasteryResponse] = Field(
        serialization_alias='recentMasteries'
    )


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetLearningPanoramaController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/panorama', response_model=Response, status_code=200)
        def _(
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            curriculum_content_provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
        ) -> Response:
            panorama = GetLearningPanoramaUseCase(
                database, curriculum_content_provider, clock
            ).execute(user.account_id, time_zone=user.time_zone)
            return _RESPONSE_ADAPTER.validate_python(panorama, from_attributes=True)
