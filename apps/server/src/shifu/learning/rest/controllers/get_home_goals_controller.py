from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from shifu.learning.core.domain.structures import GoalSummary
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import ListHomeGoalsUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe


class GoalItem(BaseModel):
    id: str
    title: str
    description: str
    skill_count: int = Field(serialization_alias='skillCount')
    updated_at: str = Field(serialization_alias='updatedAt')


class Response(BaseModel):
    goals: list[GoalItem]


class GetHomeGoalsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/goals', response_model=Response, status_code=status.HTTP_200_OK)
        def _(
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
        ) -> Response:
            goals = ListHomeGoalsUseCase(database).execute(user.account_id)
            return GetHomeGoalsController._to_response(goals)

    @staticmethod
    def _to_response(goals: list[GoalSummary]) -> Response:
        return Response(
            goals=[
                GoalItem(
                    id=goal.id,
                    title=goal.title,
                    description=goal.description,
                    skill_count=goal.skill_count,
                    updated_at=goal.updated_at.isoformat(),
                )
                for goal in goals
            ]
        )
