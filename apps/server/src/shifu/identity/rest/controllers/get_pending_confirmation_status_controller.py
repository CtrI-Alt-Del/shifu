from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.identity.core.interfaces import ActionTokenProvider, IdentityDatabase
from shifu.identity.core.use_cases import GetPendingConfirmationStatusUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    pending_handle: str = Field(
        min_length=43,
        max_length=43,
        pattern=r'^[A-Za-z0-9_-]{43}$',
    )


class Response(BaseModel):
    state: Literal['ready', 'cooldown', 'delivery_issue']
    retry_after_seconds: int | None = None


_RESPONSE_ADAPTER = TypeAdapter(Response)


class GetPendingConfirmationStatusController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/pending-confirmations/status',
            response_model=Response,
            status_code=200,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
        ) -> Response:
            result = GetPendingConfirmationStatusUseCase(
                identity_database=database,
                clock_provider=clock_provider,
                pending_confirmation_handle_provider=pending_handle_provider,
            ).execute(request.pending_handle)
            return _RESPONSE_ADAPTER.validate_python(result, from_attributes=True)
