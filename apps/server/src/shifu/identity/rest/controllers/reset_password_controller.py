from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.domain.structures import PasswordResetRequest
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases import ResetPasswordUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    token: str = Field(min_length=1, max_length=512)
    password: str = Field(min_length=8)
    password_confirmation: str = Field(min_length=1)


class Response(BaseModel):
    result: Literal['reset', 'expired', 'used', 'invalid']
    account_id: str | None = None
    requires_email_confirmation: bool = False
    access_version: int | None = None


class ResetPasswordController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/password-resets',
            response_model=Response,
            response_model_exclude_none=True,
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
            action_token_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_action_token_provider),
            ],
            password_hashing_provider: Annotated[
                PasswordHashingProvider,
                Depends(IdentityPipe.get_password_hashing_provider),
            ],
        ) -> Response:
            result = ResetPasswordUseCase(
                identity_database=database,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
                password_hashing_provider=password_hashing_provider,
            ).execute(
                request.token,
                PasswordResetRequest(
                    password=request.password,
                    password_confirmation=request.password_confirmation,
                ),
            )
            return Response(
                result=result.result,
                account_id=result.account_id,
                requires_email_confirmation=result.requires_email_confirmation,
                access_version=result.access_version,
            )
