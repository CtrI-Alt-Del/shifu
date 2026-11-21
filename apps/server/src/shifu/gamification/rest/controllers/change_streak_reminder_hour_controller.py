from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.enums import StreakReminderInviteStatus
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import ChangeStreakReminderHourUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe, SharedPipe


class Request(BaseModel):
    """A whole hour, as a JSON integer; a numeric string is rejected."""

    model_config = ConfigDict(extra='forbid')

    hour: Annotated[
        int,
        Field(
            strict=True,
            ge=GamificationProfile.REMINDER_HOUR_MIN,
            le=GamificationProfile.REMINDER_HOUR_MAX,
        ),
    ]


class Response(BaseModel):
    hour: int
    invite_status: StreakReminderInviteStatus = Field(
        serialization_alias='inviteStatus'
    )


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class ChangeStreakReminderHourController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.put(
            '/streak-reminder/hour',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            request: Request,
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                GamificationDatabase, Depends(GamificationPipe.get_database)
            ],
            clock: Annotated[ClockProvider, Depends(SharedPipe.get_clock_provider)],
        ) -> Response:
            settings = ChangeStreakReminderHourUseCase(database).execute(
                user.account_id, request.hour, now=clock.now()
            )
            return _RESPONSE_ADAPTER.validate_python(settings, from_attributes=True)
