from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Response as FastApiResponse
from pydantic import BaseModel, TypeAdapter

from shifu.intelligence.core.domain.enums import AiQuotaStatus
from shifu.intelligence.core.domain.structures import AiQuotaPolicy
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
)
from shifu.intelligence.core.use_cases import GetAiQuotaUsageUseCase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe


class Response(BaseModel):
    percentage: int
    status: AiQuotaStatus
    renews_on: date


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetAiQuotaUsageController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/ai-quota', response_model=Response, status_code=200)
        def _(
            response: FastApiResponse,
            user: Annotated[
                AuthenticatedUser, Depends(SharedPipe.get_authenticated_user)
            ],
            database: Annotated[
                IntelligenceDatabase, Depends(IntelligencePipe.get_database)
            ],
            policy: Annotated[
                AiQuotaPolicy, Depends(IntelligencePipe.get_ai_quota_policy)
            ],
            calendar: Annotated[
                AiQuotaCalendarProvider,
                Depends(IntelligencePipe.get_ai_quota_calendar_provider),
            ],
            clock: Annotated[
                ClockProvider, Depends(IntelligencePipe.get_clock_provider)
            ],
        ) -> Response:
            usage = GetAiQuotaUsageUseCase(database, policy, calendar, clock).execute(
                user.account_id
            )
            response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(usage, from_attributes=True)
