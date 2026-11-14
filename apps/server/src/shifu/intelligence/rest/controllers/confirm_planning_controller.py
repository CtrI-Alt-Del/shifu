from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Response as FastApiResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import ConfirmPlanningUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import PlannedGoalProvider
from shifu.shared.pipes import SharedPipe

_UUID_PATTERN = (
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirmation_key: str = Field(pattern=_UUID_PATTERN)
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=4000)

    @field_validator('title', 'description')
    @classmethod
    def _strip_and_require_non_empty(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError('must not be empty or whitespace-only')
        return stripped_value


class Response(BaseModel):
    goal_id: str
    replayed: bool


class ConfirmPlanningController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/planning-sessions/{planning_id}/confirm',
            response_model=Response,
            status_code=200,
        )
        def _(
            planning_id: Annotated[
                str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
            ],
            request: Request,
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            sessions: Annotated[
                PlanningSessionsRepository,
                Depends(IntelligencePipe.get_planning_sessions_repository),
            ],
            planned_goals: Annotated[
                PlannedGoalProvider,
                Depends(IntelligencePipe.get_planned_goal_provider),
            ],
        ) -> Response:
            creation = ConfirmPlanningUseCase(sessions, planned_goals).execute(
                user.account_id,
                planning_id,
                request.confirmation_key.lower(),
                request.title,
                request.description,
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return Response(goal_id=creation.goal_id, replayed=creation.replayed)
