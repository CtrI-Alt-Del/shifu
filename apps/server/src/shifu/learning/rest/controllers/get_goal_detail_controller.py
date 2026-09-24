from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from pydantic import BaseModel, Field, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetGoalDetailUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class GoalSkillResponse(BaseModel):
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    skill_id: str = Field(serialization_alias='skillId')
    name: str
    status: str
    progress: float | None
    inclusion_reason: str | None = Field(serialization_alias='inclusionReason')


class GoalSkillRelationResponse(BaseModel):
    foundation_skill_id: str = Field(serialization_alias='foundationSkillId')
    skill_id: str = Field(serialization_alias='skillId')


class ResponseModel(BaseModel):
    goal_id: str = Field(serialization_alias='goalId')
    title: str
    description: str
    skills: tuple[GoalSkillResponse, ...]
    relations: tuple[GoalSkillRelationResponse, ...]


_RESPONSE_ADAPTER = TypeAdapter(ResponseModel)


class GetGoalDetailController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}',
            response_model=ResponseModel,
            status_code=status.HTTP_200_OK,
        )
        def _(
            response: Response,
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
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
        ) -> ResponseModel:
            detail = GetGoalDetailUseCase(
                database,
                curriculum_content_provider,
            ).execute(user.account_id, goal_id)
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
