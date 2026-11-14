from typing import Annotated

from fastapi import APIRouter, Depends, Request as FastAPIRequest
from pydantic import BaseModel, ConfigDict, Field

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.create_goal_use_case import CreateGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import (
    TelemetryEventInput,
    TelemetryProvider,
)
from shifu.shared.pipes import AuthenticationPipe
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe


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
        @router.post('/goals', response_model=Response, status_code=201)
        def _(
            http_request: FastAPIRequest,
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
            telemetry_provider: Annotated[
                TelemetryProvider | None,
                Depends(TelemetryPipe.get_telemetry_provider),
            ],
        ) -> Response:
            goal = CreateGoalUseCase(database, curriculum, clock, identifiers).execute(
                user.account_id,
                request.title,
                request.description,
                request.skill_ids,
            )
            event: TelemetryEventInput = {
                'level': 'INFO',
                'event': 'learning.goal.created',
                'operation': 'goal.create',
                'result': 'success',
            }
            request_id = TelemetryPipe.get_request_id(http_request)
            if request_id is not None:
                event['request_id'] = request_id
            TelemetryPipe.emit(telemetry_provider, event)
            return Response(goal_id=goal.id, skill_ids=request.skill_ids)
