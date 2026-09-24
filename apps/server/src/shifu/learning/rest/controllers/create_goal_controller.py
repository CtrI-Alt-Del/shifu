from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.use_cases.create_goal_use_case import CreateGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)
from shifu.shared.pipes import AuthenticationPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    title: str
    description: str
    skill_ids: tuple[str, ...] = Field(default=(), alias='skillIds')


class Response(BaseModel):
    goal_id: str = Field(serialization_alias='goalId')
    skill_ids: tuple[str, ...] = Field(serialization_alias='skillIds')


class CreateGoalController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals', response_model=Response, status_code=status.HTTP_201_CREATED
        )
        def _(
            request: Request,
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            identifiers: Annotated[
                IdentifierProvider, Depends(LearningPipe.get_identifier_provider)
            ],
        ) -> Response | JSONResponse:
            try:
                goal = CreateGoalUseCase(
                    database, curriculum, clock, identifiers
                ).execute(
                    user.account_id,
                    request.title,
                    request.description,
                    request.skill_ids,
                )
            except CurriculumGapError:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        'code': 'curriculum_gap',
                        'message': 'Um Skill selecionado ainda não está pronto para iniciar.',
                    },
                )
            return Response(goal_id=goal.id, skill_ids=request.skill_ids)
