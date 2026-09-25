from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.get_goal_use_case import GetGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class SkillResponse(BaseModel):
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    status: str
    policy_id: str = Field(serialization_alias='policyId')


class Response(BaseModel):
    goal_id: str = Field(serialization_alias='goalId')
    title: str
    description: str
    skills: tuple[SkillResponse, ...]


class GetGoalController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}', response_model=Response, status_code=status.HTTP_200_OK
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
        ) -> Response:
            detail = GetGoalUseCase(database, curriculum).execute(
                user.account_id, goal_id
            )
            return Response(
                goal_id=detail.goal_id,
                title=detail.title,
                description=detail.description,
                skills=tuple(
                    SkillResponse(
                        skill_id=item.skill_id,
                        skill_name=item.skill_name,
                        status=item.status.value,
                        policy_id=item.policy_id,
                    )
                    for item in detail.skills
                ),
            )
