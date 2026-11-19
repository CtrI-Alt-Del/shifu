from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.communication.core.use_cases import RegisterPushSubscriptionUseCase
from shifu.communication.pipes import CommunicationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.pipes import AuthenticationPipe, SharedPipe


class _Keys(BaseModel):
    model_config = ConfigDict(extra='forbid')

    p256dh: str = Field(min_length=1, max_length=255, pattern=r'^\S+$')
    auth: str = Field(min_length=1, max_length=255, pattern=r'^\S+$')


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    endpoint: str = Field(max_length=2048, pattern=r'^https://\S+$')
    keys: _Keys


class RegisterPushSubscriptionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.put(
            '/push-subscriptions',
            response_model=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def _(
            request: Request,
            response: Response,
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                CommunicationDatabase, Depends(CommunicationPipe.get_database)
            ],
            id_provider: Annotated[
                IdentifierProvider, Depends(SharedPipe.get_identifier_provider)
            ],
            clock: Annotated[ClockProvider, Depends(SharedPipe.get_clock_provider)],
        ) -> Response:
            RegisterPushSubscriptionUseCase(database, id_provider).execute(
                user.account_id,
                endpoint=request.endpoint,
                p256dh_key=request.keys.p256dh,
                auth_secret=request.keys.auth,
                now=clock.now(),
            )
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
