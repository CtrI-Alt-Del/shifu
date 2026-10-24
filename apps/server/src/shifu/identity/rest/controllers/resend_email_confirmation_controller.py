from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationDeliveryGateway,
    IdentityDatabase,
)
from shifu.identity.core.use_cases import (
    QueueConfirmationDeliveryUseCase,
    ResendEmailConfirmationUseCase,
)
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    pending_handle: str = Field(
        min_length=43,
        max_length=43,
        pattern=r'^[A-Za-z0-9_-]{43}$',
    )


class Response(BaseModel):
    result: Literal['accepted', 'cooldown']
    retry_after_seconds: int | None = None


_RESPONSE_ADAPTER = TypeAdapter(Response)


class ResendEmailConfirmationController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/pending-confirmations/resend',
            response_model=Response,
            status_code=200,
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
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
            gateway: Annotated[
                ConfirmationDeliveryGateway,
                Depends(IdentityPipe.get_confirmation_delivery_gateway),
            ],
        ) -> Response:
            result = ResendEmailConfirmationUseCase(
                identity_database=database,
                id_provider=id_provider,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
                pending_confirmation_handle_provider=pending_handle_provider,
                queue_confirmation_delivery_use_case=QueueConfirmationDeliveryUseCase(
                    identity_database=database,
                    clock_provider=clock_provider,
                    delivery_gateway=gateway,
                ),
            ).execute(request.pending_handle)
            return _RESPONSE_ADAPTER.validate_python(result, from_attributes=True)
