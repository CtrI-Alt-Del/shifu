from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.communication.core.use_cases import GetStreakReminderPreferenceUseCase
from shifu.communication.pipes import CommunicationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe


class Response(BaseModel):
    enabled: bool


class GetStreakReminderPreferenceController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/streak-reminder-preference',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                CommunicationDatabase, Depends(CommunicationPipe.get_database)
            ],
        ) -> Response:
            enabled = GetStreakReminderPreferenceUseCase(database).execute(
                user.account_id
            )
            return Response(enabled=enabled)
