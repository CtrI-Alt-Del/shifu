from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    PasswordRecoveryDeliveryGateway,
)
from shifu.identity.core.use_cases import RetryPasswordRecoveryUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    recovery_handle: str = Field(min_length=1, max_length=512)


class Response(BaseModel):
    recovery_handle: str
    is_decoy: bool


class RetryPasswordRecoveryController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/password-recoveries/retry',
            response_model=Response,
            status_code=status.HTTP_202_ACCEPTED,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            id_provider: Annotated[
                IdentifierProvider,
                Depends(IdentityPipe.get_identifier_provider),
            ],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
            action_token_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_action_token_provider),
            ],
            recovery_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_recovery_handle_provider),
            ],
            gateway: Annotated[
                PasswordRecoveryDeliveryGateway,
                Depends(IdentityPipe.get_password_recovery_delivery_gateway),
            ],
        ) -> Response:
            result = RetryPasswordRecoveryUseCase(
                identity_database=database,
                id_provider=id_provider,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
                recovery_handle_provider=recovery_handle_provider,
                delivery_gateway=gateway,
            ).execute(request.recovery_handle)
            return Response(
                recovery_handle=result.recovery_handle,
                is_decoy=result.is_decoy,
            )
