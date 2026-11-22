from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from shifu.communication.core.interfaces import PushNotificationProvider
from shifu.communication.core.use_cases import GetPushPublicKeyUseCase
from shifu.communication.pipes import CommunicationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe


class Response(BaseModel):
    public_key: str = Field(serialization_alias='publicKey')


class GetPushPublicKeyController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/push-subscriptions/public-key',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            _user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            provider: Annotated[
                PushNotificationProvider | None,
                Depends(CommunicationPipe.get_push_notification_provider),
            ],
        ) -> Response:
            return Response(public_key=GetPushPublicKeyUseCase(provider).execute())
