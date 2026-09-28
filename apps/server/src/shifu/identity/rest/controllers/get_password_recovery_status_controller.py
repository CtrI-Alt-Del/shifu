from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.interfaces import ActionTokenProvider, IdentityDatabase
from shifu.identity.core.use_cases import GetPasswordRecoveryStatusUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    recovery_handle: str = Field(
        min_length=1,
        max_length=512,
    )


class Response(BaseModel):
    state: str
    retry_after_seconds: int | None = None


class GetPasswordRecoveryStatusController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/password-recoveries/status',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
            recovery_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_recovery_handle_provider),
            ],
        ) -> Response:
            result = GetPasswordRecoveryStatusUseCase(
                identity_database=database,
                clock_provider=clock_provider,
                recovery_handle_provider=recovery_handle_provider,
            ).execute(request.recovery_handle)
            return Response(
                state=result.state,
                retry_after_seconds=result.retry_after_seconds,
            )
