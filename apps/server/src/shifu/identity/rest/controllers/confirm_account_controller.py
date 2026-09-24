from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.domain.structures import AccountConfirmationResult
from shifu.identity.core.interfaces import ActionTokenProvider, IdentityDatabase
from shifu.identity.core.use_cases import ConfirmAccountUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    token: str = Field(
        min_length=43,
        max_length=43,
        pattern=r'^[A-Za-z0-9_-]{43}$',
    )


class Profile(BaseModel):
    account_id: str
    display_name: str
    email: str
    time_zone: str | None


class Response(BaseModel):
    result: Literal['activated', 'expired', 'used', 'invalid']
    profile: Profile | None = None
    access_version: int | None = None


class ConfirmAccountController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/email-confirmations',
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
        ) -> Response:
            result = ConfirmAccountUseCase(
                identity_database=database,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
            ).execute(request.token)
            return ConfirmAccountController._to_response(result)

    @staticmethod
    def _to_response(result: AccountConfirmationResult) -> Response:
        profile = result.profile
        return Response(
            result=result.result.value,
            profile=(
                Profile(
                    account_id=profile.account_id,
                    display_name=profile.display_name,
                    email=profile.email,
                    time_zone=profile.time_zone,
                )
                if profile is not None
                else None
            ),
            access_version=result.access_version,
        )
