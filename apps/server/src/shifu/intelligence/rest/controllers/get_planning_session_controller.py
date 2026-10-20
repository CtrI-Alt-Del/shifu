from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Response as FastApiResponse
from pydantic import Field, TypeAdapter

from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import GetPlanningSessionUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.rest.schemas.planning_session_schemas import (
    PlanningSessionSchemas,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe


class Response(PlanningSessionSchemas.Detail):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetPlanningSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/planning-sessions/{planning_id}', response_model=Response, status_code=200
        )
        def _(
            planning_id: Annotated[
                str, Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
            ],
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            sessions: Annotated[
                PlanningSessionsRepository,
                Depends(IntelligencePipe.get_planning_sessions_repository),
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
            operation_timeout: Annotated[
                timedelta, Depends(IntelligencePipe.get_planning_operation_timeout)
            ],
        ) -> Response:
            session = GetPlanningSessionUseCase(
                sessions, clock, operation_timeout
            ).execute(user.account_id, planning_id)
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(session, from_attributes=True)
