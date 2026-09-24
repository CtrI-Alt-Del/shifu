from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.interfaces import ActionTokenProvider, IdentityDatabase
from shifu.identity.core.use_cases import VerifyPendingConfirmationContextUseCase
from shifu.identity.pipes import IdentityPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    account_id: str = Field(min_length=1, max_length=26)
    pending_handle: str = Field(
        min_length=43,
        max_length=43,
        pattern=r'^[A-Za-z0-9_-]{43}$',
    )


class Response(BaseModel):
    valid: bool


class VerifyPendingConfirmationContextController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/pending-confirmations/validate',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
        ) -> Response:
            return Response(
                valid=VerifyPendingConfirmationContextUseCase(
                    identity_database=database,
                    pending_confirmation_handle_provider=pending_handle_provider,
                ).execute(request.pending_handle, request.account_id)
            )
