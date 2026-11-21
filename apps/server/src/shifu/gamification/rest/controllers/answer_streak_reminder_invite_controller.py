from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, TypeAdapter

from shifu.gamification.core.domain.enums import StreakReminderInviteStatus
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import AnswerStreakReminderInviteUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe, SharedPipe


class Response(BaseModel):
    hour: int
    invite_status: StreakReminderInviteStatus = Field(
        serialization_alias='inviteStatus'
    )


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class AnswerStreakReminderInviteController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/streak-reminder/invite-answer',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                GamificationDatabase, Depends(GamificationPipe.get_database)
            ],
            clock: Annotated[ClockProvider, Depends(SharedPipe.get_clock_provider)],
        ) -> Response:
            settings = AnswerStreakReminderInviteUseCase(database).execute(
                user.account_id, now=clock.now()
            )
            return _RESPONSE_ADAPTER.validate_python(settings, from_attributes=True)
