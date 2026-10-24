from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, PlainSerializer, TypeAdapter

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
    updated_at: Annotated[
        datetime,
        PlainSerializer(lambda value: value.isoformat(), return_type=str),
    ] = Field(serialization_alias='updatedAt')


class Response(BaseModel):
    goals: list[GoalItem]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetHomeGoalsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/goals', response_model=Response, status_code=200)
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
            return _RESPONSE_ADAPTER.validate_python(
                {'goals': goals}, from_attributes=True
            )
