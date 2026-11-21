from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, StrictBool

from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.communication.core.use_cases import ChangeStreakReminderPreferenceUseCase
from shifu.communication.pipes import CommunicationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe, SharedPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    enabled: StrictBool


class Response(BaseModel):
    enabled: bool


class ChangeStreakReminderPreferenceController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.put(
            '/streak-reminder-preference',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            request: Request,
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                CommunicationDatabase, Depends(CommunicationPipe.get_database)
            ],
            clock: Annotated[ClockProvider, Depends(SharedPipe.get_clock_provider)],
        ) -> Response:
            enabled = ChangeStreakReminderPreferenceUseCase(database).execute(
                user.account_id,
                enabled=request.enabled,
                now=clock.now(),
            )
            return Response(enabled=enabled)
